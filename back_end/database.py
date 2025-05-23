"""
数据库模块，用于学生校园人脸考勤系统的数据存储和检索
使用SQLite作为存储引擎，支持多角色管理
"""
import os
import sqlite3
import datetime
import logging
import hashlib
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Database")

class AttendanceDB:
    """考勤系统数据库操作类"""
    
    def __init__(self, db_path=None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的face_attendance.db
        """
        if db_path is None:
            # 使用默认的数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'face_attendance.db')
            
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        # 行工厂设置，使查询结果作为字典返回
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,           -- 用户名
            password TEXT NOT NULL,                  -- 密码哈希
            role TEXT NOT NULL,                      -- 角色: teacher, student
            real_name TEXT NOT NULL,                 -- 真实姓名
            email TEXT,                              -- 邮箱
            phone TEXT,                              -- 电话
            avatar BLOB,                             -- 头像
            last_login TIMESTAMP,                    -- 上次登录时间
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
            status INTEGER DEFAULT 1                 -- 状态: 1-启用, 0-禁用
        )
        ''')
        
        # 创建学生表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,         -- 学生学号
            name TEXT NOT NULL,                      -- 学生姓名
            face_feature BLOB,                       -- 虹软sdk提取的人脸特征数据
            face_feature_2 BLOB,                     -- 方案2提取的人脸特征数据
            face_feature_3 BLOB,                     -- 方案3提取的人脸特征数据
            class_name TEXT,                         -- 班级名称
            user_id INTEGER,                         -- 关联用户ID
            register_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 注册时间
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 创建教师表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT UNIQUE NOT NULL,         -- 教师工号
            name TEXT NOT NULL,                      -- 教师姓名
            department TEXT,                         -- 所属部门
            position TEXT,                           -- 职位
            user_id INTEGER,                         -- 关联用户ID
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 创建班级表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE NOT NULL,         -- 班级名称
            description TEXT,                        -- 班级描述
            teacher_id INTEGER,                      -- 班主任ID
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
            FOREIGN KEY (teacher_id) REFERENCES teachers (id)
        )
        ''')
        
        # 创建考勤记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,                -- 学生学号
            check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 考勤时间
            status TEXT DEFAULT 'present',           -- 考勤状态: present, late, absent
            liveness_score REAL,                     -- 活体检测分数
            detection_method TEXT,                   -- 检测方式: arcsoft, opencv, baidu等
            similarity REAL,                         -- 人脸相似度
            remark TEXT,                             -- 备注
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
        ''')
        
        # 创建考勤规则表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,               -- 班级ID
            class_name TEXT,                         -- 班级名称
            start_time TEXT NOT NULL,                -- 开始时间
            end_time TEXT NOT NULL,                  -- 结束时间
            late_threshold INTEGER DEFAULT 15,       -- 迟到阈值(分钟)
            weekdays TEXT DEFAULT '1,2,3,4,5',       -- 适用星期，如"1,2,3,4,5"
            is_active INTEGER DEFAULT 1,             -- 是否激活: 1-是, 0-否
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 创建时间
            remark TEXT,                             -- 备注
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
        ''')
        
        
        # 创建特殊日期表(节假日、调课等)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS special_dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_value TEXT NOT NULL,                -- 日期值 YYYY-MM-DD
            type TEXT NOT NULL,                      -- 类型: holiday(节假日), workday(工作日)
            description TEXT,                        -- 描述
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 创建时间
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    #------------------------ 用户管理相关方法 ------------------------#
    
    def hash_password(self, password):
        """密码哈希加密"""
        salt = uuid.uuid4().hex
        return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt
    
    def verify_password(self, hashed_password, user_password):
        """验证密码"""
        password, salt = hashed_password.split(':')
        return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
    
    def create_user(self, password, role, real_name, email=None, phone=None, username=None):
        """
        创建用户
        
        Args:
            password: 密码
            role: 角色(teacher/student)
            real_name: 真实姓名
            email: 邮箱
            phone: 电话
            username: 用户名 (可选，默认使用真实姓名)
            
        Returns:
            dict: 创建结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 使用真实姓名作为用户名
            if not username:
                username = real_name
            
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return {
                    "success": False,
                    "message": f"用户名 {username} 已存在"
                }
            
            # 密码加密
            hashed_password = self.hash_password(password)
            
            # 添加用户
            cursor.execute(
                "INSERT INTO users (username, password, role, real_name, email, phone, create_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (username, hashed_password, role, real_name, email, phone, create_time)
            )
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"用户 {username} 创建成功",
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"创建用户异常: {str(e)}")
            return {
                "success": False,
                "message": f"创建用户异常: {str(e)}"
            }
    
    def login(self, username, password):
        """
        用户登录
        
        Args:
            username: 用户名或真实姓名
            password: 密码
            
        Returns:
            dict: 登录结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 首先尝试使用输入的值作为用户名查询
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            # 如果找不到用户名匹配的记录，尝试使用真实姓名查询
            if not user:
                cursor.execute("SELECT * FROM users WHERE real_name = ?", (username,))
                user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            # 检查用户状态
            if user['status'] != 1:
                conn.close()
                return {
                    "success": False,
                    "message": "账户已被禁用，请联系管理员"
                }
            
            # 验证密码
            if not self.verify_password(user['password'], password):
                conn.close()
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            # 更新登录时间
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (current_time, user['id'])
            )
            conn.commit()
            
            # 获取详细信息
            user_details = dict(user)
            del user_details['password']  # 删除密码信息
            
            # 根据角色获取额外信息
            if user['role'] == 'student':
                # 使用真实姓名查询学生信息，因为登录时还没有student_id
                cursor.execute("SELECT * FROM students WHERE name = ?", (user['real_name'],))
                student = cursor.fetchone()
                if student:
                    student_info = dict(student)
                    # 移除人脸特征数据，避免数据过大
                    if 'face_feature' in student_info:
                        student_info['has_face_feature'] = student_info['face_feature'] is not None
                        del student_info['face_feature']
                    user_details['student_info'] = student_info
                    # 将学生ID添加到用户信息中
                    user_details['student_id'] = student_info['student_id']
            
            elif user['role'] == 'teacher':
                cursor.execute("SELECT * FROM teachers WHERE name = ?", (user['real_name'],))
                teacher = cursor.fetchone()
                if teacher:
                    user_details['teacher_info'] = dict(teacher)
                    # 将教师ID添加到用户信息中
                    user_details['teacher_id'] = teacher['teacher_id']
            
            conn.close()
            
            return {
                "success": True,
                "message": "登录成功",
                "user": user_details
            }
            
        except Exception as e:
            logger.error(f"用户登录异常: {str(e)}")
            return {
                "success": False,
                "message": f"登录异常: {str(e)}"
            }
    
    #------------------------ 班级管理相关方法 ------------------------#
    
    def create_class(self, class_name, description=None, teacher_id=None, create_time=None):
        """
        创建班级
        
        Args:
            class_name: 班级名称
            description: 班级描述
            teacher_id: 班主任ID
            create_time: 创建时间
            
        Returns:
            dict: 创建结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 检查班级名称是否已存在
            cursor.execute("SELECT id FROM classes WHERE class_name = ?", (class_name,))
            if cursor.fetchone():
                conn.close()
                return {
                    "success": False,
                    "message": f"班级名称 {class_name} 已存在"
                }
            
            # 添加班级
            cursor.execute(
                "INSERT INTO classes (class_name, description, teacher_id, create_time) VALUES (?, ?, ?, ?)",
                (class_name, description, teacher_id, create_time)
            )
            
            class_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"班级 {class_name} 创建成功",
                "class_id": class_id
            }
            
        except Exception as e:
            logger.error(f"创建班级异常: {str(e)}")
            return {
                "success": False,
                "message": f"创建班级异常: {str(e)}"
            }
    
    def get_all_classes(self):
        """
        获取所有班级列表
        
        Returns:
            dict: 班级列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.*, t.name as teacher_name 
                FROM classes c 
                LEFT JOIN teachers t ON c.teacher_id = t.id 
                ORDER BY c.class_name
            """)
            
            classes = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return {
                "success": True,
                "data": classes
            }
            
        except Exception as e:
            logger.error(f"获取班级列表异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取班级列表异常: {str(e)}"
            }
    
    #------------------------ 考勤规则相关方法 ------------------------#
    
    def create_attendance_rule(self, class_id, start_time, end_time, late_threshold=15, 
                               weekdays="1,2,3,4,5", remark=None, is_active=1):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 获取班级名称
            cursor.execute("SELECT class_name FROM classes WHERE id = ?", (class_id,))
            class_row = cursor.fetchone()
            if not class_row:
                conn.close()
                return {
                    "success": False,
                    "message": f"班级ID {class_id} 不存在"
                }

            class_name = class_row['class_name']

            # 使用班级id作为规则id
            rule_id = class_id
            create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 检查是否已存在规则
            cursor.execute("SELECT class_id FROM attendance_rules WHERE class_id = ?", (rule_id,))
            if cursor.fetchone():
                # 更新已有规则
                cursor.execute(
                    """UPDATE attendance_rules 
                       SET start_time = ?, end_time = ?, late_threshold = ?, 
                           weekdays = ?, remark = ?, is_active = ?, create_time = ? 
                       WHERE class_id = ?""",
                    (start_time, end_time, late_threshold, weekdays, remark, is_active,create_time,  rule_id)
                )
                operation = "更新"
            else:
                # 添加新规则
                cursor.execute(
                    """INSERT INTO attendance_rules 
                      (class_id, class_name, start_time, end_time, late_threshold, 
                       weekdays, remark, is_active, create_time)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (rule_id, class_name, start_time, end_time, late_threshold, 
                     weekdays, remark, is_active, create_time)
                )
                operation = "创建"

            conn.commit()
            conn.close()

            return {
                "success": True,
                "message": f"班级 {class_name} 考勤规则{operation}成功"
            }

        except Exception as e:
            logger.error(f"创建考勤规则异常: {str(e)}")
            return {
                "success": False,
                "message": f"创建考勤规则异常: {str(e)}"
            }
    
    def get_attendance_rules(self, class_id=None):
        """
        获取考勤规则
        
        Args:
            class_id: 班级ID，不指定则获取所有规则
            
        Returns:
            dict: 考勤规则列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if class_id:
                cursor.execute(
                    """SELECT r.*, c.class_name 
                       FROM attendance_rules r
                       JOIN classes c ON r.class_id = c.id
                       WHERE r.class_id = ?""", 
                    (class_id,)
                )
                rules = [dict(row) for row in cursor.fetchall()]
            else:
                cursor.execute(
                    """SELECT r.*, c.class_name 
                       FROM attendance_rules r
                       JOIN classes c ON r.class_id = c.id
                       ORDER BY r.class_id"""
                )
                rules = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "success": True,
                "data": rules
            }
            
        except Exception as e:
            logger.error(f"获取考勤规则异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取考勤规则异常: {str(e)}"
            }
    
    def check_attendance_status(self, student_id, check_time=None):
        """
        根据考勤规则检查考勤状态
        
        Args:
            student_id: 学生ID
            check_time: 考勤时间，不指定则使用当前时间
            
        Returns:
            dict: 考勤状态
        """
        try:
            if not check_time:
                check_time = datetime.datetime.now()
            elif isinstance(check_time, str):
                check_time = datetime.datetime.strptime(check_time, "%Y-%m-%d %H:%M:%S")
            
            # 获取学生班级信息
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT class_name FROM students WHERE student_id = ?", (student_id,))
            student = cursor.fetchone()
            if not student or not student['class_name']:
                conn.close()
                return {
                    "success": False,
                    "message": f"学生 {student_id} 不存在或未分配班级"
                }
            
            class_name = student['class_name']
            
            # 获取班级ID
            cursor.execute("SELECT id FROM classes WHERE class_name = ?", (class_name,))
            class_row = cursor.fetchone()
            if not class_row:
                conn.close()
                return {
                    "success": False,
                    "message": f"学生所在班级 {class_name} 不存在"
                }
            
            class_id = class_row['id']
            
            # 获取适用的考勤规则
            cursor.execute(
                "SELECT * FROM attendance_rules WHERE id = ? AND is_active = 1", 
                (class_id,)
            )
            rule = cursor.fetchone()
            
            if not rule:
                conn.close()
                return {
                    "success": False,
                    "message": f"未找到学生所在班级的考勤规则"
                }
            
            # 检查是否是工作日
            weekday = str(check_time.weekday() + 1)  # 1-7 表示周一到周日
            weekdays = rule['weekdays'].split(',')
            if weekday not in weekdays:
                conn.close()
                return {
                    "success": True,
                    "status": "exempt",  # 免考勤日
                    "message": "今日无需考勤"
                }
            
            # 检查是否是特殊日期
            check_date = check_time.strftime("%Y-%m-%d")
            cursor.execute("SELECT * FROM special_dates WHERE date_value = ?", (check_date,))
            special_date = cursor.fetchone()
            
            if special_date and special_date['type'] == 'holiday':
                conn.close()
                return {
                    "success": True,
                    "status": "exempt",  # 免考勤日
                    "message": f"今日为{special_date['description']}，无需考勤"
                }
            
            # 解析考勤时间
            check_hour = check_time.hour
            check_minute = check_time.minute
            
            start_hour, start_minute = map(int, rule['start_time'].split(':'))
            end_hour, end_minute = map(int, rule['end_time'].split(':'))
         
            # 转换为分钟计算
            check_minutes = check_hour * 60 + check_minute
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            
            # 判断考勤状态
            late_threshold = rule['late_threshold']
            
            if check_minutes <= start_minutes:
                status = "early"  # 正常
                message = "未到打卡时间"
            
            elif check_minutes <= start_minutes + late_threshold:
                status = "present"  # 正常
                message = "正常出勤"
            elif check_minutes > start_minutes + late_threshold and check_minutes <= end_minutes:
                status = "late"
                late_minutes = check_minutes - start_minutes
                message = f"迟到 {late_minutes} 分钟"
            else:
                status = "absent"  # 缺勤
                message = "严重迟到，记为缺勤"
            logger.info(f"考勤状态: {status}, 学生ID: {student_id}, 班级: {class_name}, 考勤时间: {check_time}")
            conn.close()
            
            return {
                "success": True,
                "status": status,
                "message": message,
                "rule": dict(rule)
            }
            
        except Exception as e:
            logger.error(f"检查考勤状态异常: {str(e)}")
            return {
                "success": False,
                "message": f"检查考勤状态异常: {str(e)}"
            }
    
  
    
    #------------------------ 现有方法保留和优化 ------------------------#
    def register_student(self, student_id, name, face_feature=None, class_name=None, user_id=None, face_feature_2=None, face_feature_3=None):
        """
        注册或更新学生信息，支持多种特征方案
        
        Args:
            student_id: 学生学号
            name: 学生姓名
            face_feature: 虹软sdk特征
            class_name: 班级名称
            user_id: 关联用户ID
            face_feature_2: deepface特征
            face_feature_3: 预留
            
        Returns:
            dict: 注册结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            register_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT id FROM students WHERE student_id = ?", (student_id,))
            exists = cursor.fetchone()
            if exists:
                cursor.execute("""
                    UPDATE students SET name=?, face_feature=?, face_feature_2=?, face_feature_3=?, class_name=?, user_id=? , register_time = ? WHERE student_id=?
                """, (name, face_feature, face_feature_2, face_feature_3, class_name, user_id, register_time, student_id))
            else:
                cursor.execute("""
                    INSERT INTO students (student_id, name, face_feature, face_feature_2, face_feature_3, class_name, user_id, register_time) VALUES (?, ?, ?, ?, ?, ?, ?,?)
                """, (student_id, name, face_feature, face_feature_2, face_feature_3, class_name, user_id, register_time))
            conn.commit()
            conn.close()
            # logger.info(face_feature_2)
            return {"success": True, "message": "学生信息注册/更新成功"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def record_attendance(self, student_id, liveness_score=None, detection_method=None, 
                          similarity=None, status=None, remark=None):
        """
        记录学生考勤
        
        Args:
            student_id: 学生学号
            liveness_score: 活体检测分数
            detection_method: 检测方式
            similarity: 人脸相似度
            status: 考勤状态，如果为None则自动判断
            remark: 备注
            
        Returns:
            dict: 记录结果
        """
        try:
            # 验证学生是否存在
            student = self.get_student(student_id)
            if not student["success"]:
                return student
                
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取当前本地时间
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 如果状态为None，则根据考勤规则自动判断状态
            if status is None:
                status_result = self.check_attendance_status(student_id, current_time)
                if status_result["success"]:

                    status = status_result["status"]
                    
                    # 添加状态备注
                    if remark:
                        remark = f"{status_result['message']}; {remark}"
                    else:
                        remark = status_result['message']
                else:
                    status = "present"  # 默认为正常出勤
            
            # 记录考勤
            cursor.execute(
                """INSERT INTO attendance 
                   (student_id, check_time, status, liveness_score, detection_method, similarity, remark) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (student_id, current_time, status, liveness_score, detection_method, similarity, remark)
            )
            
            attendance_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"考勤记录成功",
                "attendance_id": attendance_id,
                "student": {
                    "student_id": student["data"].get("student_id"),
                    "name": student["data"].get("name"),
                    "class_name": student["data"].get("class_name")
                },
                "check_time": current_time,
                "status": status
            }
            
        except Exception as e:
            logger.error(f"记录考勤异常: {str(e)}")
            return {
                "success": False,
                "message": f"记录考勤异常: {str(e)}"
            }

    def get_student(self, student_id):
        """
        获取学生信息
        
        Args:
            student_id: 学生学号
            
        Returns:
            dict: 学生信息
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            student = cursor.fetchone()
            conn.close()
            
            if student:
                # 将Row对象转换为字典
                student_dict = dict(student)
                # 移除人脸特征数据，避免数据过大
                #TODO 这里可以考虑使用方案2和方案3的特征数据
                if 'face_feature' in student_dict:
                    student_dict['has_face_feature'] = student_dict['face_feature'] is not None
                    del student_dict['face_feature']
                    
                return {
                    "success": True,
                    "data": student_dict
                }
            else:
                return {
                    "success": False,
                    "message": f"未找到学号为{student_id}的学生"
                }
                
        except Exception as e:
            logger.error(f"获取学生信息异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取学生信息异常: {str(e)}"
            }
    
    def get_all_students(self, class_name=None):
        """
        获取所有学生列表
        
        Args:
            class_name: 过滤班级名称
            
        Returns:
            list: 学生列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 修改查询：使用CASE判断face_feature是否为空，并返回状态
            # 考虑使用方案2和方案3的特征数据
            query = """
                SELECT 
                    id, 
                    student_id, 
                    name, 
                    class_name,
                    register_time,
                    CASE 
                        WHEN (face_feature IS NOT NULL AND LENGTH(face_feature) > 0)
                            OR (face_feature_2 IS NOT NULL AND LENGTH(face_feature_2) > 0)
                            OR (face_feature_3 IS NOT NULL AND LENGTH(face_feature_3) > 0)
                        THEN 'status-yes'
                        ELSE 'status-no'
                    END AS has_face_feature
                FROM students
            """
            params = []
            
            if class_name:
                query += " WHERE class_name = ?"
                params.append(class_name)
                
            query += " ORDER BY student_id"
            
            cursor.execute(query, params)
            students = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return {
                "success": True,
                "data": students
            }
            
        except Exception as e:
            logger.error(f"获取学生列表异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取学生列表异常: {str(e)}"
            }
    #TODO 这里应增加参数，选择获取对应的方案的人脸特征
    def get_student_face_feature(self, student_id, face_feature_type):
        """
        获取学生人脸特征
        
        Args:
            student_id: 学生学号
            face_feature_type: 人脸特征类型，可选值为 "arcsoft" 或 "deepface"
            
        Returns:
            dict: 包含特征数据的字典
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 根据特征类型选择相应的字段
            if face_feature_type == "arcsoft":
                feature_column = "face_feature"  # 存储ArcSoft特征的字段
            elif face_feature_type == "deepface":
                feature_column = "face_feature_2"  # 存储DeepFace特征的字段
            else:
                return {
                    "success": False,
                    "message": f"不支持的人脸特征类型: {face_feature_type}，请使用 'arcsoft' 或 'deepface'"
                }
            
            # 查询相应的特征字段
            query = f"SELECT {feature_column} FROM students WHERE student_id = ? AND {feature_column} IS NOT NULL"
            cursor.execute(query, (student_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:  # 注意这里使用索引0访问结果
                return {
                    "success": True,
                    "feature": result[0]  # 返回二进制特征数据
                }
            else:
                return {
                    "success": False,
                    "message": f"未找到学号为{student_id}的学生{face_feature_type}人脸特征"
                }
                
        except Exception as e:
            logger.error(f"获取学生人脸特征异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取学生人脸特征异常: {str(e)}"
            }
    
    def get_attendance_records(self, student_id=None, start_date=None, end_date=None, detection_method=None, class_name=None):
        """
        获取考勤记录
        
        Args:
            student_id: 学生学号
            start_date: 开始日期，格式YYYY-MM-DD
            end_date: 结束日期，格式YYYY-MM-DD
            detection_method: 检测方式
            class_name: 班级名称
            
        Returns:
            list: 考勤记录列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT a.id, a.student_id, s.name, s.class_name, a.check_time, a.status, 
                a.liveness_score, a.detection_method, a.similarity, a.remark
            FROM attendance a
            LEFT JOIN students s ON a.student_id = s.student_id
            WHERE 1=1
            """
            params = []
            
            if student_id:
                query += " AND a.student_id = ?"
                params.append(student_id)
                
            # 修改日期查询逻辑：支持日期范围
            if start_date and end_date:
                query += " AND a.check_time BETWEEN ? AND ?"
                params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
            elif start_date:
                query += " AND a.check_time >= ?"
                params.append(f"{start_date} 00:00:00")
            elif end_date:
                query += " AND a.check_time <= ?"
                params.append(f"{end_date} 23:59:59")
                
            if detection_method:
                query += " AND a.detection_method = ?"
                params.append(detection_method)
                
            if class_name:
                query += " AND s.class_name = ?"
                params.append(class_name)
                
            query += " ORDER BY a.check_time DESC"
            
            cursor.execute(query, params)
            records = [dict(row) for row in cursor.fetchall()]
            # logger.info(records)
            conn.close()
            
            return {
                "success": True,
                "data": records
            }
            
        except Exception as e:
            logger.error(f"获取考勤记录异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取考勤记录异常: {str(e)}"
            }
    
    def get_attendance_statistics(self, start_date=None, end_date=None, class_name=None):
        """
        获取考勤统计数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            class_name: 班级名称
            
        Returns:
            dict: 统计数据
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 设置默认日期范围为最近30天
            if not start_date:
                start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.datetime.now().strftime("%Y-%m-%d")
                
            query = """
            SELECT s.student_id, s.name, s.class_name,
                   COUNT(CASE WHEN a.status = 'present' THEN 1 END) AS present_count,
                   COUNT(CASE WHEN a.status = 'late' THEN 1 END) AS late_count,
                   COUNT(CASE WHEN a.status = 'absent' THEN 1 END) AS absent_count
            FROM students s
            LEFT JOIN attendance a ON s.student_id = a.student_id 
                                  AND date(a.check_time) BETWEEN ? AND ?
            """
            params = [start_date, end_date]
            
            if class_name:
                query += " WHERE s.class_name = ?"
                params.append(class_name)
                
            query += " GROUP BY s.student_id, s.name, s.class_name ORDER BY s.student_id"
            
            cursor.execute(query, params)
            stats = [dict(row) for row in cursor.fetchall()]
            
            # 计算总统计数据
            total_query = """
            SELECT COUNT(DISTINCT s.student_id) AS student_count,
                   COUNT(CASE WHEN a.status = 'present' THEN 1 END) AS total_present,
                   COUNT(CASE WHEN a.status = 'late' THEN 1 END) AS total_late,
                   COUNT(CASE WHEN a.status = 'absent' THEN 1 END) AS total_absent
            FROM students s
            LEFT JOIN attendance a ON s.student_id = a.student_id 
                                  AND date(a.check_time) BETWEEN ? AND ?
            """
            
            total_params = [start_date, end_date]
            
            if class_name:
                total_query += " WHERE s.class_name = ?"
                total_params.append(class_name)
                
            cursor.execute(total_query, total_params)
            total_stats = dict(cursor.fetchone())
            
            conn.close()
            
            return {
                "success": True,
                "data": {
                    "stats": stats,
                    "total": total_stats,
                    "period": {
                        "start_date": start_date,
                        "end_date": end_date
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取考勤统计异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取考勤统计异常: {str(e)}"
            }
    
    def delete_student(self, student_id):
        """
        删除学生记录
        
        Args:
            student_id: 学生学号
            
        Returns:
            dict: 删除结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查学生是否存在
            cursor.execute("SELECT id, name FROM students WHERE student_id = ?", (student_id,))
            student = cursor.fetchone()
            
            if not student:
                conn.close()
                return {
                    "success": False,
                    "message": f"未找到学号为{student_id}的学生"
                }
                
            # 删除考勤记录
            cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
            
            # 删除学生记录
            cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"学生{student['name']}({student_id})删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除学生异常: {str(e)}")
            return {
                "success": False,
                "message": f"删除学生异常: {str(e)}"
            }

    def link_student_user(self, student_id, user_id):
        """
        关联学生记录与用户帐号
        
        Args:
            student_id: 学生学号
            user_id: 用户ID
            
        Returns:
            dict: 操作结果
        """
        try:
            # Since user_id column doesn't exist, we can't link them directly
            # Return a message explaining the situation
            return {
                "success": False,
                "message": "无法关联学生记录和用户账号：数据库表结构不支持此操作"
            }
            
        except Exception as e:
            logger.error(f"关联学生用户异常: {str(e)}")
            return {
                "success": False,
                "message": f"关联学生用户异常: {str(e)}"
            }

    def delete_user(self, user_id):
        """
        删除用户账号
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 操作结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 删除用户
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            if cursor.rowcount == 0:
                conn.close()
                return {
                    "success": False,
                    "message": f"未找到ID为 {user_id} 的用户账号"
                }
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"用户账号已成功删除"
            }
            
        except Exception as e:
            logger.error(f"删除用户异常: {str(e)}")
            return {
                "success": False,
                "message": f"删除用户异常: {str(e)}"
            }
