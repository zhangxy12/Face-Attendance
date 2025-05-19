import os
import sqlite3
import re
import hashlib
import uuid
import numpy as np
import cv2
import datetime
from face_sdk.arc_face_sdk import ArcFaceSDK
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

        # 用兼容中文路径的方式读取图片
        img = imread_unicode(image_path)
        if img is not None:
            img = pad_width_to_multiple_of_4(img)
        arcsoft_feature = None
        if arc_face is not None and img is not None:
            arcsoft_result = arc_face.extract_feature_from_numpy(img)
            if arcsoft_result['success']:
                # 兼容 feature_data 可能已是 bytes
                arcsoft_feature = arcsoft_result['feature_data'] if isinstance(arcsoft_result['feature_data'], bytes) else arcsoft_result['feature_data'].tobytes()
            else:
                print(f"特征提取失败: {fname}，原因: {arcsoft_result.get('message', '未知错误')}")
                continue  # 跳过特征提取失败的图片
        elif img is None:
            print(f"特征提取失败: {fname}，原因: 无法读取图像（中文路径或文件损坏）")
            continue

        try:
            # 插入users表
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, password, role, real_name, phone, create_time) VALUES (?, ?, ?, ?, ?, ?)",
                (name, hashed_pwd, 'student', name, '1231231234', register_time)
            )
            # 获取user_id
            cursor.execute("SELECT id FROM users WHERE username=?", (name,))
            user_id = cursor.fetchone()[0]

            # 插入students表，注册人脸特征
            cursor.execute(
                "INSERT OR IGNORE INTO students (student_id, name, user_id, face_feature, register_time) VALUES (?, ?, ?, ?, ?)",
                (student_id, name, user_id, arcsoft_feature, register_time)
            )
            print(f"已注册: {student_id}-{name}")
        except Exception as e:
            print(f"插入失败: {student_id}-{name}，原因: {e}")

    conn.commit()
    conn.close()
    print("全部完成。")

if __name__ == '__main__':
    main()