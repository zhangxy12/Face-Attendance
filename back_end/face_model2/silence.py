import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.nn import functional as F
from torchvision import transforms
from facenet_pytorch import InceptionResnetV1, MTCNN
from scipy.spatial.distance import cosine
from PIL import Image

# 从原始框架中提取的完整模块定义
class L2Norm(nn.Module):
    def forward(self, x):
        return F.normalize(x)

class Flatten(nn.Module):
    def forward(self, x):
        return x.view(x.size(0), -1)

class Conv_block(nn.Module):
    def __init__(self, in_c, out_c, kernel=(1, 1), stride=(1, 1), padding=(0, 0), groups=1):
        super().__init__()
        self.conv = nn.Conv2d(in_c, out_c, kernel_size=kernel, 
                             groups=groups, stride=stride, padding=padding, bias=False)
        self.bn = nn.BatchNorm2d(out_c)
        self.prelu = nn.PReLU(out_c)
        
    def forward(self, x):
        return self.prelu(self.bn(self.conv(x)))

class Linear_block(nn.Module):
    def __init__(self, in_c, out_c, kernel=(1, 1), stride=(1, 1), padding=(0, 0), groups=1):
        super().__init__()
        self.conv = nn.Conv2d(in_c, out_c, kernel_size=kernel,
                             groups=groups, stride=stride, padding=padding, bias=False)
        self.bn = nn.BatchNorm2d(out_c)
        
    def forward(self, x):
        return self.bn(self.conv(x))

class Depth_Wise(nn.Module):
    def __init__(self, c1, c2, c3, residual=False, 
                 kernel=(3, 3), stride=(2, 2), padding=(1, 1), groups=1):
        super().__init__()
        self.conv = Conv_block(c1[0], c1[1], kernel=(1, 1), padding=(0, 0), stride=(1, 1))
        self.conv_dw = Conv_block(c2[0], c2[1], groups=c2[0], 
                                 kernel=kernel, padding=padding, stride=stride)
        self.project = Linear_block(c3[0], c3[1], kernel=(1, 1), 
                                   padding=(0, 0), stride=(1, 1))
        self.residual = residual
        
    def forward(self, x):
        if self.residual:
            shortcut = x
        x = self.conv(x)
        x = self.conv_dw(x)
        x = self.project(x)
        return x + shortcut if self.residual else x

class Residual(nn.Module):
    def __init__(self, c1, c2, c3, num_block, groups, 
                 kernel=(3, 3), stride=(1, 1), padding=(1, 1)):
        super().__init__()
        self.model = nn.Sequential(*[
            Depth_Wise(c1[i], c2[i], c3[i], residual=True,
                      kernel=kernel, padding=padding, stride=stride, groups=groups)
            for i in range(num_block)
        ])
        
    def forward(self, x):
        return self.model(x)

# 原始 keep_dict 定义
keep_dict = {
    '1.8M': [32, 32, 103, 103, 64, 13, 13, 64, 26, 26,
             64, 13, 13, 64, 52, 52, 64, 231, 231, 128,
             154, 154, 128, 52, 52, 128, 26, 26, 128, 52,
             52, 128, 26, 26, 128, 26, 26, 128, 308, 308,
             128, 26, 26, 128, 26, 26, 128, 512, 512],
    
    '1.8M_': [32, 32, 103, 103, 64, 13, 13, 64, 13, 13, 
              64, 13, 13, 64, 13, 13, 64, 231, 231, 128,
              231, 231, 128, 52, 52, 128, 26, 26, 128, 
              77, 77, 128, 26, 26, 128, 26, 26, 128, 308, 
              308, 128, 26, 26, 128, 26, 26, 128, 512, 512]
}

class MiniFASNet(nn.Module):
    def __init__(self, keep, embedding_size, conv6_kernel=(5, 5),
                 drop_p=0.0, num_classes=3, img_channel=3):
        super(MiniFASNet, self).__init__()
        self.embedding_size = embedding_size
        
        # 网络结构定义
        self.conv1 = Conv_block(img_channel, keep[0], kernel=(3, 3), 
                               stride=(2, 2), padding=(1, 1))
        self.conv2_dw = Conv_block(keep[0], keep[1], kernel=(3, 3), 
                                  stride=(1, 1), padding=(1, 1), groups=keep[1])
        
        # conv_23 模块
        c1 = [(keep[1], keep[2])]
        c2 = [(keep[2], keep[3])]
        c3 = [(keep[3], keep[4])]
        self.conv_23 = Depth_Wise(c1[0], c2[0], c3[0], kernel=(3, 3), 
                                 stride=(2, 2), padding=(1, 1), groups=keep[3])
        
        # conv_3 模块
        c1 = [(keep[4], keep[5]), (keep[7], keep[8]), (keep[10], keep[11]), (keep[13], keep[14])]
        c2 = [(keep[5], keep[6]), (keep[8], keep[9]), (keep[11], keep[12]), (keep[14], keep[15])]
        c3 = [(keep[6], keep[7]), (keep[9], keep[10]), (keep[12], keep[13]), (keep[15], keep[16])]
        self.conv_3 = Residual(c1, c2, c3, num_block=4, groups=keep[4], 
                              kernel=(3, 3), stride=(1, 1), padding=(1, 1))
        
        # conv_34 模块
        c1 = [(keep[16], keep[17])]
        c2 = [(keep[17], keep[18])]
        c3 = [(keep[18], keep[19])]
        self.conv_34 = Depth_Wise(c1[0], c2[0], c3[0], kernel=(3, 3), 
                                 stride=(2, 2), padding=(1, 1), groups=keep[19])
        
        # conv_4 模块
        c1 = [(keep[19], keep[20]), (keep[22], keep[23]), (keep[25], keep[26]), 
              (keep[28], keep[29]), (keep[31], keep[32]), (keep[34], keep[35])]
        c2 = [(keep[20], keep[21]), (keep[23], keep[24]), (keep[26], keep[27]), 
              (keep[29], keep[30]), (keep[32], keep[33]), (keep[35], keep[36])]
        c3 = [(keep[21], keep[22]), (keep[24], keep[25]), (keep[27], keep[28]), 
              (keep[30], keep[31]), (keep[33], keep[34]), (keep[36], keep[37])]
        self.conv_4 = Residual(c1, c2, c3, num_block=6, groups=keep[19], 
                              kernel=(3, 3), stride=(1, 1), padding=(1, 1))
        
        # conv_45 模块
        c1 = [(keep[37], keep[38])]
        c2 = [(keep[38], keep[39])]
        c3 = [(keep[39], keep[40])]
        self.conv_45 = Depth_Wise(c1[0], c2[0], c3[0], kernel=(3, 3), 
                                 stride=(2, 2), padding=(1, 1), groups=keep[40])
        
        # conv_5 模块
        c1 = [(keep[40], keep[41]), (keep[43], keep[44])]
        c2 = [(keep[41], keep[42]), (keep[44], keep[45])]
        c3 = [(keep[42], keep[43]), (keep[45], keep[46])]
        self.conv_5 = Residual(c1, c2, c3, num_block=2, groups=keep[40], 
                              kernel=(3, 3), stride=(1, 1), padding=(1, 1))
        
        # 分类头
        self.conv_6_sep = Conv_block(keep[46], keep[47], kernel=(1, 1), 
                                   stride=(1, 1), padding=(0, 0))
        self.conv_6_dw = Linear_block(keep[47], keep[48], kernel=conv6_kernel, 
                                    stride=(1, 1), padding=(0, 0))
        self.conv_6_flatten = Flatten()
        self.linear = nn.Linear(512, embedding_size, bias=False)
        self.bn = nn.BatchNorm1d(embedding_size)
        self.drop = nn.Dropout(p=drop_p)
        self.prob = nn.Linear(embedding_size, num_classes, bias=False)

    def forward(self, x):
        out = self.conv1(x)
        out = self.conv2_dw(out)
        out = self.conv_23(out)
        out = self.conv_3(out)
        out = self.conv_34(out)
        out = self.conv_4(out)
        out = self.conv_45(out)
        out = self.conv_5(out)
        out = self.conv_6_sep(out)
        out = self.conv_6_dw(out)
        out = self.conv_6_flatten(out)
        
        if self.embedding_size != 512:
            out = self.linear(out)
            
        out = self.bn(out)
        out = self.drop(out)
        out = self.prob(out)
        return out

# 工厂函数
def MiniFASNetV2(embedding_size=128, conv6_kernel=(5, 5),
                 drop_p=0.2, num_classes=3, img_channel=3):
    return MiniFASNet(keep_dict['1.8M_'], embedding_size, conv6_kernel, 
                     drop_p, num_classes, img_channel)

class SilentFaceRecognitionModel:
    def __init__(self, 
                 liveness_model_path="", 
                 device='cpu'):
        self.device = torch.device(device)
        self.mtcnn = MTCNN(keep_all=True, device=self.device)
        self.facenet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        self.liveness_model = self.load_liveness_model(liveness_model_path)
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((80, 80)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

    def load_liveness_model(self, model_path):
        # 使用原始定义的工厂函数创建模型
        model = MiniFASNetV2(embedding_size=128, num_classes=2, img_channel=3)
        
        # 加载状态字典
        state_dict = torch.load(model_path, map_location=self.device)
        
        # 处理DataParallel前缀
        state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
        
        # 过滤不匹配的参数
        filtered_state_dict = {
            k: v for k, v in state_dict.items() 
            if k in model.state_dict() and v.shape == model.state_dict()[k].shape
        }
        
        model.load_state_dict(filtered_state_dict, strict=False)
        return model.eval().to(self.device)

    def detect_liveness(self, image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                # print(f"[DEBUG] 无法读取图片: {image_path}")
                return {'success': False, 'is_live': False, 'message': '无法读取图片'}

            faces, _ = self.mtcnn.detect(img)
            # print(f"[DEBUG] 检测到人脸框: {faces}")
            if faces is None or len(faces) == 0:
                # print("[DEBUG] 未检测到人脸")
                return {'success': False, 'is_live': False, 'message': '未检测到人脸'}

            # 提取人脸区域并预处理
            x1, y1, x2, y2 = map(int, faces[0])
            # print(f"[DEBUG] 人脸坐标: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            face_img = img[y1:y2, x1:x2]
            if face_img.size == 0:
                # print("[DEBUG] 人脸区域为空")
                return {'success': False, 'is_live': False, 'message': '人脸区域为空'}
            input_tensor = self.transform(face_img).unsqueeze(0).to(self.device)
            # print(f"[DEBUG] 输入张量shape: {input_tensor.shape}")

            # 执行推理
            with torch.no_grad():
                output = self.liveness_model(input_tensor)
                # print(f"[DEBUG] 模型原始输出: {output}")
                probs = torch.softmax(output, dim=1)[0].cpu().numpy()
                # print(f"[DEBUG] softmax后概率: {probs}")

            is_live = probs[1] > 0.5
            return {
                'success': True,
                'is_live': bool(is_live),
                'liveness_score': float(probs[1]),
                'message': '活体检测成功'
            }

        except Exception as e:
            # print(f"[DEBUG] 异常: {e}")
            return {'success': False, 'is_live': False, 'message': str(e)}

    def extract_feature(self, image_path):
        try:
            img = Image.open(image_path).convert('RGB')
            face_tensor = self.mtcnn(img)
            if face_tensor is None:
                return {'success': False, 'message': '未检测到人脸'}
            
            # 修正：如果只有一张人脸，face_tensor.shape = [3, 160, 160]，需要unsqueeze(0)变成[1, 3, 160, 160]
            if len(face_tensor.shape) == 3:
                face_tensor = face_tensor.unsqueeze(0)
            # 如果已经是多张人脸，shape为[n, 3, 160, 160]，无需处理

            face_tensor = face_tensor.to(self.device)
            with torch.no_grad():
                embedding = self.facenet(face_tensor)[0].cpu().numpy()
                
            return {'success': True, 'feature_data': embedding}

        except Exception as e:
            return {'success': False, 'message': f'特征提取失败: {str(e)}'}

    def compare_features(self, feature1, feature2, threshold=0.6):
        try:
            f1 = np.asarray(feature1, dtype=np.float32).ravel()
            f2 = np.asarray(feature2, dtype=np.float32).ravel()
            similarity = 1 - cosine(f1, f2)
            
            return {
                "success": True,
                "similarity": float(similarity),
                "is_match": similarity >= threshold
            }

        except Exception as e:
            return {"success": False, "similarity": 0.0, "message": str(e)}


if __name__ == "__main__":
    # 初始化模型
    model = SilentFaceRecognitionModel(
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )

    # 测试图片路径
    image_path_1 = "F:\\qq\\qqfile\\2.jpg"
    image_path_2 = "F:\\qq\\qqfile\\2.jpg"

    # 活体检测
    live_result = model.detect_liveness(image_path_1)
    print(f"是否为真人：{live_result['is_live']} (得分: {live_result.get('liveness_score', 0):.2f})")

    # 特征提取与比对
    feature1 = model.extract_feature(image_path_1)
    feature2 = model.extract_feature(image_path_2)

    if feature1['success'] and feature2['success']:
        compare_result = model.compare_features(
            feature1['feature_data'], 
            feature2['feature_data']
        )
        print(f"是否匹配：{compare_result['is_match']} (相似度: {compare_result['similarity']:.2f})")
    else:
        print("特征提取失败:", feature1.get('message', ''), feature2.get('message', ''))