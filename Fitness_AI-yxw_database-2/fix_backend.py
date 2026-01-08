"""
快速修复后端数据库问题
"""
import os
import sys
from pathlib import Path

print("🔧 开始修复后端数据库问题...")

# 1. 删除旧的数据库文件
db_files = ['fitnessai.db', 'backend/fitnessai.db']
for db_file in db_files:
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"✅ 已删除旧数据库文件: {db_file}")
        except Exception as e:
            print(f"⚠️  删除 {db_file} 失败: {e}")

# 2. 切换到后端目录
backend_dir = Path('backend')
if not backend_dir.exists():
    print("❌ 后端目录不存在")
    sys.exit(1)

os.chdir(backend_dir)
print(f"📁 当前目录: {os.getcwd()}")

# 3. 更新数据库表结构
try:
    # 添加当前目录到Python路径
    sys.path.insert(0, os.getcwd())
    
    from database import db
    from app import app
    
    print("🔄 重新创建数据库表...")
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ 数据库表已重新创建")
        
        # 测试数据库连接
        db.session.execute(db.text('SELECT 1'))
        print("✅ 数据库连接测试成功")
        
except Exception as e:
    print(f"❌ 数据库更新失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ 修复完成！")
print("💡 现在可以启动后端了：")
print("   cd backend")
print("   python app.py")

