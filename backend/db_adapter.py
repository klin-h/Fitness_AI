"""
数据库适配层
提供与JSON文件操作兼容的接口，底层使用数据库
包含完整的错误处理和事务管理
"""
from database import db, User, UserProfile, Token, Plan, Session, UserAchievement, Checkin, ChallengeCompletion
from datetime import datetime, date
import json
import logging
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from utils import db_transaction

logger = logging.getLogger(__name__)

# ==================== 用户相关 ====================

def load_users():
    """加载所有用户（兼容旧接口）"""
    users = User.query.all()
    result = {}
    for user in users:
        result[user.user_id] = user.to_dict()
        result[user.user_id]['password_hash'] = user.password_hash
    return result

def save_users(users_dict):
    """保存用户（兼容旧接口）"""
    # 这个方法主要用于兼容，实际应该使用ORM直接操作
    pass

def get_user_by_id(user_id):
    """根据ID获取用户"""
    return User.query.get(user_id)

def get_user_by_username(username):
    """根据用户名获取用户"""
    return User.query.filter_by(username=username).first()

@db_transaction
def create_user(user_data):
    """创建新用户"""
    try:
        user = User(**user_data)
        db.session.add(user)
        return user
    except IntegrityError as e:
        logger.error(f"创建用户失败（可能用户名已存在）: {str(e)}")
        db.session.rollback()
        raise ValueError("用户名已存在")
    except Exception as e:
        logger.error(f"创建用户失败: {str(e)}")
        db.session.rollback()
        raise

@db_transaction
def update_user(user_id, user_data):
    """更新用户"""
    try:
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        for key, value in user_data.items():
            if hasattr(user, key) and key != 'user_id':  # 不允许修改主键
                setattr(user, key, value)
        return user
    except Exception as e:
        logger.error(f"更新用户失败: {str(e)}")
        db.session.rollback()
        raise

# ==================== Token相关 ====================

def load_tokens():
    """加载所有token（兼容旧接口）"""
    tokens = Token.query.all()
    result = {}
    for token in tokens:
        result[token.token] = {
            'user_id': token.user_id,
            'expire_time': token.expire_time.isoformat()
        }
    return result

@db_transaction
def save_token(token_str, user_id, expire_time):
    """保存token"""
    try:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        token = Token(
            token=token_str,
            user_id=user_id,
            expire_time=expire_time
        )
        db.session.add(token)
    except IntegrityError as e:
        logger.warning(f"Token已存在，跳过: {str(e)}")
        db.session.rollback()
        # Token已存在不算错误，直接返回
    except Exception as e:
        logger.error(f"保存token失败: {str(e)}")
        db.session.rollback()
        raise

@db_transaction
def delete_token(token_str):
    """删除token"""
    try:
        deleted = Token.query.filter_by(token=token_str).delete()
        if deleted == 0:
            logger.warning(f"尝试删除不存在的token: {token_str}")
    except Exception as e:
        logger.error(f"删除token失败: {str(e)}")
        db.session.rollback()
        raise

def get_token(token_str):
    """获取token"""
    return Token.query.get(token_str)

# ==================== 计划相关 ====================

def load_plans():
    """加载所有计划（兼容旧接口）"""
    plans = Plan.query.all()
    result = {}
    for plan in plans:
        result[plan.user_id] = plan.to_dict()
    return result

def get_user_plan(user_id):
    """获取用户计划"""
    try:
        plan = Plan.query.filter_by(user_id=user_id).first()
        return plan.to_dict() if plan else None
    except Exception as e:
        logger.error(f"获取用户计划失败: {str(e)}", exc_info=True)
        return None

@db_transaction
def save_user_plan(user_id, plan_data):
    """保存用户计划"""
    try:
        # 验证用户是否存在
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        # 验证JSON数据
        daily_goals = plan_data.get('daily_goals', {})
        weekly_goals = plan_data.get('weekly_goals', {})
        custom_goal = plan_data.get('custom_goal')
        ai_advice = plan_data.get('ai_advice')
        
        plan = Plan.query.filter_by(user_id=user_id).first()
        if plan:
            plan.daily_goals = json.dumps(daily_goals)
            plan.weekly_goals = json.dumps(weekly_goals)
            if custom_goal:
                plan.custom_goal = custom_goal
            if ai_advice:
                plan.ai_advice = ai_advice
            plan.updated_at = datetime.utcnow()
        else:
            plan = Plan(
                user_id=user_id,
                daily_goals=json.dumps(daily_goals),
                weekly_goals=json.dumps(weekly_goals),
                custom_goal=custom_goal,
                ai_advice=ai_advice
            )
            db.session.add(plan)
        return plan
    except (ValueError, TypeError) as e:
        logger.error(f"保存计划失败（数据格式错误）: {str(e)}")
        db.session.rollback()
        raise ValueError(f"计划数据格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"保存计划失败: {str(e)}")
        db.session.rollback()
        raise

# ==================== 会话相关 ====================

def load_sessions():
    """加载所有会话（兼容旧接口）"""
    sessions = Session.query.all()
    result = {}
    for session in sessions:
        result[session.session_id] = session.to_dict()
    return result

def get_session(session_id):
    """获取会话"""
    session = Session.query.get(session_id)
    return session.to_dict() if session else None

@db_transaction
def create_session(session_data):
    """创建会话"""
    # 验证必需字段
    required_fields = ['session_id', 'user_id', 'exercise_type', 'start_time']
    for field in required_fields:
        if field not in session_data:
            raise ValueError(f"缺少必需字段: {field}")
    
    # 验证用户是否存在（允许匿名用户）
    user_id = session_data['user_id']
    if user_id != 'anonymous':
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"用户不存在: {user_id}，但允许创建会话")
    
    # 解析start_time
    start_time = session_data['start_time']
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    
    session = Session(
        session_id=session_data['session_id'],
        user_id=user_id,
        exercise_type=session_data['exercise_type'],
        start_time=start_time,
        total_count=session_data.get('total_count', 0),
        correct_count=session_data.get('correct_count', 0),
        status=session_data.get('status', 'active'),
        scores=json.dumps(session_data.get('scores', []))
    )
    db.session.add(session)
    logger.info(f"准备创建会话: {session_data['session_id']}")
    return session

@db_transaction
def update_session(session_id, session_data):
    """更新会话"""
    try:
        session = Session.query.get(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        if 'end_time' in session_data:
            session.end_time = datetime.fromisoformat(session_data['end_time']) if session_data['end_time'] and isinstance(session_data['end_time'], str) else session_data['end_time']
        if 'total_count' in session_data:
            session.total_count = max(0, int(session_data['total_count']))  # 确保非负
        if 'correct_count' in session_data:
            session.correct_count = max(0, int(session_data['correct_count']))  # 确保非负
        if 'status' in session_data:
            if session_data['status'] not in ['active', 'completed', 'cancelled']:
                raise ValueError(f"无效的状态: {session_data['status']}")
            session.status = session_data['status']
        if 'scores' in session_data:
            session.scores = json.dumps(session_data['scores'])
        
        return session
    except (ValueError, TypeError) as e:
        logger.error(f"更新会话失败（数据验证错误）: {str(e)}")
        db.session.rollback()
        raise ValueError(f"会话数据错误: {str(e)}")
    except Exception as e:
        logger.error(f"更新会话失败: {str(e)}")
        db.session.rollback()
        raise

def get_user_sessions(user_id, limit=None, exercise_type=None):
    """获取用户会话"""
    query = Session.query.filter_by(user_id=user_id)
    if exercise_type:
        query = query.filter_by(exercise_type=exercise_type)
    query = query.order_by(Session.start_time.desc())
    if limit:
        query = query.limit(limit)
    sessions = query.all()
    return [s.to_dict() for s in sessions]

# ==================== 成就相关 ====================

def load_achievements():
    """加载所有成就（兼容旧接口）"""
    achievements = UserAchievement.query.all()
    result = {}
    for achievement in achievements:
        if achievement.user_id not in result:
            result[achievement.user_id] = {}
        result[achievement.user_id][achievement.achievement_id] = achievement.to_dict()
    return result

def get_user_achievements(user_id):
    """获取用户成就"""
    achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    return {a.achievement_id: a.to_dict() for a in achievements}

@db_transaction
def unlock_achievement(user_id, achievement_id, unlocked_at=None):
    """解锁成就"""
    try:
        # 验证用户是否存在
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        if not unlocked_at:
            unlocked_at = datetime.utcnow()
        
        # 检查是否已解锁
        existing = UserAchievement.query.filter_by(
            user_id=user_id,
            achievement_id=achievement_id
        ).first()
        
        if not existing:
            achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement_id,
                unlocked_at=unlocked_at
            )
            db.session.add(achievement)
            logger.info(f"用户 {user_id} 解锁成就 {achievement_id}")
            return True
        return False
    except IntegrityError as e:
        logger.warning(f"成就已解锁: {str(e)}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.error(f"解锁成就失败: {str(e)}")
        db.session.rollback()
        raise

# ==================== 打卡相关 ====================

def get_user_checkin_stats(user_id):
    """获取用户打卡统计"""
    return Checkin.get_user_checkin_stats(user_id)

@db_transaction
def add_checkin(user_id, checkin_date=None):
    """添加打卡记录"""
    try:
        # 验证用户是否存在
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        if not checkin_date:
            checkin_date = date.today()
        
        # 检查是否已打卡
        existing = Checkin.query.filter_by(
            user_id=user_id,
            checkin_date=checkin_date
        ).first()
        
        if not existing:
            checkin = Checkin(
                user_id=user_id,
                checkin_date=checkin_date
            )
            db.session.add(checkin)
            logger.info(f"用户 {user_id} 打卡成功: {checkin_date}")
            return True
        return False
    except IntegrityError as e:
        logger.warning(f"用户 {user_id} 今天已打卡")
        db.session.rollback()
        return False
    except Exception as e:
        logger.error(f"添加打卡记录失败: {str(e)}")
        db.session.rollback()
        raise

def get_checkin_calendar(user_id, days=90):
    """获取打卡日历"""
    from datetime import timedelta
    today = date.today()
    start_date = today - timedelta(days=days)
    
    checkins = Checkin.query.filter(
        Checkin.user_id == user_id,
        Checkin.checkin_date >= start_date
    ).all()
    
    checkin_dates = {c.checkin_date.isoformat(): True for c in checkins}
    
    # 生成所有日期
    calendar = {}
    for i in range(days):
        d = today - timedelta(days=i)
        calendar[d.isoformat()] = d.isoformat() in checkin_dates
    
    return calendar

# ==================== 挑战相关 ====================

def get_challenge_completions(user_id, date_str=None):
    """获取挑战完成记录"""
    if date_str:
        completion_date = datetime.fromisoformat(date_str).date()
        completions = ChallengeCompletion.query.filter_by(
            user_id=user_id,
            completion_date=completion_date
        ).all()
    else:
        completions = ChallengeCompletion.query.filter_by(user_id=user_id).all()
    
    return [c.challenge_id for c in completions]

@db_transaction
def complete_challenge(user_id, challenge_id, completion_date=None):
    """完成挑战"""
    try:
        # 验证用户是否存在
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        
        if not challenge_id:
            raise ValueError("挑战ID不能为空")
        
        if not completion_date:
            completion_date = date.today()
        
        # 检查是否已完成
        existing = ChallengeCompletion.query.filter_by(
            user_id=user_id,
            challenge_id=challenge_id,
            completion_date=completion_date
        ).first()
        
        if not existing:
            completion = ChallengeCompletion(
                user_id=user_id,
                challenge_id=challenge_id,
                completion_date=completion_date
            )
            db.session.add(completion)
            logger.info(f"用户 {user_id} 完成挑战 {challenge_id}")
            return True
        return False
    except IntegrityError as e:
        logger.warning(f"挑战已完成: {str(e)}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.error(f"完成挑战失败: {str(e)}")
        db.session.rollback()
        raise

