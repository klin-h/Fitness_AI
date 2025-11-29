#!/usr/bin/env python3
"""
FitnessAI Windows 启动脚本
同时启动前后端服务
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

backend_process = None
frontend_process = None

def signal_handler(signum, frame):
    print("\n🛑 收到中断信号，正在关闭服务...")
    cleanup_and_exit()

def cleanup_and_exit():
    global backend_process, frontend_process

    if backend_process:
        print("🔄 关闭后端服务...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()

    if frontend_process:
        print("🔄 关闭前端服务...")
        frontend_process.terminate()
        try:
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_process.kill()

    print("✅ 服务已关闭")
    sys.exit(0)

def check_port(port):
    """检查端口是否被占用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def kill_port_process(port):
    """结束占用端口的进程（Windows专用）"""
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}', shell=True,
                                capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        pids = set()
        for line in lines:
            if line:
                pid = line.strip().split()[-1]
                pids.add(pid)
        for pid in pids:
            subprocess.run(f'taskkill /PID {pid} /F', shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if pids:
            print(f"✅ 已清理端口 {port}")
    except Exception as e:
        print(f"⚠️ 清理端口 {port} 时出错: {e}")

def check_dependencies():
    required_packages = ['flask', 'flask-cors', 'numpy', 'opencv-python', 'mediapipe']
    missing = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ 缺少依赖: {', '.join(missing)}")
        print("🔄 正在安装...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install"
            ] + missing)
            print("✅ 依赖安装完成")
        except Exception as e:
            print(f"❌ 安装失败: {e}")
            return False

    return True

def start_backend():
    global backend_process

    print("🚀 启动后端服务...")
    if check_port(8000):
        print("🧹 清理端口 8000...")
        kill_port_process(8000)
        time.sleep(2)

    try:
        backend_process = subprocess.Popen([
            sys.executable, "simple_start.py"
        ])

        for _ in range(10):
            if check_port(8000):
                print("✅ 后端服务启动成功 (http://localhost:8000)")
                return True
            time.sleep(1)

        print("❌ 后端服务启动超时")
        return False

    except Exception as e:
        print(f"❌ 后端启动失败: {e}")
        return False

def start_frontend():
    global frontend_process

    print("🎨 启动前端服务...")

    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ frontend 目录不存在")
        return False

    if check_port(3000):
        print("🧹 清理端口 3000...")
        kill_port_process(3000)
        time.sleep(2)

    try:
        os.chdir(frontend_dir)

        if not Path("node_modules").exists():
            print("📦 安装前端依赖...")
            subprocess.check_call(["npm", "install"], shell=True)

        frontend_process = subprocess.Popen(
            ["npm", "start"], shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        os.chdir("..")

        print("⏳ 等待前端服务启动...")
        for _ in range(30):
            if check_port(3000):
                print("✅ 前端服务启动成功 (http://localhost:3000)")
                return True
            time.sleep(1)

        print("❌ 前端服务启动超时")
        return False

    except Exception as e:
        print(f"❌ 前端启动失败: {e}")
        return False

def monitor_services():
    while True:
        try:
            if backend_process and backend_process.poll() is not None:
                print("❌ 后端服务已停止")
                break
            if frontend_process and frontend_process.poll() is not None:
                print("❌ 前端服务已停止")
                break
            time.sleep(5)
        except KeyboardInterrupt:
            break

def main():
    print("🏃‍♂️ FitnessAI Windows 启动器")
    print("=" * 50)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if sys.version_info < (3, 8):
        print("❌ 需要 Python 3.8 或更高版本")
        return

    print(f"✅ Python 版本: {sys.version.split()[0]}")

    if not check_dependencies():
        return

    if not start_backend():
        print("❌ 后端启动失败")
        return

    time.sleep(3)

    if not start_frontend():
        print("⚠️ 前端启动失败，但后端正常运行")
        print("💡 可以访问 http://localhost:8000/demo 查看后端演示")

    print("\n" + "=" * 50)
    print("🎉 FitnessAI 启动成功！")
    print("\n📱 访问地址:")
    print("   - 主应用: http://localhost:3000")
    print("   - 后端API: http://localhost:8000/api")
    print("   - 演示页面: http://localhost:8000/demo")
    print("\n💡 提示:")
    print("   - 确保允许浏览器访问摄像头")
    print("   - 按 Ctrl+C 停止所有服务")
    print("   - 首次启动可能需要几分钟")

    try:
        monitor_services()
    finally:
        cleanup_and_exit()

if __name__ == "__main__":
    main()