#!/usr/bin/env python3
"""
FitnessAI 跨平台启动脚本
支持 Windows, macOS, Linux
"""

import os
import sys
import subprocess
import platform
import time
import signal
import webbrowser
from pathlib import Path

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
        # Windows下npm通常是npm.cmd
        if platform.system() == 'Windows' and command == 'npm':
            test_cmd = 'npm.cmd'
        else:
            test_cmd = command
        subprocess.run([test_cmd, '--version'], 
                      capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        # 如果npm.cmd失败，尝试npm
        if platform.system() == 'Windows' and command == 'npm':
            try:
                subprocess.run(['npm', '--version'], 
                              capture_output=True, check=True, timeout=5)
                return True
            except:
                return False
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
    
    # 检测虚拟环境结构（Windows 可能是 Scripts 或 bin）
    if system == 'Windows':
        # 使用 Path 对象进行跨平台路径检查
        scripts_pip = Path('venv') / 'Scripts' / 'pip.exe'
        scripts_python = Path('venv') / 'Scripts' / 'python.exe'
        bin_python = Path('venv') / 'bin' / 'python'
        
        if scripts_pip.exists() and scripts_python.exists():
            # 标准 Windows 虚拟环境
            pip_cmd = str(scripts_pip.resolve())
            python_venv = str(scripts_python.resolve())
            use_python_m_pip = False
        elif bin_python.exists():
            # Linux/Mac 风格的虚拟环境（在 Windows 上）
            # 在 Windows 上，bin/python 是 shell 脚本，无法直接执行
            # 需要使用系统 Python，但指定虚拟环境的 site-packages
            # 或者直接使用系统 Python（因为虚拟环境可能不兼容）
            # 这里我们使用系统 Python，但安装到虚拟环境中
            python_venv = python_cmd  # 使用系统 Python
            use_python_m_pip = True
            # 设置环境变量，让 pip 安装到虚拟环境中
            venv_site_packages = str((Path('venv') / 'lib' / 'python3.9' / 'site-packages').resolve())
            os.environ['PYTHONPATH'] = venv_site_packages
        else:
            # 如果都不存在，尝试创建
            raise FileNotFoundError("虚拟环境结构异常，请重新创建虚拟环境")
    else:
        pip_cmd = 'venv/bin/pip'
        python_venv = 'venv/bin/python'
        use_python_m_pip = False
    
    # 安装依赖
    print_colored("📦 安装Python依赖...", 'blue')
    try:
        if use_python_m_pip:
            # 在 Windows 上，如果虚拟环境是 Linux 风格，使用 python -m pip
            print_colored(f"使用 Python: {python_venv}", 'cyan')
            subprocess.run([python_venv, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'], 
                           check=True)
        else:
            # 标准方式：直接使用 pip
            pip_cmd_abs = str(Path(pip_cmd).resolve())
            print_colored(f"使用 pip: {pip_cmd_abs}", 'cyan')
            subprocess.run([pip_cmd_abs, 'install', '-q', '-r', 'requirements.txt'], 
                           check=True)
    except FileNotFoundError as e:
        print_colored(f"错误: 找不到文件", 'red')
        print_colored(f"当前目录: {os.getcwd()}", 'yellow')
        raise
    
    return python_venv

def start_backend(python_cmd):
    """启动后端服务"""
    print_colored("🔧 启动后端服务器...", 'blue')
    print_colored(f"使用 Python: {python_cmd}", 'cyan')
    
    # 获取项目根目录
    script_dir = Path(__file__).parent.resolve()
    backend_dir = script_dir / 'backend'
    app_file = backend_dir / 'app.py'
    
    if not app_file.exists():
        raise FileNotFoundError(f"后端文件不存在: {app_file}")
    
    try:
        print_colored(f"后端目录: {backend_dir}", 'cyan')
        return subprocess.Popen([python_cmd, 'app.py'], cwd=str(backend_dir))
    except FileNotFoundError as e:
        print_colored(f"错误: 找不到文件 {python_cmd}", 'red')
        print_colored(f"当前目录: {os.getcwd()}", 'yellow')
        raise

def start_frontend():
    """启动前端服务"""
    print_colored("🎨 启动前端服务器...", 'blue')
    env = os.environ.copy()
    env['BROWSER'] = 'none'
    
    # 获取项目根目录
    script_dir = Path(__file__).parent.resolve()
    frontend_dir = script_dir / 'frontend'
    
    if not frontend_dir.exists():
        raise FileNotFoundError(f"前端目录不存在: {frontend_dir}")
    
    # 尝试找到npm命令
    npm_cmd = 'npm'
    if platform.system() == 'Windows':
        # Windows下尝试多个可能的npm路径
        possible_paths = [
            'npm.cmd',
            'npm',
            os.path.join(os.environ.get('ProgramFiles', ''), 'nodejs', 'npm.cmd'),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'nodejs', 'npm.cmd'),
        ]
        for path in possible_paths:
            try:
                subprocess.run([path, '--version'], capture_output=True, check=True, timeout=2)
                npm_cmd = path
                print_colored(f"找到 npm: {npm_cmd}", 'cyan')
                break
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
    
    try:
        print_colored(f"前端目录: {frontend_dir}", 'cyan')
        return subprocess.Popen([npm_cmd, 'start'], env=env, cwd=str(frontend_dir))
    except FileNotFoundError as e:
        print_colored(f"❌ 错误: 找不到 npm 命令", 'red')
        print_colored("请确保 Node.js 已安装并添加到 PATH", 'yellow')
        print_colored("下载地址: https://nodejs.org/", 'yellow')
        raise

def main():
    """主函数"""
    print_colored("🚀 启动健身AI应用...", 'green')
    
    # 获取脚本所在目录（项目根目录）
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)
    
    # 检查目录
    frontend_dir = script_dir / 'frontend'
    backend_dir = script_dir / 'backend'
    
    if not frontend_dir.exists() or not backend_dir.exists():
        print_colored("❌ 错误: 请在项目根目录运行此脚本", 'red')
        print_colored(f"当前目录: {script_dir}", 'yellow')
        print_colored(f"前端目录: {frontend_dir} (存在: {frontend_dir.exists()})", 'yellow')
        print_colored(f"后端目录: {backend_dir} (存在: {backend_dir.exists()})", 'yellow')
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
    
    backend_process = None
    frontend_process = None
    
    try:
        # 直接使用系统 Python，不使用虚拟环境
        print_colored("📦 安装Python依赖（使用系统Python）...", 'blue')
        requirements_file = backend_dir / 'requirements.txt'
        try:
            subprocess.run([python_cmd, '-m', 'pip', 'install', '-q', '-r', str(requirements_file)], 
                           check=True)
        except subprocess.CalledProcessError as e:
            print_colored("⚠️  依赖安装失败，尝试继续启动...", 'yellow')
        
        print_colored("🏃‍♂️ 后端运行在 http://localhost:8000", 'green')
        backend_process = start_backend(python_cmd)
        
        # 启动前端
        if not (frontend_dir / 'node_modules').exists():
            print_colored("📦 安装前端依赖...", 'blue')
            npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
            try:
                subprocess.run([npm_cmd, 'install'], check=True, cwd=str(frontend_dir))
            except subprocess.CalledProcessError:
                print_colored("⚠️  前端依赖安装失败，尝试继续启动...", 'yellow')
        
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
            
    except KeyboardInterrupt:
        print_colored("\n🛑 停止所有服务...", 'yellow')
        
    except Exception as e:
        import traceback
        print_colored(f"❌ 启动失败: {e}", 'red')
        print_colored(f"详细错误信息:", 'yellow')
        traceback.print_exc()
        
    finally:
        # 清理进程
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        
        # 额外清理端口
        time.sleep(2)
        kill_process_on_port(3000)
        kill_process_on_port(8000)
        
        print_colored("服务已停止", 'green')

if __name__ == '__main__':
    main() 