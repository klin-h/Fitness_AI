"""
生成测试数据脚本
用于快速测试成就、排行榜等功能
"""
import sys
import os
from datetime import datetime, timedelta, date
import random

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import db, Session, User, ChallengeCompletion, Checkin, UserAchievement
from db_adapter import create_session, update_session, complete_challenge, add_checkin, unlock_achievement
import json

def generate_test_sessions(user_id, days=30, start_date=None):
    """生成过去N天的会话数据"""
    if start_date:
        print(f"📊 为用户 {user_id} 生成从 {start_date} 开始的 {days} 天会话数据...")
    else:
        print(f"📊 为用户 {user_id} 生成过去 {days} 天的会话数据...")
    
    exercise_types = ['squat', 'pushup', 'plank', 'jumping_jack']
    sessions_created = 0
    
    # 确定起始日期
    if start_date:
        base_date = start_date
    else:
        base_date = date.today()
    
    # 如果指定了起始日期，从该日期往前生成（从最新日期到最早日期）
    # 否则从今天往前生成
    for day_offset in range(days):
        if start_date:
            # 从起始日期往前倒推（从1月31日到1月1日）
            session_date = base_date - timedelta(days=days - 1 - day_offset)
        else:
            # 从今天往前倒推
            session_date = base_date - timedelta(days=day_offset)
        
        # 每天随机生成1-3个会话
        num_sessions = random.randint(1, 3)
        
        for session_num in range(num_sessions):
            exercise_type = random.choice(exercise_types)
            
            # 生成会话时间
            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            start_time = datetime.combine(session_date, datetime.min.time().replace(hour=hour, minute=minute))
            
            # 根据运动类型生成不同的数据
            if exercise_type == 'plank':
                # 平板支撑：时长类
                duration_seconds = random.randint(30, 180)
                total_count = 0
                correct_count = 0
                end_time = start_time + timedelta(seconds=duration_seconds)
            else:
                # 计数类运动
                total_count = random.randint(10, 50)
                correct_count = int(total_count * random.uniform(0.7, 1.0))
                duration_seconds = random.randint(60, 600)
                end_time = start_time + timedelta(seconds=duration_seconds)
            
            # 生成分数记录
            scores = []
            for i in range(total_count if total_count > 0 else 1):
                scores.append({
                    "timestamp": (start_time + timedelta(seconds=i*5)).isoformat(),
                    "score": random.randint(70, 100),
                    "is_correct": i < correct_count if total_count > 0 else True,
                    "feedback": "动作标准" if random.random() > 0.3 else "需要改进"
                })
            
            session_id = f"{user_id}_{session_date.strftime('%Y%m%d')}_{session_num}"
            
            try:
                session_data = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "exercise_type": exercise_type,
                    "start_time": start_time.isoformat(),
                    "total_count": total_count,
                    "correct_count": correct_count,
                    "status": "completed",
                    "scores": scores
                }
                
                # 创建会话
                session = create_session(session_data)
                db.session.commit()
                
                # 更新结束时间和分数
                session_obj = Session.query.get(session_id)
                if session_obj:
                    session_obj.end_time = end_time
                    session_obj.status = 'completed'
                    session_obj.scores = json.dumps(scores)
                    db.session.commit()
                
                sessions_created += 1
            except Exception as e:
                print(f"  ⚠️  创建会话失败 {session_id}: {e}")
                db.session.rollback()
    
    print(f"✅ 成功创建 {sessions_created} 个会话")
    return sessions_created

def generate_challenge_completions(user_id, days=30, start_date=None):
    """生成挑战完成记录"""
    print(f"🎯 为用户 {user_id} 生成挑战完成记录...")
    
    challenges = [
        "squat_50",
        "pushup_30",
        "plank_120",
        "combo_challenge"
    ]
    
    completions_created = 0
    
    # 确定起始日期
    if start_date:
        base_date = start_date
    else:
        base_date = date.today()
    
    # 随机选择一些日期完成挑战
    for day_offset in range(days):
        if random.random() > 0.6:  # 60%的概率完成挑战
            if start_date:
                # 从起始日期往前倒推
                completion_date = base_date - timedelta(days=days - 1 - day_offset)
            else:
                completion_date = base_date - timedelta(days=day_offset)
            challenge_id = random.choice(challenges)
            
            try:
                success = complete_challenge(user_id, challenge_id, completion_date)
                if success:
                    completions_created += 1
            except Exception as e:
                print(f"  ⚠️  完成挑战失败 {challenge_id}: {e}")
    
    print(f"✅ 成功创建 {completions_created} 个挑战完成记录")
    return completions_created

def generate_checkins(user_id, days=30, start_date=None):
    """生成打卡记录"""
    print(f"📅 为用户 {user_id} 生成打卡记录...")
    
    checkins_created = 0
    
    # 确定起始日期
    if start_date:
        base_date = start_date
    else:
        base_date = date.today()
    
    # 生成连续打卡（模拟连续打卡）
    streak_start = days - random.randint(5, 15)  # 最近5-15天开始连续打卡
    
    for day_offset in range(days):
        if start_date:
            # 从起始日期往前倒推
            checkin_date = base_date - timedelta(days=days - 1 - day_offset)
        else:
            checkin_date = base_date - timedelta(days=day_offset)
        
        # 如果是在连续打卡期间，或者随机打卡
        if day_offset <= streak_start or random.random() > 0.7:
            try:
                add_checkin(user_id, checkin_date)  # 传入 date 对象而不是字符串
                checkins_created += 1
            except Exception as e:
                # 可能已经打卡过了，忽略
                pass
    
    print(f"✅ 成功创建 {checkins_created} 个打卡记录")
    return checkins_created

def generate_all_test_data(user_id=None, days=30, start_date=None):
    """生成所有测试数据"""
    with app.app_context():
        # 如果没有指定用户ID，使用第一个用户
        if not user_id:
            user = User.query.first()
            if not user:
                print("❌ 没有找到用户，请先注册一个用户")
                return
            user_id = user.user_id
            print(f"📝 使用用户: {user.username} ({user_id})")
        else:
            user = User.query.get(user_id)
            if not user:
                print(f"❌ 用户不存在: {user_id}")
                return
        
        if start_date:
            print(f"\n🚀 开始为用户 {user_id} 生成测试数据（从 {start_date} 开始的 {days} 天）...\n")
        else:
            print(f"\n🚀 开始为用户 {user_id} 生成测试数据（过去 {days} 天）...\n")
        
        # 生成会话数据
        sessions_count = generate_test_sessions(user_id, days, start_date)
        
        # 生成挑战完成记录
        challenges_count = generate_challenge_completions(user_id, days, start_date)
        
        # 生成打卡记录
        checkins_count = generate_checkins(user_id, days, start_date)
        
        print(f"\n✅ 测试数据生成完成！")
        print(f"   - 会话: {sessions_count} 个")
        print(f"   - 挑战完成: {challenges_count} 个")
        print(f"   - 打卡: {checkins_count} 个")
        print(f"\n💡 现在可以测试成就、排行榜等功能了！")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='生成测试数据')
    parser.add_argument('--user-id', type=str, help='用户ID（可选，默认使用第一个用户）')
    parser.add_argument('--days', type=int, default=30, help='生成N天的数据（默认30天）')
    parser.add_argument('--month', type=int, help='指定月份（1-12），生成该月的数据')
    parser.add_argument('--year', type=int, default=2025, help='指定年份（默认2025）')
    parser.add_argument('--start-date', type=str, help='起始日期（YYYY-MM-DD格式）')
    
    args = parser.parse_args()
    
    # 处理日期参数
    start_date = None
    days = args.days
    
    if args.start_date:
        # 使用指定的起始日期
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    elif args.month:
        # 生成指定月份的数据
        year = args.year
        month = args.month
        # 计算该月的天数
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        # 使用该月的最后一天作为起始日期（这样往前倒推会从最后一天到第一天）
        days = (next_month - date(year, month, 1)).days
        start_date = date(year, month, days)  # 该月的最后一天
        print(f"📅 生成 {year}年{month}月的数据（共 {days} 天，从 {start_date} 往前生成）")
    
    generate_all_test_data(args.user_id, days, start_date)

