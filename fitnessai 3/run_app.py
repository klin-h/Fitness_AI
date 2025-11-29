#!/usr/bin/env python3
"""
FitnessAI 应用启动入口
解决multiprocessing semaphore泄漏问题
"""

import multiprocessing
import sys
import os

def main():
    """主函数，设置multiprocessing上下文"""
    # 设置multiprocessing启动方法
    if __name__ == '__main__':
        try:
            # 在macOS上使用spawn方法避免semaphore泄漏
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            pass  # 已经设置过了
    
    # 导入并启动Flask应用
    from app import app
    
    print("🚀 启动FitnessAI应用...")
    print("📱 访问: http://localhost:8000")
    print("🎯 演示页面: http://localhost:8000/demo")
    print("🔧 API状态: http://localhost:8000/api")
    
    # 使用生产模式配置避免额外进程
    app.run(
        debug=False,
        host='0.0.0.0',
        port=8000,
        threaded=True,
        use_reloader=False
    )

if __name__ == '__main__':
    main() 