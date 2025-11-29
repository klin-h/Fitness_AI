#!/usr/bin/env python3
"""
FitnessAI 状态检查脚本
检查前后端服务运行状态
"""

import subprocess
import requests
import time

def main():
    print('🔍 FitnessAI 状态检查')
    print('=' * 40)

    # 检查后端
    try:
        r = requests.get('http://localhost:8000/api', timeout=2)
        if r.status_code == 200:
            data = r.json()
            print(f'✅ 后端 (8000): {data["status"]}')
        else:
            print(f'⚠️ 后端 (8000): 状态码 {r.status_code}')
    except Exception as e:
        print(f'❌ 后端 (8000): 未运行 ({e})')

    # 检查前端
    try:
        r = requests.get('http://localhost:3000', timeout=5)
        if r.status_code == 200:
            print('✅ 前端 (3000): 正常运行')
        else:
            print(f'⚠️ 前端 (3000): 状态码 {r.status_code}')
    except requests.exceptions.ConnectionError:
        print('❌ 前端 (3000): 连接被拒绝')
    except requests.exceptions.Timeout:
        print('⚠️ 前端 (3000): 响应超时（可能正在启动）')
    except Exception as e:
        print(f'❌ 前端 (3000): 未响应 ({e})')

    # 检查进程
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        python_procs = [line for line in lines if 'python' in line and ('run_app' in line or 'app.py' in line or 'simple_start' in line)]
        npm_procs = [line for line in lines if 'npm' in line and 'start' in line]
        node_procs = [line for line in lines if 'node' in line and ('react-scripts' in line or 'webpack' in line)]
        
        print(f'\n📊 运行中的进程:')
        print(f'   Python (后端): {len(python_procs)}')
        print(f'   npm (前端): {len(npm_procs)}')
        print(f'   Node.js (前端): {len(node_procs)}')
        
        if python_procs:
            print('   🐍 Python进程详情:')
            for proc in python_procs[:2]:  # 只显示前2个
                parts = proc.split()
                if len(parts) > 10:
                    print(f'      PID: {parts[1]}, 命令: {" ".join(parts[10:13])}...')
        
        if npm_procs or node_procs:
            print('   📦 前端进程详情:')
            for proc in (npm_procs + node_procs)[:2]:
                parts = proc.split()
                if len(parts) > 10:
                    print(f'      PID: {parts[1]}, 命令: {" ".join(parts[10:13])}...')
        
    except Exception as e:
        print(f'⚠️ 进程检查失败: {e}')

    print('\n🚀 启动说明:')
    print('   后端: python3 run_app.py')
    print('   前端: cd frontend && npm start')
    print('   完整: python3 start_macos.py')
    
    print('\n🔗 访问地址:')
    print('   主应用: http://localhost:3000')
    print('   后端API: http://localhost:8000/api')
    print('   演示页面: http://localhost:8000/demo')

if __name__ == "__main__":
    main() 