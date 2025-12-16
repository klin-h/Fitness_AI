# FitnessAI - 智能健身辅助系统

一个基于人工智能的体感健身辅助网页系统，通过实时摄像头姿态识别，检测健身动作标准性并提供实时反馈。

## ✨ 主要功能

- 🎯 **实时姿态识别**：基于 MediaPipe 的人体骨骼关键点检测
- 📊 **动作分析**：智能判断健身动作的标准性和正确性
- 🔢 **自动计数**：准确统计运动次数和持续时间
- 💬 **实时反馈**：提供即时的动作纠正建议
- 📈 **数据统计**：记录训练历史和成就系统
- 🤖 **AI健身计划**：基于智谱AI的个性化健身计划生成
- 👤 **用户系统**：注册登录、个人中心、历史记录管理

## 🏃 支持的运动类型

1. **深蹲 (Squat)**：检测膝盖角度和姿态正确性
2. **俯卧撑 (Push-up)**：监测身体直线度和手臂动作
3. **平板支撑 (Plank)**：分析核心稳定性和保持时间
4. **开合跳 (Jumping Jack)**：识别手臂和腿部协调性

## 🚀 快速开始

### 一键启动（推荐）

```bash
python start.py
```

启动脚本会自动：
- 检查并安装依赖
- 启动后端服务（http://localhost:8000）
- 启动前端服务（http://localhost:3000）
- 自动打开浏览器

### 访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000

## 📋 系统要求

- **Node.js 16+** 
- **Python 3.8+**
- **现代浏览器**（Chrome/Firefox/Safari/Edge）
- **摄像头设备**

支持的操作系统：Windows 10/11、macOS 10.15+、Linux (Ubuntu 18.04+)

## 🛠️ 技术栈

### 前端
- React 18 + TypeScript
- Tailwind CSS
- React Router DOM
- Lucide React

### 后端
- Flask
- Flask-CORS
- 智谱AI (GLM) - AI健身计划生成

## 📖 配置说明

所有详细配置说明请查看 **[CONFIG.md](CONFIG.md)**，包括：
- 环境要求
- 启动方式（自动/手动）
- AI功能配置
- 常见问题
- 故障排除

## 🎮 使用流程

1. **启动应用**：运行 `python start.py`
2. **注册/登录**：创建账号或登录
3. **填写资料**：在个人中心填写身高、体重、年龄、性别
4. **选择运动**：在主页选择要练习的动作类型
5. **开始检测**：点击"开始检测"，允许摄像头权限
6. **进行锻炼**：按照提示进行标准运动
7. **查看反馈**：观察实时反馈和统计数据
8. **结束训练**：点击"暂停检测"结束本次训练
9. **查看历史**：在个人中心查看历史记录

## 📁 项目结构

```
fitnessai/
├── frontend/              # React 前端应用
│   ├── src/
│   │   ├── components/    # React 组件
│   │   ├── pages/         # 页面组件
│   │   ├── contexts/      # Context API
│   │   ├── hooks/         # 自定义 Hooks
│   │   └── services/      # API 服务
│   └── package.json
├── backend/               # Python 后端 API
│   ├── app.py            # Flask 主应用
│   ├── requirements.txt  # Python 依赖
│   └── *.json           # 数据存储文件
├── start.py              # 跨平台启动脚本
├── CONFIG.md             # 配置文档
└── README.md             # 项目文档
```

## 🔑 核心功能说明

### 用户系统
- 用户注册/登录
- 个人资料管理（昵称、邮箱、身高、体重、年龄、性别）
- 密码修改
- 历史记录查看

### 健身计划
- 设置每日目标（深蹲、俯卧撑、平板支撑、开合跳）
- 设置每周目标（总运动次数、总运动时长）
- AI生成个性化建议（可选，需配置API Key）

### 运动检测
- 实时摄像头姿态识别
- 自动计数和评分
- 实时反馈和建议
- 运动数据持久化存储

## 🔧 开发

### 手动启动

**后端：**
```bash
cd backend
python app.py
```

**前端：**
```bash
cd frontend
npm install
npm start
```

### 构建生产版本

**前端：**
```bash
cd frontend
npm run build
```

**后端：**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 📝 API 接口

### 认证相关
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息
- `POST /api/auth/change-password` - 修改密码

### 用户相关
- `GET /api/user/profile` - 获取用户资料
- `PUT /api/user/profile` - 更新用户资料
- `GET /api/user/{user_id}/history` - 获取历史记录
- `GET /api/user/plan` - 获取健身计划
- `PUT /api/user/plan` - 更新健身计划

### AI相关
- `POST /api/ai/generate-plan` - AI生成健身计划建议

### 会话相关
- `POST /api/session/start` - 开始运动会话
- `POST /api/session/{session_id}/data` - 提交运动数据
- `POST /api/session/{session_id}/end` - 结束运动会话

## ⚠️ 注意事项

- 所有视频数据仅在本地处理，不会上传到服务器
- 需要摄像头权限才能使用运动检测功能
- AI功能需要配置API Key（详见 CONFIG.md）
- 数据存储在本地JSON文件中（生产环境建议使用数据库）

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**🎉 开始你的智能健身之旅！**
