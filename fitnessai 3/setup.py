#!/usr/bin/env python3
"""
FitnessAI 项目设置脚本 - macOS版本
自动创建虚拟环境并安装依赖
"""

import os
import sys
import subprocess
import venv
from pathlib import Path

def run_command(cmd, description=""):
    """运行命令并处理错误"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 失败")
        print(f"错误: {e.stderr}")
        return False

def create_virtual_environment():
    """创建虚拟环境"""
    venv_path = Path("venv")
    
    # 如果虚拟环境已存在，删除它
    if venv_path.exists():
        print("🧹 清理旧的虚拟环境...")
        import shutil
        shutil.rmtree(venv_path)
    
    print("📦 创建新的虚拟环境...")
    try:
        venv.create("venv", with_pip=True)
        print("✅ 虚拟环境创建成功")
        return True
    except Exception as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return False

def install_python_dependencies():
    """安装Python依赖"""
    pip_path = "venv/bin/pip" if sys.platform != "win32" else "venv\\Scripts\\pip.exe"
    
    if not Path(pip_path).exists():
        print(f"❌ pip 不存在: {pip_path}")
        return False
    
    # 升级pip
    if not run_command(f"{pip_path} install --upgrade pip", "升级pip"):
        return False
    
    # 安装依赖
    if not run_command(f"{pip_path} install -r requirements.txt", "安装Python依赖"):
        return False
    
    return True

def setup_frontend():
    """设置前端环境"""
    if not Path("frontend").exists():
        print("❌ frontend 目录不存在")
        return False
    
    os.chdir("frontend")
    
    # 检查是否有package.json
    if not Path("package.json").exists():
        print("❌ package.json 不存在")
        os.chdir("..")
        return False
    
    # 安装npm依赖
    if not run_command("npm install", "安装前端依赖"):
        os.chdir("..")
        return False
    
    os.chdir("..")
    return True

def main():
    """主设置函数"""
    print("🚀 FitnessAI 项目设置开始")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 创建虚拟环境
    if not create_virtual_environment():
        return False
    
    # 安装Python依赖
    if not install_python_dependencies():
        return False
    
    # 设置前端
    print("\n🎨 设置前端环境...")
    if setup_frontend():
        print("✅ 前端环境设置完成")
    else:
        print("⚠️ 前端环境设置失败，但后端可以正常运行")
    
    print("\n" + "=" * 50)
    print("🎉 项目设置完成！")
    print("\n📋 启动说明:")
    print("1. 启动后端: python run_app.py")
    print("2. 启动前端: cd frontend && npm start")
    print("3. 访问应用: http://localhost:3000")
    print("\n或者使用简化启动:")
    print("python simple_start.py")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ 设置失败，请检查错误信息")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n🛑 设置被用户中断")
    except Exception as e:
        print(f"\n❌ 设置过程中出现错误: {e}")
        sys.exit(1) 