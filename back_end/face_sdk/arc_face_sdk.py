"""
虹软ArcSoft人脸识别SDK Python封装
使用ctypes调用SDK的DLL函数实现人脸检测、活体检测等功能
"""
import os
import sys
import ctypes
from ctypes import c_void_p, c_char_p, c_ubyte, c_int, c_uint32, c_float, c_int32, POINTER, Structure, Union, pointer, cast
import numpy as np
import cv2
import platform
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ArcFaceSDK")

# 确定当前平台系统位数
IS_64 = sys.maxsize > 2**32

# 常量定义 - 从 arcsoft_face_sdk.h 提取
ASF_NONE = 0x00000000  # 无属性
ASF_FACE_DETECT = 0x00000001  # 人脸检测
ASF_FACERECOGNITION = 0x00000004  # 人脸特征
ASF_AGE = 0x00000008  # 年龄
ASF_GENDER = 0x00000010  # 性别
ASF_FACE3DANGLE = 0x00000020  # 3D角度
ASF_LIVENESS = 0x00000080  # RGB活体
ASF_IR_LIVENESS = 0x00000400  # IR活体

# 图像数据格式
ASVL_PAF_RGB24_B8G8R8 = 0x201  # BGR24位图像
ASVL_PAF_GRAY = 0x701  # 灰度图像

# 人脸检测模式
ASF_DETECT_MODE_IMAGE = 0x00000000  # 图像模式
ASF_DETECT_MODE_VIDEO = 0x00000001  # 视频模式

# 检测角度
ASF_OP_0_ONLY = 0x1  # 仅检测0度
ASF_OP_90_ONLY = 0x2  # 仅检测90度
ASF_OP_270_ONLY = 0x3  # 仅检测270度
ASF_OP_180_ONLY = 0x4  # 仅检测180度
ASF_OP_ALL_OUT = 0x5  # 全角度检测

# 错误码
MOK = 0  # 成功
MERR_ASF_ALREADY_ACTIVATED = 90114  # SDK已激活

# 定义C结构体
class MRECT(Structure):
    """人脸框结构体"""
    _fields_ = [
        ('left', c_int32),     # 左上角横坐标
        ('top', c_int32),      # 左上角纵坐标
        ('right', c_int32),    # 右下角横坐标
        ('bottom', c_int32),   # 右下角纵坐标
    ]

class ASF_VERSION(Structure):
    """版本信息结构体"""
    _fields_ = [
        ('Version', c_char_p),  # 版本号
        ('BuildDate', c_char_p),  # 构建日期
        ('CopyRight', c_char_p),  # 版权信息
    ]
    
class ASF_SingleFaceInfo(Structure):
    """单人脸信息结构体"""
    _fields_ = [
        ('faceRect', MRECT),  # 人脸框
        ('faceOrient', c_int32),  # 人脸角度
    ]

class ASF_MultiFaceInfo(Structure):
    """多人脸信息结构体"""
    _fields_ = [
        ('faceRect', POINTER(MRECT)),  # 人脸框数组
        ('faceOrient', POINTER(c_int32)),  # 人脸角度数组
        ('faceNum', c_int32),  # 人脸数
        ('faceID', POINTER(c_int32)),  # 人脸ID数组
    ]

class ASF_FaceFeature(Structure):
    """人脸特征结构体"""
    _fields_ = [
        ('feature', c_void_p),  # 特征数据
        ('featureSize', c_int32),  # 特征大小
    ]

class ASF_LivenessInfo(Structure):
    """活体信息结构体（官方文档：isLive为MInt32*，即c_int32*）"""
    _fields_ = [
        ('isLive', POINTER(c_int32)),  # 活体状态数组（0:非真人，1:真人，-1~-5:异常）
        ('num', c_int32),
    ]

class ASF_ImageData(Structure):
    """图像数据结构体"""
    _fields_ = [
        ('u32PixelArrayFormat', c_uint32),  # 像素格式
        ('i32Width', c_int32),  # 图像宽度
        ('i32Height', c_int32),  # 图像高度
        ('pi32Pitch', c_int32 * 4),  # 图像步长
        ('ppu8Plane', POINTER(c_ubyte) * 4),  # 图像数据
    ]

class ASF_LivenessThreshold(Structure):
    _fields_ = [
        ('thresholdmodel_BGR', c_float),
        ('thresholdmodel_IR', c_float)
    ]

class ArcFaceSDK:
    """
    虹软ArcSoft人脸识别SDK Python封装类
    实现了SDK初始化、人脸检测、特征提取和活体检测等功能
    """
    def __init__(self, app_id=None, sdk_key=None, lib_path=None):
        """
        初始化SDK
        
        Args:
            app_id: SDK授权APP_ID
            sdk_key: SDK授权密钥
            lib_path: SDK库文件路径，默认自动查找
        """
        self.app_id = app_id or b''  # 
        self.sdk_key = sdk_key or b''  # 
        self.handle = c_void_p()
        self.mask = ASF_FACE_DETECT | ASF_FACERECOGNITION | ASF_LIVENESS
        self.lib = None
        self.active = False
        
        # 确定库文件路径
        if lib_path:
            self.lib_path = lib_path
        else:
            # 自动查找库文件
            sdk_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.lib_path = os.path.join(sdk_path, 'libarcsoft_face_engine.dll')
            
            # 如果找不到库文件，尝试从ArcSoft目录查找
            if not os.path.exists(self.lib_path):
                arc_path = os.path.join(sdk_path, 'ArcSoft', 'lib', 'X64' if IS_64 else 'Win32', 'libarcsoft_face_engine.dll')
                if os.path.exists(arc_path):
                    self.lib_path = arc_path
                
        if not os.path.exists(self.lib_path):
            raise FileNotFoundError(f"无法找到SDK库文件: {self.lib_path}")
        
        # 加载动态链接库
        try:
            self.lib = ctypes.CDLL(self.lib_path)
            logger.info(f"成功加载SDK库: {self.lib_path}")
        except Exception as e:
            logger.error(f"加载SDK库失败: {str(e)}")
            raise
        
        # 初始化SDK函数
        self._init_functions()
        
        # 激活SDK
        self.activate()
        
        # 初始化引擎
        self.init_engine()
    
    def _init_functions(self):
        """初始化SDK函数"""
        # 激活SDK
        self.ASFActivation = self.lib.ASFActivation
        self.ASFActivation.restype = c_int
        self.ASFActivation.argtypes = (c_char_p, c_char_p)
        
        # 初始化引擎
        self.ASFInitEngine = self.lib.ASFInitEngine
        self.ASFInitEngine.restype = c_int
        self.ASFInitEngine.argtypes = (c_uint32, c_int32, c_int32, c_int32, c_int32, POINTER(c_void_p))
        
        # 人脸检测
        self.ASFDetectFaces = self.lib.ASFDetectFaces
        self.ASFDetectFaces.restype = c_int
        self.ASFDetectFaces.argtypes = (c_void_p, c_int32, c_int32, c_int32, POINTER(c_ubyte), POINTER(ASF_MultiFaceInfo))
        
        # 预处理
        self.ASFProcess = self.lib.ASFProcess
        self.ASFProcess.restype = c_int
        self.ASFProcess.argtypes = (c_void_p, c_int32, c_int32, c_int32, POINTER(c_ubyte), POINTER(ASF_MultiFaceInfo), c_int32)
        
        # 活体检测
        self.ASFGetLivenessScore = self.lib.ASFGetLivenessScore
        self.ASFGetLivenessScore.restype = c_int
        self.ASFGetLivenessScore.argtypes = (c_void_p, POINTER(ASF_LivenessInfo))
        
        # 设置活体阈值
        self.ASFSetLivenessParam = self.lib.ASFSetLivenessParam
        self.ASFSetLivenessParam.restype = c_int
        self.ASFSetLivenessParam.argtypes = (c_void_p, POINTER(ASF_LivenessThreshold))
        
        # 提取人脸特征
        self.ASFFaceFeatureExtract = self.lib.ASFFaceFeatureExtract
        self.ASFFaceFeatureExtract.restype = c_int
        self.ASFFaceFeatureExtract.argtypes = (c_void_p, c_int32, c_int32, c_int32, POINTER(c_ubyte), POINTER(ASF_SingleFaceInfo), POINTER(ASF_FaceFeature))
        
        # 人脸特征比对
        self.ASFFaceFeatureCompare = self.lib.ASFFaceFeatureCompare
        self.ASFFaceFeatureCompare.restype = c_int
        self.ASFFaceFeatureCompare.argtypes = (c_void_p, POINTER(ASF_FaceFeature), POINTER(ASF_FaceFeature), POINTER(c_float))
        
        # 释放引擎
        self.ASFUninitEngine = self.lib.ASFUninitEngine
        self.ASFUninitEngine.restype = c_int
        self.ASFUninitEngine.argtypes = (c_void_p,)
        
        # 获取版本信息
        self.ASFGetVersion = self.lib.ASFGetVersion
        self.ASFGetVersion.restype = ASF_VERSION
        self.ASFGetVersion.argtypes = (c_void_p,)
    
    def activate(self):
        """激活SDK"""
        if self.active:
            return True
            
        ret = self.ASFActivation(self.app_id, self.sdk_key)
        if ret != MOK and ret != MERR_ASF_ALREADY_ACTIVATED:
            logger.error(f"SDK激活失败，错误码: {ret}")
            return False
            
        logger.info("SDK激活成功")
        self.active = True
        return True
    
    def init_engine(self):
        """初始化引擎"""
        ret = self.ASFInitEngine(ASF_DETECT_MODE_IMAGE, ASF_OP_0_ONLY, 30, 5, self.mask, pointer(self.handle))
        if ret != MOK:
            logger.error(f"引擎初始化失败，错误码: {ret}")
            return False
            
        logger.info("引擎初始化成功")
        # 初始化后立即设置活体阈值
        self.set_liveness_threshold(rgb=0.4, ir=0.6)
        return True
    
    def set_liveness_threshold(self, rgb=0.4, ir=0.6):
        threshold = ASF_LivenessThreshold()
        threshold.thresholdmodel_BGR = c_float(rgb)
        threshold.thresholdmodel_IR = c_float(ir)
        ret = self.ASFSetLivenessParam(self.handle, pointer(threshold))
        if ret != MOK:
            logger.error(f"设置活体阈值失败，错误码: {ret}")
            return False
        logger.info(f"设置活体阈值成功，RGB: {rgb}, IR: {ir}")
        self.liveness_rgb_threshold = rgb
        self.liveness_ir_threshold = ir
        return True
    
    def get_version(self):
        """获取SDK版本信息"""
        version_info = self.ASFGetVersion(self.handle)
        return {
            'version': version_info.Version.decode('utf-8') if version_info.Version else "",
            'build_date': version_info.BuildDate.decode('utf-8') if version_info.BuildDate else "",
            'copyright': version_info.CopyRight.decode('utf-8') if version_info.CopyRight else ""
        }
    
    def detect_faces(self, image_path):
        """
        检测图像中的人脸
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            dict: 人脸检测结果
        """
        try:
            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                return {"success": False, "message": "无法读取图像"}
                
            return self.detect_faces_from_numpy(img)
        except Exception as e:
            logger.error(f"人脸检测异常: {str(e)}")
            return {"success": False, "message": f"人脸检测异常: {str(e)}"}
    
    def detect_faces_from_numpy(self, img, return_landmarks=False):
        """
        从numpy数组中检测人脸，并可选返回人脸框和关键点
        Args:
            img: numpy格式的图像数据
            return_landmarks: 是否返回人脸框坐标（用于前端实时绘制）
        Returns:
            dict: 人脸检测结果
        """
        try:
            # 确保图像是BGR格式
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            height, width = img.shape[:2]
            img_data = ASF_ImageData()
            img_data.u32PixelArrayFormat = ASVL_PAF_RGB24_B8G8R8
            img_data.i32Width = width
            img_data.i32Height = height
            img_data.pi32Pitch[0] = width * 3
            img_data.ppu8Plane[0] = img.ctypes.data_as(POINTER(c_ubyte))
            multi_face_info = ASF_MultiFaceInfo()
            ret = self.ASFDetectFaces(
                self.handle, 
                width, 
                height, 
                ASVL_PAF_RGB24_B8G8R8, 
                img_data.ppu8Plane[0], 
                pointer(multi_face_info)
            )
            if ret != MOK:
                return {"success": False, "message": f"人脸检测失败，错误码: {ret}"}
            face_count = multi_face_info.faceNum
            if face_count <= 0:
                return {"success": True, "face_count": 0, "message": "未检测到人脸", "faces": []}
            faces = []
            for i in range(face_count):
                face_rect = multi_face_info.faceRect[i]
                face_orient = multi_face_info.faceOrient[i] if multi_face_info.faceOrient else 0
                face_id = multi_face_info.faceID[i] if multi_face_info.faceID else 0
                face_info = {
                    "rect": {
                        "left": int(face_rect.left),
                        "top": int(face_rect.top),
                        "right": int(face_rect.right),
                        "bottom": int(face_rect.bottom),
                        "width": int(face_rect.right - face_rect.left),
                        "height": int(face_rect.bottom - face_rect.top)
                    },
                    "orient": int(face_orient),
                    "face_id": int(face_id)
                }
                if return_landmarks:
                    face_info["landmarks"] = None  # 可扩展支持关键点
                faces.append(face_info)
            return {
                "success": True,
                "face_count": face_count,
                "message": f"检测到{face_count}个人脸",
                "faces": faces,
                "raw_info": multi_face_info
            }
        except Exception as e:
            logger.error(f"人脸检测异常: {str(e)}")
            return {"success": False, "message": f"人脸检测异常: {str(e)}"}

    def detect_liveness(self, image_path):
        """
        检测图像中的人脸活体
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            dict: 活体检测结果
        """
        try:
            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                return {"success": False, "message": "无法读取图像"}
                
            # 检测人脸
            face_result = self.detect_faces_from_numpy(img)
            if not face_result["success"]:
                return face_result
                
            if face_result["face_count"] == 0:
                return {"success": False, "message": "未检测到人脸，无法进行活体检测"}
            
            # 获取图像信息
            height, width = img.shape[:2]
            
            # 创建图像数据结构
            img_data = ASF_ImageData()
            img_data.u32PixelArrayFormat = ASVL_PAF_RGB24_B8G8R8
            img_data.i32Width = width
            img_data.i32Height = height
            img_data.pi32Pitch[0] = width * 3
            img_data.ppu8Plane[0] = img.ctypes.data_as(POINTER(c_ubyte))
            
            # 获取多人脸信息
            multi_face_info = face_result["raw_info"]
            
            # 进行预处理，提取活体信息
            ret = self.ASFProcess(
                self.handle,
                width,
                height,
                ASVL_PAF_RGB24_B8G8R8,
                img_data.ppu8Plane[0],
                pointer(multi_face_info),
                ASF_LIVENESS
            )
            
            if ret != MOK:
                return {"success": False, "message": f"活体检测预处理失败，错误码: {ret}"}
            
            # 获取活体信息
            liveness_info = ASF_LivenessInfo()
            ret = self.ASFGetLivenessScore(self.handle, pointer(liveness_info))
            
            if ret != MOK:
                return {"success": False, "message": f"获取活体检测结果失败，错误码: {ret}"}
            
            # 处理活体检测结果
            liveness_count = liveness_info.num
            if liveness_count <= 0:
                return {"success": False, "message": "未获取到活体信息"}
            
            # 获取每个人脸的活体信息
            liveness_list = []
            
            for i in range(liveness_count):
                status = liveness_info.isLive[i]
                is_live = int(status) == 1
                liveness_list.append({
                    "status_code": int(status),
                    "is_live": is_live,
                    "status": "真人" if is_live else f"非真人/异常({status})"
                })
            
            # 总体结果判断：只要有一个是真人，就认为有真人
            any_live = any(item["is_live"] for item in liveness_list)
            
            return {
                "success": True,
                "method": "arcsoft",
                "is_live": any_live,
                "message": "检测到真人" if any_live else "未检测到真人",
                "liveness_count": liveness_count,
                "liveness_list": liveness_list,
                "faces": face_result["faces"]
            }
            
        except Exception as e:
            logger.error(f"活体检测异常: {str(e)}")
            return {"success": False, "message": f"活体检测异常: {str(e)}"}

    def detect_liveness_from_numpy(self, img):
        """
        直接从numpy数组检测活体（用于视频流实时识别）
        Args:
            img: numpy格式的图像数据
        Returns:
            dict: 活体检测结果
        """
        try:
            face_result = self.detect_faces_from_numpy(img)
            if not face_result["success"]:
                return face_result
            if face_result["face_count"] == 0:
                return {"success": False, "message": "未检测到人脸，无法进行活体检测"}
            height, width = img.shape[:2]
            img_data = ASF_ImageData()
            img_data.u32PixelArrayFormat = ASVL_PAF_RGB24_B8G8R8
            img_data.i32Width = width
            img_data.i32Height = height
            img_data.pi32Pitch[0] = width * 3
            img_data.ppu8Plane[0] = img.ctypes.data_as(POINTER(c_ubyte))
            multi_face_info = face_result["raw_info"]
            ret = self.ASFProcess(
                self.handle,
                width,
                height,
                ASVL_PAF_RGB24_B8G8R8,
                img_data.ppu8Plane[0],
                pointer(multi_face_info),
                ASF_LIVENESS
            )
            if ret != MOK:
                return {"success": False, "message": f"活体检测预处理失败，错误码: {ret}"}
            liveness_info = ASF_LivenessInfo()
            ret = self.ASFGetLivenessScore(self.handle, pointer(liveness_info))
            if ret != MOK:
                return {"success": False, "message": f"获取活体检测结果失败，错误码: {ret}"}
            liveness_count = liveness_info.num
            if liveness_count <= 0:
                return {"success": False, "message": "未获取到活体信息"}
            liveness_list = []
            for i in range(liveness_count):
                status = liveness_info.isLive[i]
                is_live = int(status) == 1
                liveness_list.append({
                    "status_code": int(status),
                    "is_live": is_live,
                    "status": "真人" if is_live else f"非真人/异常({status})"
                })
            any_live = any(item["is_live"] for item in liveness_list)
            return {
                "success": True,
                "method": "arcsoft",
                "is_live": any_live,
                "message": "检测到真人" if any_live else "未检测到真人",
                "liveness_count": liveness_count,
                "liveness_list": liveness_list,
                "faces": face_result["faces"]
            }
        except Exception as e:
            logger.error(f"活体检测异常: {str(e)}")
            return {"success": False, "message": f"活体检测异常: {str(e)}"}

    def extract_feature(self, image_path):
        """
        提取人脸特征
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            dict: 特征提取结果
        """
        try:
            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                return {"success": False, "message": "无法读取图像"}
                
            # 检测人脸
            face_result = self.detect_faces_from_numpy(img)
            if not face_result["success"]:
                return face_result
                
            if face_result["face_count"] == 0:
                return {"success": False, "message": "未检测到人脸，无法提取特征"}
            
            # 获取图像信息
            height, width = img.shape[:2]
            
            # 创建图像数据结构
            img_data = ASF_ImageData()
            img_data.u32PixelArrayFormat = ASVL_PAF_RGB24_B8G8R8
            img_data.i32Width = width
            img_data.i32Height = height
            img_data.pi32Pitch[0] = width * 3
            img_data.ppu8Plane[0] = img.ctypes.data_as(POINTER(c_ubyte))
            
            # 获取单人脸信息（取第一个人脸）
            face_info = face_result["faces"][0]
            rect = face_info["rect"]
            orient = face_info["orient"]
            
            # 创建单人脸结构
            single_face_info = ASF_SingleFaceInfo()
            single_face_info.faceRect.left = rect["left"]
            single_face_info.faceRect.top = rect["top"]
            single_face_info.faceRect.right = rect["right"]
            single_face_info.faceRect.bottom = rect["bottom"]
            single_face_info.faceOrient = orient
            
            # 创建特征结构
            face_feature = ASF_FaceFeature()
            
            # 提取特征
            ret = self.ASFFaceFeatureExtract(
                self.handle,
                width,
                height,
                ASVL_PAF_RGB24_B8G8R8,
                img_data.ppu8Plane[0],
                pointer(single_face_info),
                pointer(face_feature)
            )
            
            if ret != MOK:
                return {"success": False, "message": f"特征提取失败，错误码: {ret}"}
            
            # 将特征数据转换为Python字节串
            feature_size = face_feature.featureSize
            feature_data = ctypes.string_at(face_feature.feature, feature_size)
            
            return {
                "success": True,
                "message": "特征提取成功",
                "feature_size": feature_size,
                "feature_data": feature_data
            }
            
        except Exception as e:
            logger.error(f"特征提取异常: {str(e)}")
            return {"success": False, "message": f"特征提取异常: {str(e)}"}

    def extract_feature_from_numpy(self, img):
        """
        从numpy数组提取人脸特征（用于视频流实时识别）
        Args:
            img: numpy格式的图像数据
        Returns:
            dict: 特征提取结果
        """
        try:
            face_result = self.detect_faces_from_numpy(img)
            if not face_result["success"]:
                return face_result
            if face_result["face_count"] == 0:
                return {"success": False, "message": "未检测到人脸，无法提取特征"}
            height, width = img.shape[:2]
            img_data = ASF_ImageData()
            img_data.u32PixelArrayFormat = ASVL_PAF_RGB24_B8G8R8
            img_data.i32Width = width
            img_data.i32Height = height
            img_data.pi32Pitch[0] = width * 3
            img_data.ppu8Plane[0] = img.ctypes.data_as(POINTER(c_ubyte))
            face_info = face_result["faces"][0]
            rect = face_info["rect"]
            orient = face_info["orient"]
            single_face_info = ASF_SingleFaceInfo()
            single_face_info.faceRect.left = rect["left"]
            single_face_info.faceRect.top = rect["top"]
            single_face_info.faceRect.right = rect["right"]
            single_face_info.faceRect.bottom = rect["bottom"]
            single_face_info.faceOrient = orient
            face_feature = ASF_FaceFeature()
            ret = self.ASFFaceFeatureExtract(
                self.handle,
                width,
                height,
                ASVL_PAF_RGB24_B8G8R8,
                img_data.ppu8Plane[0],
                pointer(single_face_info),
                pointer(face_feature)
            )
            if ret != MOK:
                return {"success": False, "message": f"特征提取失败，错误码: {ret}"}
            feature_size = face_feature.featureSize
            feature_data = ctypes.string_at(face_feature.feature, feature_size)
            return {
                "success": True,
                "message": "特征提取成功",
                "feature_size": feature_size,
                "feature_data": feature_data
            }
        except Exception as e:
            logger.error(f"特征提取异常: {str(e)}")
            return {"success": False, "message": f"特征提取异常: {str(e)}"}

    def compare_features(self, feature1, feature2):
        """
        比较两个人脸特征的相似度
        
        Args:
            feature1: 第一个特征数据
            feature2: 第二个特征数据
            
        Returns:
            dict: 比对结果
        """
        try:
            # 创建特征结构
            face_feature1 = ASF_FaceFeature()
            face_feature1.featureSize = len(feature1)
            face_feature1.feature = cast(feature1, c_void_p)
            
            face_feature2 = ASF_FaceFeature()
            face_feature2.featureSize = len(feature2)
            face_feature2.feature = cast(feature2, c_void_p)
            
            # 相似度结果
            similarity = c_float(0.0)
            
            # 比对特征
            ret = self.ASFFaceFeatureCompare(
                self.handle,
                pointer(face_feature1),
                pointer(face_feature2),
                pointer(similarity)
            )
            
            if ret != MOK:
                return {"success": False, "message": f"特征比对失败，错误码: {ret}"}
            
            similar_value = similarity.value
            # 推荐阈值为0.8
            is_same = similar_value > 0.8
            
            return {
                "success": True,
                "message": "特征比对成功",
                "similarity": similar_value,
                "is_same": is_same
            }
            
        except Exception as e:
            logger.error(f"特征比对异常: {str(e)}")
            return {"success": False, "message": f"特征比对异常: {str(e)}"}
    
    def __del__(self):
        """释放资源"""
        if hasattr(self, 'handle') and self.handle:
            try:
                self.ASFUninitEngine(self.handle)
                logger.info("ArcFace引擎资源已释放")
            except:
                pass
