"""
测试所有导入是否正常
"""
import sys
import os

# 确保在backend目录
if os.path.basename(os.getcwd()) != 'backend':
    os.chdir('backend')

print("当前工作目录:", os.getcwd())
print("\nPython路径:")
for p in sys.path:
    print(f"  - {p}")

print("\n测试导入...")

try:
    from utils import validate_exercise_type
    print("✅ validate_exercise_type 导入成功")
    print(f"   函数: {validate_exercise_type}")
    print(f"   测试: validate_exercise_type('squat') = {validate_exercise_type('squat')}")
except ImportError as e:
    print(f"❌ validate_exercise_type 导入失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from database import db, Session, User
    print("✅ database 模块导入成功")
except ImportError as e:
    print(f"❌ database 模块导入失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from db_adapter import create_session
    print("✅ db_adapter 模块导入成功")
except ImportError as e:
    print(f"❌ db_adapter 模块导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ 所有导入测试完成")

