"""
数据库初始化脚本
运行此脚本可以初始化PostgreSQL数据库并迁移JSON数据
"""
import os
import sys
from app import app
from database import init_db, migrate_from_json

def check_postgresql_connection():
    """检查PostgreSQL连接"""
    try:
        with app.app_context():
            from database import db
            db.engine.connect()
            print("✅ PostgreSQL连接成功")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL连接失败: {e}")
        print("\n💡 请确保:")
        print("   1. PostgreSQL已安装并运行")
        print("   2. 数据库已创建: createdb -U postgres fitnessai")
        print("   3. .env文件中的DATABASE_URL配置正确")
        print("\n📖 详细设置指南请查看: setup_postgresql.md")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 FitnessAI PostgreSQL 数据库初始化工具")
    print("=" * 60)
    
    # 检查连接
    if not check_postgresql_connection():
        sys.exit(1)
    
    # 初始化数据库
    print("\n📦 正在初始化数据库表...")
    try:
        init_db(app)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)
    
    # 迁移JSON数据
    print("\n📥 正在检查是否需要迁移JSON数据...")
    try:
        migrate_from_json(app)
    except Exception as e:
        print(f"⚠️  数据迁移失败: {e}")
        print("   这可能是正常的（如果没有JSON数据需要迁移）")
    
    print("\n✅ 数据库初始化完成！")
    print("=" * 60)
    print("\n🎉 现在可以启动应用了:")
    print("   python app.py")
