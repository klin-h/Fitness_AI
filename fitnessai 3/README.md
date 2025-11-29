# FitnessAI - 智能健身辅助系统

## 项目概述

FitnessAI 是一个基于人工智能的体感健身辅助网页系统，通过实时获取摄像头图像，利用 MediaPipe 姿态识别技术对人体骨骼进行数据解析，检测用户的健身动作是否标准，并提供实时反馈和统计功能。

## 主要功能

- **实时姿态识别**：基于 Google MediaPipe 的人体骨骼关键点检测（33个关键点），并实时绘制姿态关键点和连接线。
- **动作分析评估**：智能判断健身动作的标准性和正确性，提供即时的动作纠正建议和评分。同时可以准确统计运动次数（对于符合标准的健身动作）和持续时间。
-  **数据统计**：记录训练历史、准确率和成就系统，并基于健身历史记录提供个性化的健身计划方案。

## 支持的运动类型

- **深蹲 (Squat)**
- **俯卧撑 (Push-up)**
- **平板支撑 (Plank)**
- **开合跳 (Jumping Jack)**

## 系统运行方法

### 1. 运行前的检查工作

1. **检查操作系统**：Windows 10/11、macOS 10.15及以上、Linux（Ubuntu 18.04及以上）
2. **最低硬件配置**：内存：4GB RAM；处理器：双核2.0GHz；摄像头；稳定的网络连接
3. **检查软件配置**：Node.js 16及以上、Python 3.8及以上、现代浏览器（Chrome 88+ / Firefox 85+ / Safari 14+ / Edge 88+）

### 2. 运行系统的方法（下面两种方式任选一种）

- **一键启动（推荐）**

一键启动的方法讲自动完成以下操作：检查系统依赖、安装Python包、启动后端服务、启动前端服务、自动打开浏览器。请根据您的操作系统选择对应的方法：
macOS用户：
```bash
python3 start_macos.py
```
Windows用户：（须接入国际互联网）
```bash
python3 win_start.py
```

- **通用启动（适合所有平台）**
```bash
# 设置环境
python3 setup.py

# 启动应用
python3 simple_start.py
```

## 项目文件结构
```
fitnessai/
├── frontend/                           # React 前端应用
│   ├── src/
│   │   ├── components/                 # React 组件
│   │   │   ├── CameraView.tsx          # 摄像头视图（增强错误处理）
│   │   │   ├── StatsPanel.tsx          # 统计面板
│   │   │   └── ExerciseSelector.tsx    # 运动选择器
│   │   ├── hooks/                      # 自定义 Hooks
│   │   │   └── usePoseDetection.ts     # 姿态识别Hook（完全重写）
│   │   ├── App.tsx                     # 主应用（状态指示器）
│   │   ├── index.css                   # Tailwind CSS
│   │   └── App.css                     # 自定义样式
│   ├── package.json                    # 前端依赖配置
│   └── public/                         # 静态资源
├── backend/                            # Python 后端 API
│   ├── pose_analyzer.py                # 姿态分析算法（20KB）
│   ├── requirements.txt                # Python 依赖
│   └── venv/                           # Python虚拟环境目录，用于隔离依赖
├── start_macos.py                      # macOS专用启动器
├── simple_start.py                     # 通用简单启动器
├── setup.py                            # 环境设置脚本
├── status_check.py                     # 状态检查工具
├── start.py                            # 原始启动脚本
├── run_app.py                          # 后端启动器
├── test_integration.py                 # 集成测试脚本
├── check_env.py                        # 环境检查工具
└── 其余文件                             # 前端构建和依赖配置文件
```