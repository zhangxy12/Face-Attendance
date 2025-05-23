import os
import sqlite3
import re
import hashlib
import uuid
import numpy as np
import cv2
import datetime
from face_sdk.arc_face_sdk import ArcFaceSDK
from face_model1.deepface_model import DeepFaceAttendanceModel
from face_model2.silence import SilentFaceRecognitionModel
import torch

# 初始化模型
deepface_model = DeepFaceAttendanceModel(detector_backend='mtcnn', model_name='ArcFace')
try:
    silence_model = SilentFaceRecognitionModel(device='cuda' if torch.cuda.is_available() else 'cpu')
    print("静默活体检测模型初始化成功")
except Exception as e:
    print(f"静默活体检测模型初始化失败: {str(e)}")
    silence_model = None

try:
    arc_face = ArcFaceSDK()
    print("虹软SDK初始化成功")
except Exception as e:
    print(f"虹软SDK初始化失败: {str(e)}")
    arc_face = None

DATA_DIR = r'D:\\dasanxia\\content_s\\students_ph\\data'
DB_PATH = 'face_attendance.db'  # 当前目录下

def hash_password(password):
    """密码哈希加密"""
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

def get_student_info_from_filename(filename):
    # 匹配学号-姓名.扩展名
    match = re.match(r'(\d+)-(.+?)\.', filename)
    if match:
        student_id = match.group(1)
        name = match.group(2)
        return student_id, name
    return None, None

def imread_unicode(path):
    try:
        img_array = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"imread_unicode error: {e}")
        return None

def pad_width_to_multiple_of_4(img):
    h, w = img.shape[:2]
    if w % 4 != 0:
        new_w = ((w // 4) + 1) * 4
        pad = new_w - w
        img = cv2.copyMakeBorder(img, 0, 0, 0, pad, cv2.BORDER_CONSTANT, value=[0,0,0])
    return img

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    register_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    

    for fname in os.listdir(DATA_DIR):
        if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.JPG')):
            continue
        
        student_id, name = get_student_info_from_filename(fname)
        if not student_id or not name:
            print(f"跳过无效文件名: {fname}")
            continue

        hashed_pwd = hash_password('123')
        image_path = os.path.join(DATA_DIR, fname)

        # 读取图片并处理宽度
        img = imread_unicode(image_path)
        if img is None:
            print(f"跳过无法读取的图片: {fname}")
            continue
        img = pad_width_to_multiple_of_4(img)

        # ------------------------ 方案1：虹软特征提取 ------------------------
        arcsoft_feature = None
        if arc_face is not None:
            try:
                arcsoft_result = arc_face.extract_feature(image_path)  
                if arcsoft_result['success']:
                    arcsoft_feature = (
                        arcsoft_result['feature_data'] 
                        if isinstance(arcsoft_result['feature_data'], bytes) 
                        else arcsoft_result['feature_data'].tobytes()
                    )
                else:
                    print(f"虹软特征提取失败: {fname}，原因: {arcsoft_result.get('message', '未知错误')}")
            except Exception as e:
                print(f"虹软SDK调用异常: {e}")

        # ------------------------ 方案2：DeepFace特征提取 ------------------------
        deepface_feature = None
        if deepface_model is not None:
            try:
                deepface_result = deepface_model.extract_feature(image_path)
                if deepface_result['success']:
                    feature = np.asarray(deepface_result['feature_data'], dtype=np.float32).reshape(-1)
                    if feature.shape[0] != 512:
                        print(f"DeepFace特征维度错误: {fname}，实际为{feature.shape[0]}，应为512")
                        continue  # 跳过当前图片
                    deepface_feature = feature.tobytes()
                else:
                    print(f"DeepFace特征提取失败: {fname}，原因: {deepface_result.get('message', '未知错误')}")
            except Exception as e:
                print(f"DeepFace模型调用异常: {e}")

        # ------------------------ 方案3：静默活体特征提取 ------------------------
        silence_feature = None
        if silence_model is not None:
            try:
                silence_result = silence_model.extract_feature(image_path)
                if silence_result['success']:
                    feature = np.asarray(silence_result['feature_data'], dtype=np.float32).reshape(-1)
                    
                    silence_feature = feature.tobytes()
                else:
                    print(f"静默活体特征提取失败: {fname}，原因: {silence_result.get('message', '未知错误')}")
            except Exception as e:
                print(f"静默活体模型调用异常: {e}")

        # ------------------------ 存储至数据库 ------------------------
        try:
            # 插入users表（若需关联用户系统）
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, password, role, real_name, phone, create_time) VALUES (?, ?, ?, ?, ?, ?)",
                (name, hashed_pwd, 'student', name, '1231231234', register_time)
            )
            cursor.execute("SELECT id FROM users WHERE username=?", (name,))
            user_id = cursor.fetchone()[0] if cursor.fetchone() else None  # 允许user_id为空（若无需关联）

            # 插入students表，存储三种特征
            cursor.execute(
                """
                INSERT OR REPLACE INTO students (
                    student_id, name, user_id,
                    face_feature, face_feature_2, face_feature_3,
                    register_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id, name, user_id,
                    arcsoft_feature, deepface_feature, silence_feature,
                    register_time
                )
            )
            print(f"成功注册学生: {student_id}-{name}，特征状态: "
                  f"ArcSoft={bool(arcsoft_feature)}, "
                  f"DeepFace={bool(deepface_feature)}, "
                  f"Silence={bool(silence_feature)}")

        except Exception as e:
            print(f"数据库操作失败: {student_id}-{name}，原因: {e}")
            conn.rollback()  # 出错时回滚事务
            continue

    conn.commit()
    conn.close()
    print("所有学生特征提取及存储完成。")

if __name__ == '__main__':
    main()