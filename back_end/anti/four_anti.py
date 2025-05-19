import numpy as np
from scipy.spatial import distance as dist
import time
import cv2

# 活体检测常量
EYE_AR_THRESH = 0.2         # 眨眼阈值
EYE_AR_CONSEC_FRAMES = 2    # 眨眼帧数
MAR_THRESH = 0.5            # 张嘴阈值
MOUTH_AR_CONSEC_FRAMES = 3  # 张嘴帧数
NOD_THRESH = 0.03           # 点头阈值
NOD_CONSEC_FRAMES = 5       # 点头帧数
SHAKE_THRESH = 0.03         # 摇头阈值
SHAKE_CONSEC_FRAMES = 5     # 摇头帧数

# 眨眼
def eye_aspect_ratio(eye):
    if eye is None or len(eye) < 6:
        return 0.0
    try:
        A = dist.euclidean(np.asarray(eye[1]).flatten(), np.asarray(eye[5]).flatten())
        B = dist.euclidean(np.asarray(eye[2]).flatten(), np.asarray(eye[4]).flatten())
        C = dist.euclidean(np.asarray(eye[0]).flatten(), np.asarray(eye[3]).flatten())
        if C == 0:
            return 0.0
        ear = (A + B) / (2.0 * C)
        return ear
    except Exception:
        return 0.0

# 张嘴
def mouth_aspect_ratio(mouth):
    if mouth is None or len(mouth) < 10:
        return 0.0
    try:
        A = np.linalg.norm(mouth[2] - mouth[9])
        B = np.linalg.norm(mouth[4] - mouth[7])
        C = np.linalg.norm(mouth[0] - mouth[6])
        if C == 0:
            return 0.0
        mar = (A + B) / (2.0 * C)
        return mar
    except Exception:
        return 0.0

# 点头
def nod_aspect_ratio(size, pre_point, now_point):
    if size is None or pre_point is None or now_point is None or len(size) < 1:
        return 0.0
    try:
        denom = float(size[0]) / 2
        if denom == 0:
            return 0.0
        return abs(float((pre_point[1] - now_point[1]) / denom))
    except Exception:
        return 0.0

# 摇头
def shake_aspect_ratio(size, pre_point, now_point):
    if size is None or pre_point is None or now_point is None or len(size) < 2:
        return 0.0
    try:
        denom = float(size[1]) / 2
        if denom == 0:
            return 0.0
        return abs(float((pre_point[0] - now_point[0]) / denom))
    except Exception:
        return 0.0

# 四步检测函数

def detect_blink(landmarks):
    if landmarks is None or len(landmarks) < 48:
        return False, 0.0
    left_eye = landmarks[42:48]
    right_eye = landmarks[36:42]
    l_ear = eye_aspect_ratio(left_eye)
    r_ear = eye_aspect_ratio(right_eye)
    t_ear = (l_ear + r_ear) / 2.0
    return t_ear < EYE_AR_THRESH, t_ear

def detect_mouth(landmarks):
    if landmarks is None or len(landmarks) < 68:
        return False, 0.0
    mouth_points = landmarks[48:68]
    mar = mouth_aspect_ratio(mouth_points)
    return mar > MAR_THRESH, mar

def detect_nod(size, nose_center, compare_point):
    if compare_point is None or nose_center is None or size is None:
        return False, 0.0
    nod_value = nod_aspect_ratio(size, nose_center, compare_point)
    return nod_value > NOD_THRESH, nod_value

def detect_shake(size, nose_center, compare_point):
    if compare_point is None or nose_center is None or size is None:
        return False, 0.0
    shake_value = shake_aspect_ratio(size, nose_center, compare_point)
    return shake_value > SHAKE_THRESH, shake_value

def check_reflection(frame, threshold=30):
    """
    检查图像中是否存在反射高光区域（防止屏幕/视频攻击）
    threshold: 亮度阈值，越高越严格
    返回True表示检测到反射，False表示未检测到
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # 统计高亮像素比例
    bright_pixels = (gray > 255 - threshold).sum()
    total_pixels = gray.size
    bright_ratio = bright_pixels / total_pixels
    # 如果高亮区域比例过大，判定为反射
    return bright_ratio > 0.18  # 可根据实际调整

def simple_reflection_detection(frame):
    """
    HSV空间高亮+低饱和反光检测，防止屏幕/照片攻击
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    v = hsv[:,:,2]
    s = hsv[:,:,1]
    bright = cv2.threshold(v, 220, 255, cv2.THRESH_BINARY)[1]
    low_sat = cv2.threshold(s, 40, 255, cv2.THRESH_BINARY_INV)[1]
    combined = cv2.bitwise_and(bright, low_sat)
    ratio = cv2.countNonZero(combined) / (frame.shape[0] * frame.shape[1])
    return ratio > 0.1  # 阈值可调

class LivenessSession:
    """
    活体检测会话，支持超时、反射检测、动态纹理分析
    """
    def __init__(self, timeout=10):
        self.start_time = time.time()
        self.timeout = timeout
        self.finished = False
        self.last_step_time = self.start_time
        self.reflection_detected = False
        self.last_gray = None
        self.history = []

    def check_timeout(self):
        return (time.time() - self.start_time) > self.timeout

    def update_step(self):
        self.last_step_time = time.time()

    def check_reflection(self, frame):
        # 结合灰度反射和HSV反射
        if check_reflection(frame) or simple_reflection_detection(frame):
            self.reflection_detected = True
        return self.reflection_detected

    def texture_analysis(self, frame):
        """
        动态纹理分析，检测帧间变化，防止视频/照片攻击
        """
        gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 64))
        if self.last_gray is None:
            self.last_gray = gray
            return False
        diff = np.mean(cv2.absdiff(gray, self.last_gray))
        self.history.append(diff)
        self.last_gray = gray
        if len(self.history) < 5:
            return False
        std = np.std(self.history)
        return std < 4  # 屏幕/视频纹理变化更规律，真人更大
