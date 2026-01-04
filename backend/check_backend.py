"""
快速检查后端服务器状态
"""
import requests
import sys

try:
    response = requests.get('http://localhost:8000/api/health', timeout=2)
    if response.status_code == 200:
        print("✅ 后端服务器运行正常")
        print(f"响应: {response.json()}")
        sys.exit(0)
    else:
        print(f"⚠️  后端服务器响应异常: {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("❌ 后端服务器未启动或无法连接")
    print("💡 请检查:")
    print("   1. 后端服务是否已启动")
    print("   2. 端口8000是否被占用")
    print("   3. 防火墙是否阻止了连接")
    sys.exit(1)
except Exception as e:
    print(f"❌ 检查后端时出错: {e}")
    sys.exit(1)

