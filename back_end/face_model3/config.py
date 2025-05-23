# -*- coding: utf-8 -*-
import os
from pathlib import Path

# 基础路径配置
BASE_DIR = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "models"          # 模型存放目录
DATA_DIR = BASE_DIR / "data"             # 数据存储目录

# 创建必要目录
MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# InsightFace 模型配置
FACE_MODEL_NAME = "buffalo_l"            # 使用的大模型名称
FACE_DET_THRESH = 0.6                    # 人脸检测阈值
FACE_REC_THRESH = 0.8                    # 人脸识别相似度阈值

# 数据库配置
DATABASE_URL = "sqlite:///attendance.db"  # SQLite数据库路径

# 活体检测阈值
LIVENESS_THRESHOLD = 0.8                 # 活体检测分数阈值