#!/usr/bin/env python3
"""
FitnessAI 跨平台启动脚本 - 修复版本
支持 Windows, macOS, Linux
"""

import os
import sys
import subprocess
import platform
import time
import signal
import webbrowser
import atexit
from pathlib import Path

# 全局变量存储进程引用
backend_process = None
frontend_process = None

def cleanup_processes():
    """清理所有子进程"""
    global backend_process, frontend_process
    
    print_colored("🧹 清理进程资源...", 'yellow')
    
    if backend_process:
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            if backend_process.poll() is None:
                backend_process.kill()
        backend_process = None
    
    if frontend_process:
        try:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            if frontend_process.poll() is None:
                frontend_process.kill()
        frontend_process = None
    
    # 额外清理端口
    kill_process_on_port(3000)
    kill_process_on_port(8000)

# 注册清理函数
atexit.register(cleanup_processes)

def signal_handler(signum, frame):
    """信号处理器"""
    print_colored(f"\n接收到信号 {signum}，正在清理...", 'yellow')
    cleanup_processes()
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def print_colored(text, color='white'):
    """打印彩色文本"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m', 
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'end': '\033[0m'
    }
    if platform.system() == 'Windows':
        # Windows下可能不支持颜色
        print(text)
    else:
        print(f"{colors.get(color, colors['white'])}{text}{colors['end']}")

def check_command(command):
    """检查命令是否存在"""
    try:
        subprocess.run([command, '--version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def kill_process_on_port(port):
    """跨平台杀死占用端口的进程"""
    system = platform.system()
    try:
        if system == 'Windows':
            # Windows方式
            result = subprocess.run(['netstat', '-ano'], 
                                  capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        subprocess.run(['taskkill', '/pid', pid, '/f'], 
                                     capture_output=True)
        else:
            # Mac/Linux方式
            if check_command('lsof'):
                result = subprocess.run(['lsof', f'-ti:{port}'], 
                                      capture_output=True, text=True)
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', '-9', pid], 
                                     capture_output=True)
    except Exception as e:
        print_colored(f"清理端口 {port} 时出错: {e}", 'yellow')

def get_python_command():
    """获取Python命令"""
    for cmd in ['python3', 'python']:
        if check_command(cmd):
            return cmd
    return None

def get_venv_activate_command():
    """获取虚拟环境激活命令"""
    system = platform.system()
    if system == 'Windows':
        return ['venv\\Scripts\\activate.bat']
    else:
        return ['source', 'venv/bin/activate']

def create_virtual_env(python_cmd):
    """创建虚拟环境"""
    if not Path('venv').exists():
        print_colored("📦 创建Python虚拟环境...", 'blue')
        subprocess.run([python_cmd, '-m', 'venv', 'venv'], check=True)

def activate_and_install(python_cmd):
    """激活虚拟环境并安装依赖"""
    system = platform.system()
    
    if system == 'Windows':
        pip_cmd = 'venv\\Scripts\\pip.exe'
        python_venv = 'venv\\Scripts\\python.exe'
    else:
        pip_cmd = 'venv/bin/pip'
        python_venv = 'venv/bin/python'
    
    # 安装依赖
    print_colored("📦 安装Python依赖...", 'blue')
    subprocess.run([pip_cmd, 'install', '-q', '-r', 'requirements.txt'], 
                   check=True)
    
    return python_venv

def start_backend(python_cmd):
    """启动后端服务"""
    print_colored("🔧 启动后端服务器...", 'blue')
    
    # 设置环境变量避免multiprocessing问题
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    env['FLASK_ENV'] = 'production'  # 使用生产模式
    
    return subprocess.Popen(
        [python_cmd, 'app.py'], 
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def start_frontend():
    """启动前端服务"""
    print_colored("🎨 启动前端服务器...", 'blue')
    env = os.environ.copy()
    env['BROWSER'] = 'none'
    return subprocess.Popen(['npm', 'start'], env=env)

def main():
    """主函数"""
    global backend_process, frontend_process
    
    print_colored("🚀 启动健身AI应用...", 'green')
    
    # 检查目录
    if not Path('frontend').exists() or not Path('backend').exists():
        print_colored("❌ 错误: 请在项目根目录运行此脚本", 'red')
        sys.exit(1)
    
    # 检查依赖
    if not check_command('node'):
        print_colored("❌ 错误: Node.js 未安装", 'red')
        print_colored("下载地址: https://nodejs.org/", 'yellow')
        sys.exit(1)
    
    python_cmd = get_python_command()
    if not python_cmd:
        print_colored("❌ 错误: Python 未安装", 'red')
        print_colored("下载地址: https://www.python.org/downloads/", 'yellow')
        sys.exit(1)
    
    # 清理端口
    print_colored("🧹 清理端口...", 'cyan')
    kill_process_on_port(3000)
    kill_process_on_port(8000)
    
    try:
        # 启动后端
        os.chdir('backend')
        create_virtual_env(python_cmd)
        python_venv = activate_and_install(python_cmd)
        
        print_colored("🏃‍♂️ 后端运行在 http://localhost:8000", 'green')
        backend_process = start_backend(python_venv)
        
        # 启动前端
        os.chdir('../frontend')
        
        if not Path('node_modules').exists():
            print_colored("📦 安装前端依赖...", 'blue')
            subprocess.run(['npm', 'install'], check=True)
        
        print_colored("🌐 前端运行在 http://localhost:3000", 'green')
        frontend_process = start_frontend()
        
        # 等待服务启动
        time.sleep(5)
        
        print_colored("\n✅ 健身AI应用已启动！", 'green')
        print_colored("📱 前端: http://localhost:3000", 'cyan')
        print_colored("🔧 后端: http://localhost:8000", 'cyan')
        print_colored("\n按 Ctrl+C 停止所有服务", 'yellow')
        
        # 可选择性打开浏览器
        try:
            webbrowser.open('http://localhost:3000')
        except:
            pass
        
        # 等待中断信号
        while True:
            time.sleep(1)
            
            # 检查进程是否还在运行
            if backend_process and backend_process.poll() is not None:
                print_colored("❌ 后端进程意外退出", 'red')
                break
            if frontend_process and frontend_process.poll() is not None:
                print_colored("❌ 前端进程意外退出", 'red')
                break
            
    except KeyboardInterrupt:
        print_colored("\n🛑 用户中断，停止所有服务...", 'yellow')
        
    except Exception as e:
        print_colored(f"❌ 启动失败: {e}", 'red')
        
    finally:
        cleanup_processes()
        print_colored("✅ 服务已完全停止", 'green')

if __name__ == '__main__':
    main() 