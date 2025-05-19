import os
import sys
import numpy as np
import cv2
from deepface import DeepFace
from skimage.metrics import structural_similarity as ssim
import os
print("模型权重存在吗？", os.path.exists(r"D:\\dasanxia\\content_s\\lab6\\back_end\\face_model2\\anti_spoof_models\\2.7_80x80_MiniFASNetV2.pth"))
class DeepFaceAttendanceModel:
    def __init__(self, detector_backend='mtcnn', model_name='ArcFace'):
        self.detector_backend = detector_backend
        self.model_name = model_name
        self.model = DeepFace.build_model(model_name)

    def detect_liveness(self, image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {'success': False, 'is_live': False, 'message': '无法读取图片'}
            
            face_objs = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=False
            )
            
            if not face_objs:
                return {'success': False, 'is_live': False, 'message': '未检测到人脸'}
            
            face_img = face_objs[0]['face']
            
            # 转换浮点型图像为uint8
            if np.issubdtype(face_img.dtype, np.floating):
                face_img = (face_img * 255).clip(0, 255).astype(np.uint8)
            
            # 转换为灰度图
            face_gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY) if len(face_img.shape) == 3 else face_img
            
            # 活体检测指标计算
            blur_score = cv2.Laplacian(face_gray, cv2.CV_64F).var()
            contrast_score = face_gray.std()
            flipped = cv2.flip(face_gray, 1)
            ssim_score = ssim(face_gray, flipped)
            
            is_live = (blur_score > 50 and contrast_score > 10 and ssim_score < 0.99)
            
            return {
                'success': True,
                'is_live': is_live,
                'liveness_list': [{'score': float(min(blur_score, 1000) / 1000)}],
                'blur_score': float(blur_score),
                'contrast_score': float(contrast_score),
                'ssim_score': float(ssim_score)
            }
        except Exception as e:
            return {'success': False, 'is_live': False, 'message': str(e)}

    def extract_feature(self, image_path):
        try:
            embedding = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True,
                normalization="ArcFace"  # 确保生成512维特征
            )
            if embedding and len(embedding) > 0:
                feature = np.array(embedding[0]["embedding"])
                print(f"特征维度: {len(feature)}")  # 应输出512
                return {'success': True, 'feature_data': feature}
            return {'success': False, 'message': '未检测到人脸'}
        except Exception as e:
            return {'success': False, 'message': f'特征提取失败: {str(e)}'}

    def compare_features(self, feature1, feature2, threshold=0.6):
        """
        比较两个人脸特征向量的相似度
        
        Args:
            feature1: 第一个人脸特征向量
            feature2: 第二个人脸特征向量
            threshold: 相似度阈值，默认为0.8
            
        Returns:
            dict: 包含比对结果的字典
        """
        try:
            # 确保特征是numpy数组
            if isinstance(feature1, dict):
                # 如果是字典类型，尝试提取特征数据
                if 'embedding' in feature1:
                    feature1 = np.array(feature1['embedding'], dtype=np.float32)
                elif 'feature_data' in feature1:
                    feature1 = np.array(feature1['feature_data'], dtype=np.float32)
                else:
                    raise ValueError("特征字典格式不支持，缺少'embedding'或'feature_data'键")
            
            if isinstance(feature2, dict):
                # 如果是字典类型，尝试提取特征数据
                if 'embedding' in feature2:
                    feature2 = np.array(feature2['embedding'], dtype=np.float32)
                elif 'feature_data' in feature2:
                    feature2 = np.array(feature2['feature_data'], dtype=np.float32)
                else:
                    raise ValueError("特征字典格式不支持，缺少'embedding'或'feature_data'键")
            
            # 展平为一维数组
            f1 = np.asarray(feature1, dtype=np.float32).ravel()
            f2 = np.asarray(feature2, dtype=np.float32).ravel()
            
            # 验证维度
            if f1.shape[0] != 512 or f2.shape[0] != 512:
                raise ValueError(f"特征维度错误：f1({f1.shape[0]}) vs f2({f2.shape[0]})，预期512维")
            
            # 特征归一化
            f1_normalized = f1 / (np.linalg.norm(f1) + 1e-8)
            f2_normalized = f2 / (np.linalg.norm(f2) + 1e-8)
            
            # 计算余弦相似度
            similarity = np.dot(f1_normalized, f2_normalized)
            
            return {
                "success": True,
                "similarity": float(similarity),
                "is_match": similarity >= threshold
            }
        
        except Exception as e:
            return {
                "success": False,
                "similarity": 0.0,
                "message": str(e)
            }

# 实例化模型
arc_face = DeepFaceAttendanceModel(detector_backend='mtcnn', model_name='ArcFace')

if __name__ == "__main__":
    image_path = "F:\\qq\\qqfile\\1.jpg"
    liveness_result = arc_face.detect_liveness(image_path)
    print("活体检测结果:", liveness_result)
    
    if liveness_result['success'] and liveness_result['is_live']:
        feature_result = arc_face.extract_feature(image_path)
        print("特征提取结果:", feature_result)
    cmp_result = arc_face.compare_features(
        feature1=feature_result['feature_data'],
        feature2=feature_result['feature_data'],  # 这里可以替换为其他特征进行比较
        threshold=0.8
    )
    print("特征比较结果:", cmp_result)
