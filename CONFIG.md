# FitnessAI 配置指南

本文档包含 FitnessAI 项目的所有配置说明。

## 📋 目录

- [环境要求](#环境要求)
- [快速启动](#快速启动)
- [AI功能配置](#ai功能配置)
- [常见问题](#常见问题)

---

## 环境要求

### 必需软件

- **Node.js 16+**
- **Python 3.8+**
- **现代浏览器**（Chrome/Firefox/Safari/Edge）
- **摄像头设备**

### 系统要求

- **Windows 10/11**
- **macOS 10.15+**
- **Linux (Ubuntu 18.04+)**

---

## 快速启动

### 方法一：使用启动脚本（推荐）

**Windows:**
```bash
python start.py
```

**Mac/Linux:**
```bash
chmod +x start.sh
./start.sh
```

启动脚本会自动：
1. 检查并安装 Python 依赖
2. 启动后端服务（http://localhost:8000）
3. 检查并安装前端依赖
4. 启动前端服务（http://localhost:3000）
5. 自动打开浏览器

### 方法二：手动启动

#### 启动后端

```bash
cd backend
python app.py
```

后端将在 `http://localhost:8000` 运行

#### 启动前端

```bash
cd frontend
npm install  # 如果还没安装依赖
npm start
```

前端将在 `http://localhost:3000` 运行

---

## AI功能配置

### 智谱AI API配置（可选）

项目集成了智谱AI（GLM）API，可以根据用户身体指标生成个性化健身计划。

#### 1. 获取API Key（免费）

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册账号（免费）
3. 登录后进入"控制台"
4. 在"API Keys"页面创建新的API Key
5. 复制API Key

#### 2. 配置API Key

在 `backend` 目录下创建 `.env` 文件：

**Windows:**
```cmd
cd backend
type nul > .env
```

**Mac/Linux:**
```bash
cd backend
touch .env
```

在 `.env` 文件中添加：
```
ZHIPU_API_KEY=你的API_Key_粘贴在这里
```

例如：
```
ZHIPU_API_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

#### 3. 重启服务

配置完成后，重启后端服务即可使用AI功能。

#### 4. 使用AI功能

1. 登录系统
2. 填写个人资料（身高、体重、年龄、性别）
3. 进入"个人中心" → "健身计划"
4. 点击"AI生成建议"按钮
5. AI会根据您的身体指标生成个性化健身计划

#### 5. 降级机制

- 如果未配置API Key，系统会自动使用规则引擎生成建议
- 如果API调用失败，系统会自动降级使用规则引擎
- 功能仍然可用，只是建议来源不同

---

## 常见问题

### 启动问题

**Q: 端口被占用怎么办？**

Windows:
```cmd
netstat -ano | findstr :3000
netstat -ano | findstr :8000
taskkill /pid <PID> /f
```

Mac/Linux:
```bash
lsof -i :3000
lsof -i :8000
kill -9 <PID>
```

**Q: Python依赖安装失败？**

```bash
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Q: Node依赖安装失败？**

```bash
cd frontend
npm cache clean --force
npm install
```

### AI功能问题

**Q: API调用失败？**

1. 检查API Key是否正确配置在 `backend/.env` 文件中
2. 检查网络连接
3. 查看后端控制台的错误信息
4. 系统会自动降级使用规则引擎，功能仍然可用

**Q: 如何知道是否使用了AI？**

- 查看后端控制台日志
- 如果看到 `✅ [AI] API调用成功！`，说明使用了AI
- 如果看到 `⚠️ [AI] API Key未配置` 或 `❌ [AI] API调用失败`，说明使用了规则引擎

**Q: API Key安全吗？**

- `.env` 文件已添加到 `.gitignore`，不会被提交到代码仓库
- 请勿将API Key分享给他人
- 如果API Key泄露，请立即在智谱AI平台重新生成

### 功能问题

**Q: 摄像头无法访问？**

1. 检查浏览器权限设置
2. 确保没有其他应用占用摄像头
3. 尝试刷新页面

**Q: 历史记录没有数据？**

1. 确保已登录账号
2. 开始一次运动并点击"暂停检测"结束会话
3. 历史记录才会保存

**Q: 健身计划没有同步？**

1. 确保已保存健身计划（点击"保存计划"按钮）
2. 刷新主页，计划会自动加载

---

## 其他配置

### 修改端口

**后端端口（默认8000）：**
修改 `backend/app.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=8000)
```

**前端端口（默认3000）：**
修改 `frontend/package.json` 中的 `start` 脚本，或设置环境变量：
```bash
PORT=3001 npm start
```

### 使用其他AI API

如果需要使用其他AI API，可以修改 `backend/app.py` 中的 `call_zhipu_ai_api` 函数。

支持的国内AI API：
- 智谱AI（GLM）- 当前使用
- 通义千问（阿里云）
- 文心一言（百度）
- 月之暗面（Kimi）

---

## 技术支持

如有问题，请查看：
- 后端控制台日志
- 浏览器开发者工具（F12）控制台
- 项目 README.md 文件

