"""
修复数据库中准确率异常的数据
确保所有会话的 correct_count <= total_count
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import db, Session

def fix_accuracy_data():
    """修复所有会话的准确率数据"""
    with app.app_context():
        # 查询所有会话
        sessions = Session.query.all()
        fixed_count = 0
        
        print(f"开始检查 {len(sessions)} 个会话...")
        
        for session in sessions:
            original_correct = session.correct_count
            original_total = session.total_count
            
            # 修复 correct_count > total_count 的情况
            if session.total_count > 0 and session.correct_count > session.total_count:
                session.correct_count = session.total_count
                fixed_count += 1
                print(f"修复会话 {session.session_id}: "
                      f"correct_count {original_correct} -> {session.correct_count}, "
                      f"total_count {original_total}")
            # 修复负数情况
            elif session.correct_count < 0:
                session.correct_count = 0
                fixed_count += 1
                print(f"修复会话 {session.session_id}: "
                      f"correct_count {original_correct} -> 0 (负数)")
            elif session.total_count < 0:
                session.total_count = 0
                fixed_count += 1
                print(f"修复会话 {session.session_id}: "
                      f"total_count {original_total} -> 0 (负数)")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ 成功修复 {fixed_count} 个会话的数据")
        else:
            print("\n✅ 所有数据正常，无需修复")
        
        # 显示统计信息
        print("\n数据统计:")
        total_sessions = Session.query.count()
        abnormal_sessions = Session.query.filter(
            Session.total_count > 0,
            Session.correct_count > Session.total_count
        ).count()
        
        print(f"  总会话数: {total_sessions}")
        print(f"  异常会话数: {abnormal_sessions}")
        
        if abnormal_sessions == 0:
            print("\n✅ 所有会话数据正常！")

if __name__ == '__main__':
    fix_accuracy_data()

