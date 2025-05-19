# 校园人脸考勤系统

本项目为基于多方案（ArcSoft/DeepFace/静默活体）的人脸识别考勤系统，包含前端（Vue3+Vite）和后端（FastAPI+多模型）两部分，支持高安全性活体检测、考勤管理、班级管理等功能。

---

## 目录结构

```
lab6/
├── back_end/           # 后端服务（FastAPI）
│   ├── app.py         # 主后端应用
│   ├── database.py    # 数据库操作
│   ├── dataset.py     # 数据集与特征处理
│   ├── face_sdk/      # ArcSoft SDK集成
│   ├── face_model1/   # DeepFace方案
│   ├── face_model2/   # 静默活体检测方案
│   ├── anti/          # 交互式活体检测
│   ├── uploads/       # 上传图片存储
│   └── ...
├── front_end/          # 前端项目（Vue3+Vite）
│   ├── src/           # 前端源码
│   ├── public/        # 静态资源
│   ├── vite.config.js # Vite配置
│   └── ...
└── README.md           # 项目说明
```

---

## 后端使用说明

### 1. 终端启动redis
  ```powershell
  redis-server
  ```
### 2. 环境准备
- Python 3.7/3.8（建议Anaconda虚拟环境）
- 安装依赖：
  ```powershell
  pip install -r requirements.txt
  ```
- 确保已放置ArcSoft SDK、模型权重（如`face_model2/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth`）
- 数据库文件自动生成（SQLite）

### 注意修改相关路径

### 2. 启动后端服务

```powershell
cd back_end
python app.py
```
- 默认监听8090端口，可在命令行修改


### 3. 主要API接口
- `/api/register-student`  学生人脸注册（支持三种特征）
- `/api/attendance`        ArcSoft方案考勤
- `/api/attendance/deepface` DeepFace方案考勤
- `/api/attendance/silence`  静默活体考勤
- `/api/interactive-liveness` 交互式活体检测
- `/api/face-recognize`    实时识别API
- 详见`app.py`注释

---

## 前端使用说明

### 1. 环境准备
- Node.js 16+
- 进入`front_end`目录，安装依赖：
  ```powershell
  npm install
  ```

### 2. 启动前端开发服务器
```powershell
npm run dev
```
- 默认端口为5173
- 访问 http://localhost:5173

### 3. 前后端联调配置
- `vite.config.js` 已配置 `/api` 代理到 `http://127.0.0.1:8090`
- 前端所有接口请求均以 `/api/xxx` 开头，无需关心端口跨域
- 若后端端口有变，需同步修改 `vite.config.js` 代理配置

---

## 常见问题

- **端口冲突/多实例**：不要在`app.py`里写`uvicorn.run`，只用命令行启动。
- **模型权重找不到**：确保`face_model2/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth`存在。
- **前端无法访问后端**：确认前端请求为`/api/xxx`，且`vite.config.js`代理正确。
- **防火墙/杀毒拦截**：如遇端口监听失败，关闭防火墙或换高位端口。

---

## 主要功能
- 支持ArcSoft/DeepFace/静默活体三种考勤方案
- 交互式活体检测（眨眼、张嘴、点头、摇头）
- 防照片/视频攻击、反射检测、超时检测
- 学生/教师/班级/考勤规则管理
- 实时人脸识别与考勤统计

---

## 其他
- 本项目仅供学习交流，部分SDK/模型需自行获取授权。

