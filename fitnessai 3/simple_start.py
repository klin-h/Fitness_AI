#!/usr/bin/env python3
"""
FitnessAI 简单启动脚本
直接使用系统Python运行，无需虚拟环境
"""

import os
import sys
import subprocess
import pkg_resources
from pathlib import Path

def check_and_install_dependencies():
    """检查并安装所需的Python包"""
    required_packages = [
        'flask',
        'flask-cors',
        'numpy',
        'opencv-python',
        'mediapipe'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            pkg_resources.get_distribution(package)
            print(f"✅ {package} 已安装")
        except pkg_resources.DistributionNotFound:
            missing_packages.append(package)
            print(f"❌ {package} 未安装")
    
    if missing_packages:
        print(f"\n📦 安装缺失的包: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--user"
            ] + missing_packages)
            print("✅ 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            return False
    
    return True

def start_backend():
    """启动后端服务"""
    print("🚀 启动FitnessAI后端服务...")
    
    # 设置multiprocessing
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass
    
    # 启动Flask应用
    from app import app
    
    print("📱 后端服务启动中...")
    print("🔗 访问地址:")
    print("   - API: http://localhost:8000/api")
    print("   - 演示: http://localhost:8000/demo")
    print("   - 前端: http://localhost:3000 (需单独启动)")
    print("\n💡 提示: 按 Ctrl+C 停止服务")
   
    try:
        app.run(
            debug=False,
            host='0.0.0.0',
            port=8000,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

def main():
    """主函数"""
    print("🏃‍♀️ FitnessAI 简单启动器")
    print("=" * 40)
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version.split()[0]}")
    
    # 检查并安装依赖
    if not check_and_install_dependencies():
        print("❌ 依赖安装失败")
        return False
    
    # 启动后端
    start_backend()

if __name__ == "__main__":
    main() 