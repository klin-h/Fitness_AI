#!/usr/bin/env python3
"""
FitnessAI 环境检查脚本
检查系统依赖和环境配置
"""

import subprocess
import sys
import platform
from pathlib import Path

def check_command(command, description):
    """检查命令是否存在"""
    try:
        result = subprocess.run([command, '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"✅ {description}: {version}")
            return True
        else:
            print(f"❌ {description}: 命令执行失败")
            return False
    except FileNotFoundError:
        print(f"❌ {description}: 未安装")
        return False
    except Exception as e:
        print(f"❌ {description}: 检查失败 - {e}")
        return False

def check_python_packages():
    """检查Python包"""
    packages = [
        ('flask', 'Flask web框架'),
        ('flask_cors', 'Flask CORS支持'),
        ('numpy', 'NumPy数值计算'),
    ]
    
    print("\n📦 检查Python包:")
    missing_packages = []
    
    for package, description in packages:
        try:
            __import__(package)
            print(f"✅ {description}: 已安装")
        except ImportError:
            print(f"❌ {description}: 未安装")
            missing_packages.append(package)
    
    return missing_packages

def check_node_packages():
    """检查Node.js包"""
    if not Path('frontend/node_modules').exists():
        print("❌ 前端依赖: 未安装 (需要运行 npm install)")
        return False
    
    print("✅ 前端依赖: 已安装")
    return True

def check_ports():
    """检查端口占用"""
    print("\n🔌 检查端口占用:")
    
    system = platform.system()
    ports = [3000, 8000]
    
    for port in ports:
        try:
            if system == 'Windows':
                result = subprocess.run(['netstat', '-ano'], 
                                      capture_output=True, text=True)
                if f':{port}' in result.stdout:
                    print(f"⚠️  端口 {port}: 被占用")
                else:
                    print(f"✅ 端口 {port}: 可用")
            else:
                result = subprocess.run(['lsof', f'-i:{port}'], 
                                      capture_output=True, text=True)
                if result.stdout.strip():
                    print(f"⚠️  端口 {port}: 被占用")
                else:
                    print(f"✅ 端口 {port}: 可用")
        except Exception:
            print(f"❓ 端口 {port}: 无法检查")

def check_browser_support():
    """检查浏览器支持"""
    print("\n🌐 浏览器兼容性检查:")
    
    browsers = {
        'Chrome': '建议使用最新版本',
        'Firefox': '建议使用最新版本', 
        'Safari': '建议使用最新版本',
        'Edge': '建议使用最新版本'
    }
    
    for browser, note in browsers.items():
        print(f"📱 {browser}: {note}")
    
    print("⚠️  注意: MediaPipe需要现代浏览器支持WebGL和摄像头访问")

def main():
    """主检查函数"""
    print("🔍 FitnessAI 环境检查")
    print("=" * 50)
    
    print(f"🖥️  操作系统: {platform.system()} {platform.release()}")
    print(f"🐍 Python版本: {sys.version}")
    
    print("\n📋 检查系统依赖:")
    
    # 检查基础工具
    checks = [
        ('node', 'Node.js'),
        ('npm', 'npm包管理器'),
        ('git', 'Git版本控制'),
    ]
    
    # 添加Python命令检查
    python_cmd = None
    for cmd in ['python3', 'python']:
        if check_command(cmd, f'Python ({cmd})'):
            python_cmd = cmd
            break
    
    if not python_cmd:
        print("❌ 没有找到可用的Python命令")
        failed = True
    else:
        failed = False
    
    # 检查其他工具
    for cmd, desc in checks:
        if not check_command(cmd, desc):
            failed = True
    
    # 检查Python包
    missing_packages = check_python_packages()
    
    # 检查Node.js包
    if not check_node_packages():
        print("💡 提示: 在frontend目录运行 'npm install' 安装前端依赖")
    
    # 检查端口
    check_ports()
    
    # 检查浏览器支持
    check_browser_support()
    
    print("\n" + "=" * 50)
    
    if failed or missing_packages:
        print("❌ 环境检查发现问题，请解决后重试")
        
        if missing_packages:
            print(f"\n📦 需要安装的Python包:")
            for package in missing_packages:
                print(f"   pip install {package}")
            print("\n或者运行: pip install -r backend/requirements.txt")
        
        print("\n🔧 修复建议:")
        print("1. 确保安装了 Node.js (https://nodejs.org/)")
        print("2. 确保安装了 Python 3.8+ (https://python.org/)")
        print("3. 在backend目录运行: pip install -r requirements.txt")
        print("4. 在frontend目录运行: npm install")
        
        sys.exit(1)
    else:
        print("✅ 环境检查通过！可以启动应用程序")
        print("\n🚀 启动命令:")
        print("Mac/Linux: ./start.sh")
        print("Windows:   start.bat")
        print("跨平台:    python start.py")

if __name__ == '__main__':
    main() 