# 学生校园人脸考勤系统后端

这是一个基于虹软ArcSoft人脸识别SDK等多种方案的学生校园人脸考勤系统后端，提供人脸识别、活体检测和考勤管理功能。

## 功能特点

- 基于虹软ArcSoft人脸识别SDK的活体检测
- 人脸特征提取和比对
- 学生信息管理
- 考勤记录管理和统计
- RESTful API接口
- SQLite数据库存储

## 系统要求

- Python 3.7+
- Windows 10 64位系统（虹软SDK要求）
- 虹软人脸识别SDK许可证（请访问[虹软开发者平台](https://ai.arcsoft.com.cn/)申请）

## 安装步骤

1. 克隆代码仓库

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 配置SDK
   - 将虹软SDK的应用ID和密钥填入`face_sdk/arc_face_sdk.py`文件中的相应位置
   - 确保`libarcsoft_face_engine.dll`和`libarcsoft_face.dll`文件位于正确的路径

4. 启动应用
   ```bash
   cd back_end
   python app.py
   ```


## API接口说明

### 认证与用户管理
- `POST /api/auth/login` 用户登录，返回token及用户信息
- `POST /api/auth/register/student` 学生注册账号
- `POST /api/auth/register/teacher` 教师注册账号


### 学生管理（教师权限）
- `GET /api/admin/students` 获取学生列表（可按班级筛选）
- `GET /api/admin/students/{student_id}` 获取学生详情
- `PUT /api/admin/students/{student_id}` 更新学生信息
- `DELETE /api/admin/students/{student_id}` 删除学生

### 班级管理（教师权限）
- `GET /api/admin/classes` 获取所有班级
- `POST /api/admin/classes` 创建班级
- `PUT /api/admin/classes/{class_id}` 更新班级信息
- `DELETE /api/admin/classes/{class_id}` 删除班级

### 考勤规则管理（教师权限）
- `GET /api/admin/attendance-rules` 获取考勤规则（可按班级筛选）
- `POST /api/admin/attendance-rules` 创建或更新考勤规则

### 学生人脸注册与考勤
- `POST /api/register-student` 学生人脸特征注册（上传照片）
- `POST /api/attendance` 学生考勤打卡（上传照片，活体检测）

### 考勤记录与统计
- `GET /api/attendance` 查询考勤记录（支持按学号、班级、时间段等筛选）
- `GET /api/attendance/statistics` 查询考勤统计数据（支持按班级、时间段等筛选）

### 系统管理
- `GET /api/system/sdk-info` 获取SDK版本信息

---

## 数据库结构

### users 用户表
| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| id | INTEGER | 主键 |
| username | TEXT | 用户名 |
| password | TEXT | 密码哈希 |
| role | TEXT | 角色 |
| real_name | TEXT | 真实姓名 |
| email | TEXT | 邮箱 |
| phone | TEXT | 电话 |
| avatar | BLOB | 头像 |
| last_login | TIMESTAMP | 上次登录时间 |
| create_time | TIMESTAMP | 创建时间 |
| status | INTEGER | 状态 |

### students 学生表
| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| id | INTEGER | 主键 |
| student_id | TEXT | 学号 |
| name | TEXT | 姓名 |
| face_feature | BLOB | 人脸特征 |
| class_name | TEXT | 班级 |
| user_id | INTEGER | 关联用户ID |
| register_time | TIMESTAMP | 注册时间 |

### teachers 教师表
| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| id | INTEGER | 主键 |
| teacher_id | TEXT | 工号 |
| name | TEXT | 姓名 |
| department | TEXT | 部门 |
| position | TEXT | 职位 |
| user_id | INTEGER | 关联用户ID |
| create_time | TIMESTAMP | 创建时间 |

### classes 班级表
| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| id | INTEGER | 主键 |
| class_name | TEXT | 班级名称 |
| description | TEXT | 描述 |
| teacher_id | INTEGER | 班主任ID |
| create_time | TIMESTAMP | 创建时间 |

### attendance 考勤记录表
| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| id | INTEGER | 主键 |
| student_id | TEXT | 学号 |
| check_time | TIMESTAMP | 考勤时间 |
| status | TEXT | 状态 |
| liveness_score | REAL | 活体分数 |
| detection_method | TEXT | 检测方式 |
| similarity | REAL | 相似度 |
| remark | TEXT | 备注 |

### attendance_rules 考勤规则表
| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| id | INTEGER | 主键 |
| class_id | INTEGER | 班级ID |
| class_name | TEXT | 班级名称 |
| start_time | TEXT | 上课时间 |
| end_time | TEXT | 下课时间 |
| late_threshold | INTEGER | 迟到阈值 |
| weekdays | TEXT | 适用星期 |
| is_active | INTEGER | 是否激活 |
| create_time | TIMESTAMP | 创建时间 |
| remark | TEXT | 备注 |

---

## 前端实际调用的主要API
- 登录/注册：`/api/auth/login`、`/api/auth/register/student`、`/api/auth/register/teacher`
- 学生人脸注册：`/api/register-student`
- 学生考勤打卡：`/api/attendance`
- 查询考勤记录/统计：`/api/attendance`、`/api/attendance/statistics`
- 班级管理：`/api/admin/classes`（GET/POST/PUT/DELETE）
- 学生管理：`/api/admin/students`、`/api/admin/students/{student_id}`（GET/PUT/DELETE）
- 考勤规则管理：`/api/admin/attendance-rules`（GET/POST）
- 修改密码：`/api/auth/password`

## 未被前端实际调用的API（可后续扩展）
- `POST /api/liveness-detect` 通用活体检测接口（前端未直接用，考勤打卡时已集成）
- `GET /api/system/sdk-info` 获取SDK版本信息
- `POST /api/admin/classes/{class_id}` 班级信息更新（部分前端未用 PUT/DELETE）
- `POST /api/admin/attendance-rules` 直接批量创建/更新规则（前端仅用单条）
- `GET /api/admin/students?class_name=xxx` 按班级查学生（部分页面未用）
- `POST /api/attendance/appeal` 考勤申诉接口（如有实现）

---

## 说明
- 所有管理类接口均需教师权限，需携带 Bearer Token。
- 学生考勤、注册等接口需学生权限或登录。
- 活体检测、考勤等接口依赖虹软 ArcSoft SDK，需正确配置授权文件。
- 数据库为 SQLite，支持单机部署。

