# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import numpy as np
import json
from config import DATABASE_URL

Base = declarative_base()


class Student(Base):
    """学生信息表"""
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    student_id = Column(String(50), unique=True, nullable=False)  # 学号
    name = Column(String(100), nullable=False)  # 姓名
    class_name = Column(String(100))  # 班级
    face_feature = Column(String(2000))  # 人脸特征(JSON序列化)
    created_at = Column(DateTime, default=datetime.now)


class AttendanceRecord(Base):
    """考勤记录表"""
    __tablename__ = 'attendance'

    id = Column(Integer, primary_key=True)
    student_id = Column(String(50), nullable=False)  # 学号
    timestamp = Column(DateTime, default=datetime.now)  # 考勤时间
    liveness_score = Column(Float)  # 活体检测分数
    similarity = Column(Float)  # 匹配相似度
    status = Column(String(20))  # 考勤状态（正常/迟到/缺勤）
    method = Column(String(50))  # 识别方法


# 初始化数据库
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DatabaseManager:
    def __init__(self):
        self.session = SessionLocal()

    def register_student(self, student_id: str, name: str, face_feature: np.ndarray, class_name: str = None) -> dict:
        """
        注册学生人脸信息
        :param student_id: 学号
        :param name: 姓名
        :param face_feature: 人脸特征向量
        :param class_name: 班级名称
        :return: 操作结果
        """
        try:
            # 序列化特征向量
            feature_json = json.dumps(face_feature.tolist())

            student = Student(
                student_id=student_id,
                name=name,
                class_name=class_name,
                face_feature=feature_json
            )
            self.session.add(student)
            self.session.commit()
            return {"success": True, "student_id": student_id}
        except Exception as e:
            self.session.rollback()
            return {"success": False, "message": f"注册失败: {str(e)}"}

    def get_all_students(self) -> dict:
        """获取所有学生信息"""
        try:
            students = self.session.query(Student).all()
            return {
                "success": True,
                "data": [
                    {
                        "student_id": s.student_id,
                        "name": s.name,
                        "class_name": s.class_name,
                        "feature": json.loads(s.face_feature) if s.face_feature else None
                    } for s in students
                ]
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def record_attendance(self, student_id: str, liveness_score: float, detection_method: str,
                          similarity: float) -> dict:
        """
        记录考勤信息
        :param student_id: 学号
        :param liveness_score: 活体检测分数
        :param detection_method: 识别方法
        :param similarity: 匹配相似度
        :return: 操作结果
        """
        try:
            # 自动判断考勤状态（示例逻辑，需根据实际规则调整）
            current_time = datetime.now().time()
            if current_time.hour > 9:
                status = "迟到"
            else:
                status = "正常"

            record = AttendanceRecord(
                student_id=student_id,
                liveness_score=liveness_score,
                method=detection_method,
                similarity=similarity,
                status=status
            )
            self.session.add(record)
            self.session.commit()
            return {"success": True, "record_id": record.id}
        except Exception as e:
            self.session.rollback()
            return {"success": False, "message": str(e)}


# 全局数据库实例
db_manager = DatabaseManager()