from fastapi import FastAPI, File, UploadFile, Form, Query, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union
import uvicorn
import os
import uuid
import shutil
import datetime
import jwt
from jwt.exceptions import InvalidTokenError
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
import cv2
import redis
import random
import base64
import dlib
from scipy.spatial import distance as dist
import math
import time

# 导入自定义模块
from database import AttendanceDB
from face_sdk.arc_face_sdk import ArcFaceSDK
from face_model1.deepface_model import DeepFaceAttendanceModel
from face_model2.silence import SilentFaceRecognitionModel
from anti.four_anti import detect_blink, detect_mouth, detect_nod, detect_shake, LivenessSession, check_reflection
import torch

# Redis配置
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

# dlib模型加载
predictor_path = ''
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_path)

# 活体检测步骤定义
LIVENESS_STEPS = [
    {"name": "blink", "text": "请眨眼"},
    {"name": "mouth", "text": "请张嘴"},
    {"name": "nod", "text": "请点头"},
    {"name": "shake", "text": "请摇头"}
]

# 检测算法实现
EYE_AR_THRESH = 0.2
EYE_AR_CONSEC_FRAMES = 2
MAR_THRESH = 0.5
MOUTH_AR_CONSEC_FRAMES = 3
NOD_THRESH = 0.03
NOD_CONSEC_FRAMES = 5
SHAKE_THRESH = 0.03
SHAKE_CONSEC_FRAMES = 5

def get_random_steps():
    steps = LIVENESS_STEPS.copy()
    random.shuffle(steps)
    return steps

# Redis session key helpers
def get_session_key(session_id):
    return f"liveness_session:{session_id}"

def get_session(session_id):
    key = get_session_key(session_id)
    data = redis_client.get(key)
    if data:
        import json
        return json.loads(data)
    return None

def set_session(session_id, session):
    key = get_session_key(session_id)
    import json
    redis_client.setex(key, 600, json.dumps(session))  # 10分钟过期

# JWT配置
SECRET_KEY = "b47e9f96493a4abf543d3079a837493e27512359707301f882b2517e654f53ad"  # 随机变量需要复杂
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# 身份验证模型
class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: str
    user_id: int
    real_name: str
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None

class UserBase(BaseModel):
    real_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: str = "student"  # 默认为学生角色

class StudentCreate(BaseModel):
    password: str
    real_name: str
    student_id: str
    phone: Optional[str] = None

class TeacherCreate(BaseModel):
    password: str
    real_name: str
    teacher_id: str
    phone: Optional[str] = None

class User(UserBase):
    id: int
    role: str
    status: bool = True

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# 考勤规则模型
class AttendanceRuleCreate(BaseModel):
    class_id: int
    start_time: str
    end_time: str
    late_threshold: int = 15
    weekdays: str = "1,2,3,4,5"
    remark: Optional[str] = None
    is_active: int = 1


# 创建应用
app = FastAPI(
    title="学生校园人脸考勤系统",
    description="基于多角色的校园人脸考勤系统，支持教师管理和学生考勤",
    version="2.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置上传目录
UPLOAD_DIR = Path(__file__).parent / "uploads"

UPLOAD_DIR.mkdir(exist_ok=True)


# OAuth2认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# 初始化数据库
db = AttendanceDB()

# 初始化虹软SDK
try:
    arc_face = ArcFaceSDK()
    print("虹软SDK初始化成功")
except Exception as e:
    print(f"虹软SDK初始化失败: {str(e)}")
    arc_face = None

# 初始化DeepFace模型
deepface_model = DeepFaceAttendanceModel(detector_backend='mtcnn', model_name='ArcFace')

# 初始化SilentFaceRecognitionModel（静默活体检测模型）
try:
    silence_model = SilentFaceRecognitionModel(device='cuda' if torch.cuda.is_available() else 'cpu')
    print("静默活体检测模型初始化成功")
except Exception as e:
    print(f"静默活体检测模型初始化失败: {str(e)}")
    silence_model = None

# 保存上传的图片
def save_upload_file(upload_file: UploadFile, directory: Path = UPLOAD_DIR) -> str:
    # 创建唯一文件名
    file_ext = os.path.splitext(upload_file.filename)[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = directory / filename
    
    # 保存文件
    with open(file_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    
    return str(file_path)

# 创建访问令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 验证令牌
async def verify_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        role: str = payload.get("role")
        user_id: int = payload.get("user_id")
        token_data = TokenData(username=username, role=role, user_id=user_id)
    except InvalidTokenError:
        raise credentials_exception
    return token_data

# 获取当前用户
async def get_current_user(token_data: TokenData = Depends(verify_token)):
    return token_data

# 检查是否为教师
async def check_teacher_role(token_data: TokenData = Depends(verify_token)):
    if token_data.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要教师权限"
        )
    return token_data

# 检查是否为学生
async def check_student_role(token_data: TokenData = Depends(verify_token)):
    if token_data.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要学生权限"
        )
    return token_data

# 获取学生ID
async def get_student_id(token_data: TokenData = Depends(check_student_role)):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id FROM students WHERE user_id = ?", (token_data.user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到关联的学生信息"
        )
    
    return result["student_id"]

# 获取教师ID
async def get_teacher_id(token_data: TokenData = Depends(check_teacher_role)):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM teachers WHERE user_id = ?", (token_data.user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到关联的教师信息"
        )
    
    return result["id"]

#------------------------ 认证相关API ------------------------#

# 用户登录
@app.post("/api/auth/login", response_model=Token, tags=["认证管理"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录并获取访问令牌"""
    login_result = db.login(form_data.username, form_data.password)
    
    if not login_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=login_result["message"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = login_result["user"]
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user_role": user["role"],
        "user_id": user["id"],
        "real_name": user["real_name"]
    }
    
    # 添加学生或教师ID到响应
    if user["role"] == "student" and "student_id" in user:
        response_data["student_id"] = user["student_id"]
    elif user["role"] == "teacher" and "teacher_id" in user:
        response_data["teacher_id"] = user["teacher_id"]
    
    return response_data

# 注册学生
@app.post("/api/auth/register/student", tags=["认证管理"])
async def register_student_with_account(student: StudentCreate):
    """注册学生账号"""
    # 创建用户
    user_result = db.create_user(
        password=student.password,
        role="student",
        real_name=student.real_name,
        email=None,  # Default to None since email was removed from model
        phone=student.phone
    )
    
    if not user_result["success"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=user_result
        )
    
    # 注册学生信息
    result = db.register_student(
        student_id=student.student_id,
        name=student.real_name,
        class_name=""  # Default to empty string since class_name was removed from model
    )
    
    # 如果学生信息注册失败，需要删除刚才创建的用户账号
    if not result["success"]:
        db.delete_user(user_result["user_id"])
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=result
        )
    
    # 关联用户ID到学生表
    db.link_student_user(student.student_id, user_result["user_id"])
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "message": f"学生 {student.real_name} 注册成功"
        }
    )

# 注册教师
@app.post("/api/auth/register/teacher", tags=["认证管理"])
async def register_teacher(
    teacher: TeacherCreate
):
    """注册教师账号"""
    # 创建用户
    user_result = db.create_user(
        password=teacher.password,
        role="teacher",
        real_name=teacher.real_name,
        phone=teacher.phone
    )
    
    if not user_result["success"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=user_result
        )
    
    # 创建教师记录
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO teachers (teacher_id, name, department, position, user_id) VALUES (?, ?, ?, ?, ?)",
            (teacher.teacher_id, teacher.real_name, "", "", user_result["user_id"])
        )
        conn.commit()
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": f"教师 {teacher.real_name} 注册成功"
            }
        )
    except Exception as e:
        # 用户创建成功但教师记录创建失败，需要回滚
        cursor.execute("DELETE FROM users WHERE id = ?", (user_result["user_id"],))
        conn.commit()
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "message": f"教师记录创建失败: {str(e)}"
            }
        )
    finally:
        conn.close()

# 修改密码
@app.post("/api/auth/password", tags=["认证管理"])
async def change_password(
    password_data: PasswordChange,
    token_data: TokenData = Depends(get_current_user)
):
    """修改用户密码"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # 获取用户信息
        cursor.execute("SELECT password FROM users WHERE id = ?", (token_data.user_id,))
        user = cursor.fetchone()
        
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "message": "用户不存在"
                }
            )
        
        # 验证旧密码
        if not db.verify_password(user["password"], password_data.old_password):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "message": "旧密码不正确"
                }
            )
        
        # 生成新密码哈希
        new_password_hash = db.hash_password(password_data.new_password)
        
        # 更新密码
        cursor.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (new_password_hash, token_data.user_id)
        )
        conn.commit()
        
        return {
            "success": True,
            "message": "密码修改成功"
        }
    except Exception as e:
        conn.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": f"密码修改失败: {str(e)}"
            }
        )
    finally:
        conn.close()

#------------------------ 学生管理API ------------------------#

# 获取学生列表（教师权限）
@app.get("/api/admin/students", tags=["教师管理"])
async def get_students(
    class_name: Optional[str] = None,
    token_data: TokenData = Depends(check_teacher_role)
):
    """获取学生列表"""
    result = db.get_all_students(class_name)
    return result

# 获取学生详情（教师权限）
@app.get("/api/admin/students/{student_id}", tags=["教师管理"])
async def get_student_detail(
    student_id: str,
    token_data: TokenData = Depends(check_teacher_role)
):
    """获取学生详细信息"""
    result = db.get_student(student_id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    return result

# 更新学生信息（教师权限）
# @app.put("/api/admin/students/{student_id}", tags=["教师管理"])
# async def update_student(
#     student_id: str,
#     name: Optional[str] = Form(None),
#     class_name: Optional[str] = Form(None),
#     token_data: TokenData = Depends(check_teacher_role)
# ):
#     """更新学生信息"""
#     # 获取原始学生信息
#     student_info = db.get_student(student_id)
#     if not student_info["success"]:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=student_info["message"]
#         )
    
#     # 更新学生信息
#     result = db.register_student(
#         student_id=student_id,
#         name=name or student_info["data"]["name"],
#         class_name=class_name or student_info["data"]["class_name"]
#     )
    
#     return result

# # 删除学生（教师权限）
# @app.delete("/api/admin/students/{student_id}", tags=["教师管理"])
# async def delete_student(
#     student_id: str,
#     token_data: TokenData = Depends(check_teacher_role)
# ):
#     """删除学生信息"""
#     result = db.delete_student(student_id)
#     return result

#------------------------ 班级管理API ------------------------#

# 获取班级列表（教师权限）
@app.get("/api/admin/classes", tags=["教师管理"])
async def get_classes(token_data: TokenData = Depends(check_teacher_role)):
    """获取所有班级列表"""
    result = db.get_all_classes()
    return result

# 创建班级（教师权限）
@app.post("/api/admin/classes", tags=["教师管理"])
async def create_class(
    class_name: str = Form(...),
    description: Optional[str] = Form(None),
    token_data: TokenData = Depends(check_teacher_role)
):
    """创建新班级"""
    # 获取教师ID
    teacher_id = await get_teacher_id(token_data)
    
    # 创建班级
    result = db.create_class(
        class_name=class_name,
        description=description,
        teacher_id=teacher_id,
        
    )
    
    return result

#------------------------ 考勤规则API ------------------------#

# 创建或更新考勤规则（教师权限）
@app.post("/api/admin/attendance-rules", tags=["教师管理"])
async def create_attendance_rule(
    rule: AttendanceRuleCreate,
    token_data: TokenData = Depends(check_teacher_role)
):
    print(f"Received rule: {rule}")
    """创建或更新班级考勤规则"""
    result = db.create_attendance_rule(
        class_id=rule.class_id,
        start_time=rule.start_time,
        end_time=rule.end_time,
        late_threshold=rule.late_threshold,
        weekdays=rule.weekdays,
        remark=rule.remark,
        is_active=rule.is_active
    )
    
    return result

# 获取考勤规则（教师权限）
@app.get("/api/admin/attendance-rules", tags=["教师管理"])
async def get_attendance_rules(
    class_id: Optional[int] = None,
    token_data: TokenData = Depends(check_teacher_role)
):
    """获取班级考勤规则"""
    result = db.get_attendance_rules(class_id)
    return result

#------------------------ 考勤申诉API ------------------------#
#------------------------ 保留现有API接口，增加认证 ------------------------#

# 注册学生接口 (学生人脸注册)
@app.post("/api/register-student", tags=["学生管理"])
async def register_student_face(
    student_id: str = Form(...),
    name: str = Form(...),
    class_name: str = Form(None),
    face_image: UploadFile = File(...)
):
    """学生人脸特征注册，支持多方案（ArcSoft/DeepFace/静默活体）"""
    image_path = save_upload_file(face_image)
    # 1. ArcSoft特征
    arcsoft_feature = None
    if arc_face is not None:
        arcsoft_result = arc_face.extract_feature(image_path)
        if arcsoft_result['success']:
            arcsoft_feature = arcsoft_result['feature_data'] if isinstance(arcsoft_result['feature_data'], bytes) else arcsoft_result['feature_data'].tobytes()
    # 2. DeepFace特征
    deepface_feature = None
    deepface_result = deepface_model.extract_feature(image_path)
    if deepface_result['success']:
        feature = np.asarray(deepface_result['feature_data'], dtype=np.float32).reshape(-1)
        if feature.shape[0] != 512:
            os.remove(image_path)
            return {"success": False, "message": f"DeepFace特征维度错误，实际为{feature.shape[0]}，应为512"}
        deepface_feature = feature.tobytes()
    # 3. 静默活体特征
    silence_feature = None
    if silence_model is not None:
        silence_result = silence_model.extract_feature(image_path)
        if silence_result['success']:
            silence_feature = np.asarray(silence_result['feature_data'], dtype=np.float32).reshape(-1).tobytes()
    os.remove(image_path)
    # 注册学生信息，存3种特征
    result = db.register_student(
        student_id=student_id,
        name=name,
        face_feature=arcsoft_feature,
        class_name=class_name,
        face_feature_2=deepface_feature,
        face_feature_3=silence_feature
    )
    return result

# 考勤记录接口
#TODO: 新增剩下两种方案的考勤方法的后端api设计
@app.post("/api/attendance", tags=["考勤管理"])
async def record_attendance(
    image: UploadFile = File(...),
    method: str = Form("arcsoft"),
    student_id: Optional[str] = Form(None)
):
    """记录学生考勤"""
    if arc_face is None:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "虹软SDK未正确初始化"}
        )
    image_path = save_upload_file(image)
    # 1. 活体检测
    liveness_result = arc_face.detect_liveness(image_path)
    print(f"活体检测结果: {liveness_result}")
    if "liveness_list" in liveness_result and liveness_result["liveness_list"]:
        for item in liveness_result["liveness_list"]:
            if "is_live" in item:
                print(f"活体检测: {item['is_live']}")
                score = item["is_live"]
                
    if not liveness_result["success"] or not liveness_result.get("is_live", False):
        
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "活体检测失败，无法进行考勤",
                
            }
        )
    feature_result = arc_face.extract_feature(image_path)
    if not feature_result["success"]:
        os.remove(image_path)
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "人脸特征提取失败，无法进行考勤",
                
            }
        )
    os.remove(image_path)
    current_feature = feature_result["feature_data"]
    similarity_threshold = 0.8
    # 新增：如果传入 student_id，只比对该学生
    if student_id:
        feature_result = db.get_student_face_feature(student_id,"arcsoft")
        if not feature_result["success"]:
            
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "该学生未注册人脸特征，无法考勤"
                }
            )
        compare_result = arc_face.compare_features(current_feature, feature_result["feature"])
        if not compare_result["success"] or compare_result["similarity"] < similarity_threshold:
            
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "人脸比对失败或不匹配，考勤失败",
                    "similarity": compare_result.get("similarity", 0.0)
                }
            )
        similarity = compare_result["similarity"]
        liveness_score = None
        if liveness_result.get("liveness_list") and len(liveness_result["liveness_list"]) > 0:
            score = liveness_result["liveness_list"][0].get("is_live")
            if isinstance(score, float) and not np.isnan(score) and not np.isinf(score):
                liveness_score = score
        attendance_result = db.record_attendance(
            student_id=student_id,
            liveness_score=liveness_score,
            detection_method=method,
            similarity=similarity,
            status=None
        )
        
        return attendance_result


@app.post("/api/attendance/deepface", tags=["考勤管理"])
async def record_attendance_deepface(
    image: UploadFile = File(...),
    student_id: str = Form(...)
):
    """基于DeepFace方案的考勤打卡"""
    image_path = save_upload_file(image)
    # 1. 活体检测
    liveness_result = deepface_model.detect_liveness(image_path)
    if not liveness_result['success'] or not liveness_result['is_live']:
        return {"success": False, "message": liveness_result.get('message', '活体检测未通过')}
    
    # 2. 提取特征
    feature_result = deepface_model.extract_feature(image_path)
    os.remove(image_path)  # 删除临时文件
    if not feature_result['success']:
        return {"success": False, "message": feature_result.get('message', '特征提取失败')}
    print(f"实时特征类型: {type(feature_result['feature_data'])}")
    # 3. 获取学生特征
    student = db.get_student(student_id)
    if not student['success'] or not student['data'].get('face_feature_2'):
        return {"success": False, "message": '未注册人脸特征'}
    
    #  = np.frombuffer(student['data']['face_feature_2'], dtype=np.float32)
    feature_response = db.get_student_face_feature(student_id,"deepface")
    if not feature_response['success']:
        return {"success": False, "message": f"获取特征失败: {feature_response['message']}"}

    # 从响应中提取实际的特征数据
    db_feature_bytes = feature_response['feature']
    print(f"数据库特征changdu: {len(db_feature_bytes)}")
    try:
        db_feature = np.frombuffer(db_feature_bytes, dtype=np.float32)
    except Exception as e:
        return {"success": False, "message": f"特征转换失败: {str(e)}"}

    # 验证维度（必须为512）
    if db_feature.shape[0] != 512:
        return {"success": False, "message": f"数据库特征维度错误，实际为{db_feature.shape[0]}，应为512"}

    # 4. 比对
    compare_result = deepface_model.compare_features(
        feature_result['feature_data'], 
        db_feature  # 传递正确的特征向量
    )
    print(f"比对结果: {compare_result}")
    # print(compare_result)
    if not compare_result['success'] or not compare_result['is_match']:
        return {"success": False, "message": '人脸比对失败或不匹配'}
    # 5. 记录考勤
    db.record_attendance(
        student_id=student_id,
        liveness_score=liveness_result.get('liveness_list', [{}])[0].get('score', 0),
        detection_method='deepface',
        similarity=compare_result.get('similarity', 0),
        status=None,
        
    )
    
    return {"success": True, "message": "打卡成功", "student": {"student_id": student_id, "name": student['data']['name']}}

@app.post("/api/attendance/silence", tags=["考勤管理"])
async def record_attendance_silence(
    image: UploadFile = File(...),
    student_id: str = Form(...)
):
    """基于静默活体检测方案的考勤打卡"""
    if silence_model is None:
        return {"success": False, "message": "静默活体检测模型未正确初始化"}
    image_path = save_upload_file(image)
    # 1. 活体检测
    liveness_result = silence_model.detect_liveness(image_path)
    print(f"活体检测结果: {liveness_result}")
    
    if not liveness_result['success'] or not liveness_result['is_live']:
        os.remove(image_path)
        
        return {"success": False, "message": '活体检测未通过'}
    # 2. 特征提取
    feature_result = silence_model.extract_feature(image_path)
    os.remove(image_path)
    if not feature_result['success']:
        return {"success": False, "message": feature_result.get('message', '特征提取失败')}
    # 3. 获取学生静默特征（face_feature_3）
    student = db.get_student(student_id)
    if not student['success'] or not student['data'].get('face_feature_3'):
        return {"success": False, "message": '未注册静默人脸特征（face_feature_3）'}
    db_feature_bytes = student['data']['face_feature_3']
    try:
        db_feature = np.frombuffer(db_feature_bytes, dtype=np.float32)
    except Exception as e:
        return {"success": False, "message": f"特征转换失败: {str(e)}"}
    # 4. 比对
    compare_result = silence_model.compare_features(
        feature_result['feature_data'],
        db_feature
    )
    if not compare_result['success'] or not compare_result['is_match']:
        return {"success": False, "message": '人脸比对失败或不匹配', "similarity": compare_result.get('similarity', 0.0)}
    # 5. 记录考勤
    db.record_attendance(
        student_id=student_id,
        liveness_score=liveness_result.get('liveness_score', 0),
        detection_method='silence',
        similarity=compare_result.get('similarity', 0),
        status=None,
    )
    return {"success": True, "message": "打卡成功", "student": {"student_id": student_id, "name": student['data']['name']}}

# 获取考勤记录
@app.get("/api/attendance", tags=["考勤管理"])
async def get_attendance(
    student_id: Optional[str] = None,
    start_date: Optional[str] = None,  # 新增：开始日期
    end_date: Optional[str] = None,    # 新增：结束日期
    method: Optional[str] = None,
    class_name: Optional[str] = None
):
    """获取考勤记录"""
    result = db.get_attendance_records(student_id, start_date, end_date, method, class_name)
    return result

# 获取考勤统计
@app.get("/api/attendance/statistics", tags=["考勤管理"])
async def get_attendance_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    class_name: Optional[str] = None
):
    """获取考勤统计数据"""
    result = db.get_attendance_statistics(start_date, end_date, class_name)
    return result

# 获取SDK版本信息
@app.get("/api/system/sdk-info", tags=["系统管理"])
async def get_sdk_info(token_data: TokenData = Depends(check_teacher_role)):
    """获取SDK版本信息"""
    if arc_face is None:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "虹软SDK未正确初始化"}
        )
    
    version_info = arc_face.get_version()
    return {
        "success": True,
        "data": {
            "sdk_name": "ArcSoft Face SDK",
            "version": version_info
        }
    }

# 实时识别API
def read_imagefile(file) -> np.ndarray:
    image = np.frombuffer(file, np.uint8)
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)
    return img

@app.post("/api/face-recognize", tags=["实时识别"])
async def face_recognize_api(
    image: UploadFile = File(...),
    student_id: str = Form(None)
):
    img_bytes = await image.read()
    img = read_imagefile(img_bytes)
    if img is None:
        return JSONResponse(status_code=400, content={"success": False, "message": "无法读取图片"})
    # 活体检测
    liveness_result = arc_face.detect_liveness_from_numpy(img)
    liveness_score = liveness_result.get("is_live")
    
    # 特征提取
    feature_result = arc_face.extract_feature_from_numpy(img)
    if not feature_result["success"]:
        return {"success": False, "message": feature_result.get("message", "特征提取失败")}
    current_feature = feature_result["feature_data"]
    similarity_threshold = 0.8
    # 1. 指定student_id精确比对
    if student_id:
        db_feature_result = db.get_student_face_feature(student_id, "arcsoft")
        if not db_feature_result["success"]:
            return {
                "success": False,
                "message": "该学生未注册人脸特征，无法识别"
            }
        compare_result = arc_face.compare_features(current_feature, db_feature_result["feature"])
        if not compare_result["success"] or compare_result["similarity"] < similarity_threshold:
            return {
                "success": False,
                "message": "人脸比对失败或不匹配",
                "similarity": compare_result.get("similarity", 0.0)
            }
        student_info = db.get_student(student_id)
        return {
            "success": True,
            "name": student_info["data"]["name"] if student_info["success"] else None,
            "student_id": student_id,
            "liveness_score": liveness_score,
            "similarity": compare_result["similarity"]
        }
    # # 2. 全库比对，返回最相似学生
    # best_match = None
    # best_similarity = 0
    # best_student = None
    # all_students = db.get_all_students()
    # for stu in all_students.get("data", []):
    #     stu_id = stu.get("student_id")
    #     if not stu_id:
    #         continue
    #     db_feature_result = db.get_student_face_feature(stu_id, "arcsoft")
    #     if not db_feature_result["success"]:
    #         continue
    #     compare_result = arc_face.compare_features(current_feature, db_feature_result["feature"])
    #     if compare_result["success"] and compare_result["similarity"] > best_similarity:
    #         best_similarity = compare_result["similarity"]
    #         best_match = stu_id
    #         best_student = stu
    # if best_match and best_similarity > similarity_threshold:
    #     return {
    #         "success": True,
    #         "name": best_student.get("name"),
    #         "student_id": best_match,
    #         "liveness_score": liveness_score,
    #         "similarity": best_similarity
    #     }
    # else:
    #     return {
    #         "success": False,
    #         "message": "未找到匹配学生",
    #         "liveness_score": liveness_score
    #     }

# 交互式活体检测API
@app.post("/api/interactive-liveness", tags=["活体检测"])
async def interactive_liveness(
    image: UploadFile = File(...),
    session_id: str = Form(...),
):
    img_bytes = await image.read()
    img_array = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse(status_code=400, content={"success": False, "message": "无法读取图片"})

    session = get_session(session_id)
    if not session:
        steps = get_random_steps()
        # 保存最开始的那一帧
        _, first_buffer = cv2.imencode('.jpg', frame)
        first_frame_b64 = base64.b64encode(first_buffer).decode()
        session = {
            "steps": steps,
            "current": 0,
            "done": [False] * len(steps),
            "blink_count": 0,
            "mouth_count": 0,
            "nod_count": 0,
            "shake_count": 0,
            "compare_point": None,
            "last_frame": None,
            "first_frame": first_frame_b64,  # 只保存第一帧
            "start_time": time.time(),
            "reflection_detected": False
        }
    
    # img = read_imagefile(img_bytes)
    # liveness_result = arc_face.detect_liveness_from_numpy(img)
    # liveness_score = liveness_result.get("is_live")
    # if not liveness_result["success"] or not liveness_result.get("is_live", False):
    #     return JSONResponse(status_code=400, content={"success": False, "message": "活体检测不通过，检测到视频攻击，请使用真实人脸"})
    # 超时检测
    if "start_time" in session and (time.time() - session["start_time"] > 20):
        set_session(session_id, session)
        return JSONResponse(status_code=400, content={"success": False, "message": "操作超时，请重新开始"})

    # 反射检测
    if not session.get("reflection_detected", False):
        if check_reflection(frame):
            session["reflection_detected"] = True
            set_session(session_id, session)
            return JSONResponse(status_code=400, content={"success": False, "message": "检测到屏幕反射/视频攻击，请使用真实人脸"})

    steps = session["steps"]
    current = session["current"]
    done = session["done"]
    compare_point = session.get("compare_point")

    # dlib人脸检测
    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(img_gray, 0)
    step_name = steps[current]["name"]
    step_text = steps[current]["text"]
    passed = False
    msg = ""

    if len(faces) == 1:
        landmarks = np.array([[p.x, p.y] for p in predictor(frame, faces[0]).parts()])
        size = frame.shape
        # 眨眼
        if step_name == "blink":
            blinked, t_ear = detect_blink(landmarks)
            if blinked:
                session["blink_count"] += 1
            if session["blink_count"] >= EYE_AR_CONSEC_FRAMES:
                passed = True
                msg = "眨眼通过"
        # 张嘴
        elif step_name == "mouth":
            mouthed, mar = detect_mouth(landmarks)
            if mouthed:
                session["mouth_count"] += 1
            if session["mouth_count"] >= MOUTH_AR_CONSEC_FRAMES:
                passed = True
                msg = "张嘴通过"
        # 点头
        elif step_name == "nod":
            nose_points = landmarks[32:36]
            nose_center = nose_points.mean(axis=0)
            nodded, nod_value = detect_nod(size, nose_center, compare_point)
            if nodded:
                session["nod_count"] += 1
            session["compare_point"] = nose_center.tolist()
            if session["nod_count"] >= NOD_CONSEC_FRAMES:
                passed = True
                msg = "点头通过"
        # 摇头
        elif step_name == "shake":
            nose_points = landmarks[32:36]
            nose_center = nose_points.mean(axis=0)
            shaked, shake_value = detect_shake(size, nose_center, compare_point)
            if shaked:
                session["shake_count"] += 1
            session["compare_point"] = nose_center.tolist()
            if session["shake_count"] >= SHAKE_CONSEC_FRAMES:
                passed = True
                msg = "摇头通过"
    else:
        msg = "未检测到单个人脸，请正对摄像头"

    if passed:
        done[current] = True
        session["current"] += 1
        session["blink_count"] = 0
        session["mouth_count"] = 0
        session["nod_count"] = 0
        session["shake_count"] = 0
        session["compare_point"] = None

    all_passed = all(done)
    last_frame_b64 = None
    if all_passed:
        last_frame_b64 = session.get("first_frame")
        session["last_frame"] = last_frame_b64

    set_session(session_id, session)

    resp = {
        "success": True,
        "current_step": steps[session["current"]]["name"] if not all_passed else None,
        "current_text": steps[session["current"]]["text"] if not all_passed else "全部通过",
        "steps": [{"name": s["name"], "text": s["text"], "done": d} for s, d in zip(steps, done)],
        "all_passed": all_passed,
        "msg": msg,
        "last_frame": last_frame_b64 if all_passed else None
    }
    return resp

# 主函数
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8090, reload=True)
