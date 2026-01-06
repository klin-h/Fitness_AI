#!/bin/bash

# 健身AI应用启动脚本 (Mac/Linux)

echo "🚀 启动健身AI应用..."

# 检查是否在正确的目录
if [ ! -d "frontend" ] || [ ! -d "backend" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: Node.js 未安装，请先安装 Node.js"
    echo "下载地址: https://nodejs.org/"
    exit 1
fi

# 检查Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ 错误: Python 未安装，请先安装 Python 3.8+"
    echo "下载地址: https://www.python.org/downloads/"
    exit 1
fi

# 确定Python命令
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# 清理端口
echo "🧹 清理端口..."
if command -v lsof &> /dev/null; then
    # Mac/Linux方式
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
else
    echo "⚠️  警告: lsof 命令不可用，跳过端口清理"
fi

# 启动后端
echo "🔧 启动后端服务器..."
cd backend

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    $PYTHON_CMD -m venv venv
fi

# 激活虚拟环境 (Mac/Linux方式)
source venv/bin/activate

# 检查pip
if ! command -v pip &> /dev/null; then
    echo "❌ 错误: pip 不可用"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip install -q -r requirements.txt

# 启动后端服务
echo "🏃‍♂️ 后端运行在 http://localhost:8000"
$PYTHON_CMD app.py &
BACKEND_PID=$!

# 切换到前端目录
cd ../frontend

# 检查npm
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: npm 不可用，请确保Node.js正确安装"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 安装前端依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

# 启动前端服务
echo "🎨 启动前端服务器..."
echo "🌐 前端运行在 http://localhost:3000"

# 设置环境变量
export BROWSER=none
npm start &
FRONTEND_PID=$!

# 等待服务器启动
sleep 5

echo ""
echo "✅ 健身AI应用已启动！"
echo "📱 前端: http://localhost:3000"
echo "🔧 后端: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 清理函数
cleanup() {
    echo ""
    echo "🛑 停止所有服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    
    # 额外清理端口
    if command -v lsof &> /dev/null; then
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    fi
    
    echo "服务已停止"
    exit 0
}

# 等待并处理中断信号
trap cleanup INT TERM

# 持续监控
while true; do
    # 检查进程是否还在运行
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ 后端进程意外停止"
        cleanup
    fi
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ 前端进程意外停止" 
        cleanup
    fi
    sleep 1
done 