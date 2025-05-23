# -*- coding: utf-8 -*-
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from typing import Dict, Any, List, Optional
from pathlib import Path
from .config import MODEL_DIR, FACE_MODEL_NAME, FACE_DET_THRESH, LIVENESS_THRESHOLD


class FaceProcessor:
    def __init__(self):
        """
        初始化人脸处理模型
        - 加载InsightFace模型用于人脸检测和特征提取
        """
        self.face_app = FaceAnalysis(
            name=FACE_MODEL_NAME,
            root=str(MODEL_DIR),
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
        self.face_app.prepare(ctx_id=0, det_thresh=FACE_DET_THRESH)

    def detect_faces(self, image_path: str) -> Dict[str, Any]:
        """
        检测图片中的人脸并提取特征
        :param image_path: 图片路径
        :return: 包含人脸信息和特征的字典
        """
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "message": "无法读取图片文件"}

        faces = self.face_app.get(img)
        if len(faces) == 0:
            return {"success": False, "message": "未检测到人脸"}

        # 只处理第一张人脸（假设考勤场景单人）
        face = faces[0]
        # 修复landmark为None时报错
        landmark = face.landmark.tolist() if face.landmark is not None else None
        # 特征向量转为list，便于后续处理
        feature = face.normed_embedding.tolist() if hasattr(face.normed_embedding, 'tolist') else face.normed_embedding
        return {
            "success": True,
            "face_count": len(faces),
            "bbox": face.bbox.tolist(),  # 人脸框坐标
            "landmark": landmark,  # 人脸关键点
            "feature": feature,  # 归一化后的特征向量
            "det_score": face.det_score  # 检测置信度
        }
    # 新增辅助函数：图像质量评估（基于方差和梯度）
    def _image_quality_assessment(self, img: np.ndarray) -> float:
        """评估图像质量（0-1，越高质量越好）"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        var = gray.var()
        grad = cv2.Sobel(gray, cv2.CV_64F, 1, 1).var()
        return (var + grad) / (2 * 255**2)  # 归一化到[0,1]

    # 新增辅助函数：计算熵值
    def _entropy(self, img: np.ndarray) -> float:
        """计算图像熵（衡量纹理复杂度）"""
        hist = cv2.calcHist([img], [0], None, [256], [0, 256])
        hist_normalized = hist / hist.sum()
        return -np.sum([p * np.log2(p + 1e-7) for p in hist_normalized if p != 0])
    
    def check_liveness(self, image_path: str) -> Dict[str, Any]:
        """
        增强版活体检测：结合清晰度、颜色分布、纹理特征和图像质量评估
        
        Args:
            image_path: 输入图像路径
            
        Returns:
            包含检测结果和多维度指标的字典
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {"success": False, "message": "无法读取图片文件"}
                
            # 1. 人脸检测与区域裁剪
            faces = self.face_app.get(img)
            if len(faces) == 0:
                return {"success": False, "message": "未检测到人脸"}
                
            face = faces[0]
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            face_img = img[y1:y2, x1:x2]
            
            # 2. 图像质量评估（新增）
            quality_score = self._image_quality_assessment(face_img)
            
            # 3. 清晰度检测（拉普拉斯方差 + 梯度能量）
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()  # 拉普拉斯方差
            grad_mag = cv2.Sobel(gray, cv2.CV_64F, 1, 1).std()  # 梯度能量
            
            # 4. 颜色分布与纹理分析（新增）
            hsv = cv2.cvtColor(face_img, cv2.COLOR_BGR2HSV)
            sat_mean = np.mean(hsv[:, :, 1])  # 平均饱和度
            sat_std = np.std(hsv[:, :, 1])    # 饱和度标准差
            lab = cv2.cvtColor(face_img, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]
            texture_entropy = self._entropy(l_channel)  # 亮度熵（纹理复杂度）
            
            # 5. 多特征融合与阈值调整
            is_high_quality = quality_score > 0.7
            clarity_score = (lap_var + grad_mag) / 2  # 融合清晰度指标
            color_score = (sat_mean + sat_std) / 2     # 融合颜色指标
            
            # 动态阈值策略（根据图像质量自动调整）
            if is_high_quality:
                clarity_thresh = 60   # 高质量图像提高清晰度要求
                color_thresh = 15     # 高质量图像提高颜色丰富度要求
            else:
                clarity_thresh = 40   # 低质量图像降低清晰度要求
                color_thresh = 8      # 低质量图像降低颜色要求
            
            # 活体判定逻辑（新增纹理复杂度判断）
            is_live = (
                clarity_score > clarity_thresh and
                color_score > color_thresh and
                texture_entropy > 6.0  # 真实人脸纹理熵通常大于6
            )
            
            # 综合得分计算（0-1归一化）
            liveness_score = (
                (clarity_score / max(clarity_thresh, 1)) * 0.5 +
                (color_score / max(color_thresh, 1)) * 0.3 +
                (texture_entropy / 8.0) * 0.2  # 纹理熵最大为8
            )
            liveness_score = max(0, min(1, liveness_score))  # 限制在[0,1]区间
            
            return {
                "success": True,
                "is_live": is_live,
                "liveness_score": round(liveness_score, 4),
                "clarity": round(clarity_score, 2),
                "color_score": round(color_score, 2),
                "texture_entropy": round(texture_entropy, 2),
                "image_quality": round(quality_score, 2),
                "thresholds": {
                    "clarity": clarity_thresh,
                    "color": color_thresh,
                    "texture": 6.0
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"活体检测失败: {str(e)}"}

    

    @staticmethod
    def compare_features(feat1: np.ndarray, feat2: np.ndarray) -> float:
        """
        计算两个人脸特征的余弦相似度（强制归一化，提升鲁棒性）
        :param feat1: 特征向量1 (list或ndarray)
        :param feat2: 特征向量2 (list或ndarray)
        :return: 相似度分数 [0-1]
        """
        from numpy.linalg import norm
        feat1 = np.array(feat1, dtype=np.float32)
        feat2 = np.array(feat2, dtype=np.float32)
        # 强制归一化
        if norm(feat1) > 0:
            feat1 = feat1 / norm(feat1)
        if norm(feat2) > 0:
            feat2 = feat2 / norm(feat2)
        sim = float(np.dot(feat1, feat2))
        # 映射到[0,1]区间
        sim = (sim + 1) / 2
        return {
                "success": True,
                "similarity": sim,
                "is_match": sim >= 0.5
            }


# 全局实例化处理器
face_processor = FaceProcessor()

def main():
    import sys
    print("FaceProcessor 测试程序")
    img1 = input("请输入第一张图片路径: ").strip()
    img2 = input("请输入第二张图片路径: ").strip()

    print("\n[1] 检测第一张图片的人脸...")
    res1 = face_processor.detect_faces(img1)
    print("检测结果:", res1)

    print("\n[2] 检测第二张图片的人脸...")
    res2 = face_processor.detect_faces(img2)
    print("检测结果:", res2)

    print("\n[3] 第一张图片活体检测...")
    live1 = face_processor.check_liveness(img1)
    print("活体检测:", live1)

    print("\n[4] 第二张图片活体检测...")
    live2 = face_processor.check_liveness(img2)
    print("活体检测:", live2)

    if res1.get("success") and res2.get("success"):
        print("\n[5] 计算两张图片人脸特征相似度...")
        feat1 = res1["feature"]
        feat2 = res2["feature"]
        sim = FaceProcessor.compare_features(np.array(feat1), np.array(feat2))
        print(f"特征相似度: {sim:.4f}")
    else:
        print("\n无法比较特征，相应图片未检测到人脸。")

if __name__ == "__main__":
    main()