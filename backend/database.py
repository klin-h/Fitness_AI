"""
数据库模型和初始化
默认使用SQLite（本地开发），支持PostgreSQL（生产环境）
支持本地开发和服务器部署
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

# ==================== 数据库模型 ====================

class User(db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    user_id = db.Column(db.String(100), primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    nickname = db.Column(db.String(100))
    avatar = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联关系
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    plans = db.relationship('Plan', backref='user', uselist=False, cascade='all, delete-orphan')
    # 注意：由于移除了Session表的外键约束（允许匿名用户），
    # 这里暂时注释掉sessions relationship，避免SQLAlchemy关系映射错误
    # 如果需要查询用户的会话，可以直接使用Session.query.filter_by(user_id=...)
    # sessions = db.relationship('Session', backref='user', lazy='dynamic')
    achievements = db.relationship('UserAchievement', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    checkins = db.relationship('Checkin', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    challenge_completions = db.relationship('ChallengeCompletion', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'profile': self.profile.to_dict() if self.profile else {}
        }


class UserProfile(db.Model):
    """用户资料表"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('users.user_id'), unique=True, nullable=False)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    body_fat = db.Column(db.Float)  # 体脂率
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'height': self.height,
            'weight': self.weight,
            'body_fat': self.body_fat,
            'age': self.age,
            'gender': self.gender
        }


class Token(db.Model):
    """Token表"""
    __tablename__ = 'tokens'
    
    token = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('users.user_id'), nullable=False)
    expire_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Plan(db.Model):
    """健身计划表"""
    __tablename__ = 'plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('users.user_id'), unique=True, nullable=False)
    daily_goals = db.Column(db.Text)  # JSON字符串
    weekly_goals = db.Column(db.Text)  # JSON字符串
    custom_goal = db.Column(db.String(50))  # 用户自定义目标 (weight_loss, muscle_gain, etc.)
    ai_advice = db.Column(db.Text)  # AI生成的建议对话
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        daily_goals_data = {}
        if self.daily_goals:
            if isinstance(self.daily_goals, str):
                try:
                    daily_goals_data = json.loads(self.daily_goals)
                except:
                    daily_goals_data = {}
            else:
                daily_goals_data = self.daily_goals

        weekly_goals_data = {}
        if self.weekly_goals:
            if isinstance(self.weekly_goals, str):
                try:
                    weekly_goals_data = json.loads(self.weekly_goals)
                except:
                    weekly_goals_data = {}
            else:
                weekly_goals_data = self.weekly_goals

        return {
            'daily_goals': daily_goals_data,
            'weekly_goals': weekly_goals_data,
            'custom_goal': self.custom_goal,
            'ai_advice': self.ai_advice,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Session(db.Model):
    """运动会话表"""
    __tablename__ = 'sessions'
    
    session_id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)  # 移除外键约束，允许匿名用户
    exercise_type = db.Column(db.String(50), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, index=True)
    total_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active', index=True)
    scores = db.Column(db.Text)  # JSON字符串，存储所有得分记录
    
    # 添加复合索引以提高查询性能
    __table_args__ = (
        db.Index('idx_user_status_time', 'user_id', 'status', 'start_time'),
        db.Index('idx_user_exercise_time', 'user_id', 'exercise_type', 'start_time'),
    )
    
    def to_dict(self):
        scores_data = []
        if self.scores:
            if isinstance(self.scores, str):
                try:
                    scores_data = json.loads(self.scores)
                except:
                    scores_data = []
            else:
                scores_data = self.scores

        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'exercise_type': self.exercise_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_count': self.total_count,
            'correct_count': self.correct_count,
            'status': self.status,
            'scores': scores_data
        }


class UserAchievement(db.Model):
    """用户成就表"""
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('users.user_id'), nullable=False, index=True)
    achievement_id = db.Column(db.String(100), nullable=False, index=True)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),
    )
    
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),)
    
    def to_dict(self):
        return {
            'achievement_id': self.achievement_id,
            'unlocked_at': self.unlocked_at.isoformat() if self.unlocked_at else None
        }


class Checkin(db.Model):
    """打卡记录表"""
    __tablename__ = 'checkins'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('users.user_id'), nullable=False, index=True)
    checkin_date = db.Column(db.Date, nullable=False, index=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'checkin_date', name='unique_user_checkin_date'),
        db.Index('idx_user_checkin_date', 'user_id', 'checkin_date'),
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'checkin_date', name='unique_user_checkin_date'),)
    
    @staticmethod
    def get_user_checkin_stats(user_id):
        """获取用户打卡统计"""
        checkins = Checkin.query.filter_by(user_id=user_id).order_by(Checkin.checkin_date.desc()).all()
        
        if not checkins:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'last_checkin_date': None,
                'checkin_history': [],
                'total_days': 0
            }
        
        checkin_dates = [c.checkin_date for c in checkins]
        checkin_dates.sort(reverse=True)
        
        # 计算连续天数
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        last_date = None
        
        for i, date in enumerate(checkin_dates):
            if i == 0:
                current_streak = 1
                temp_streak = 1
                last_date = date
            else:
                days_diff = (last_date - date).days
                if days_diff == 1:
                    current_streak += 1
                    temp_streak += 1
                elif days_diff > 1:
                    longest_streak = max(longest_streak, temp_streak)
                    if i == 1:  # 如果第一次就断了，当前连续为1
                        current_streak = 1
                    temp_streak = 1
                last_date = date
        
        longest_streak = max(longest_streak, temp_streak)
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'last_checkin_date': checkin_dates[0].isoformat() if checkin_dates else None,
            'checkin_history': [d.isoformat() for d in checkin_dates],
            'total_days': len(checkin_dates)
        }


class ChallengeCompletion(db.Model):
    """挑战完成记录表"""
    __tablename__ = 'challenge_completions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('users.user_id'), nullable=False, index=True)
    challenge_id = db.Column(db.String(100), nullable=False, index=True)
    completion_date = db.Column(db.Date, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'challenge_id', 'completion_date', name='unique_user_challenge_date'),
        db.Index('idx_user_challenge_date', 'user_id', 'challenge_id', 'completion_date'),
    )


def init_db(app):
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        print("✅ 数据库初始化完成")


def migrate_from_json(app):
    """从JSON文件迁移数据到数据库"""
    import json
    import os
    from datetime import datetime
    
    with app.app_context():
        # 检查是否已经迁移过
        if User.query.first():
            print("⚠️  数据库中已有数据，跳过迁移")
            return
        
        print("🔄 开始从JSON文件迁移数据...")
        
        # 迁移用户数据
        users_file = 'users.json'
        if os.path.exists(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
                for user_id, user_data in users_data.items():
                    user = User(
                        user_id=user_id,
                        username=user_data.get('username', user_id),
                        password_hash=user_data.get('password_hash', ''),
                        email=user_data.get('email', ''),
                        nickname=user_data.get('nickname', ''),
                        avatar=user_data.get('avatar', ''),
                        created_at=datetime.fromisoformat(user_data.get('created_at', datetime.now().isoformat()))
                    )
                    db.session.add(user)
                    
                    # 添加用户资料
                    if 'profile' in user_data:
                        profile_data = user_data['profile']
                        profile = UserProfile(
                            user_id=user_id,
                            height=profile_data.get('height'),
                            weight=profile_data.get('weight'),
                            age=profile_data.get('age'),
                            gender=profile_data.get('gender')
                        )
                        db.session.add(profile)
            
            print(f"✅ 迁移了 {len(users_data)} 个用户")
        
        # 迁移Token数据
        tokens_file = 'tokens.json'
        if os.path.exists(tokens_file):
            with open(tokens_file, 'r', encoding='utf-8') as f:
                tokens_data = json.load(f)
                for token_str, token_data in tokens_data.items():
                    token = Token(
                        token=token_str,
                        user_id=token_data.get('user_id'),
                        expire_time=datetime.fromisoformat(token_data.get('expire_time'))
                    )
                    db.session.add(token)
            
            print(f"✅ 迁移了 {len(tokens_data)} 个token")
        
        # 迁移计划数据
        plans_file = 'plans.json'
        if os.path.exists(plans_file):
            with open(plans_file, 'r', encoding='utf-8') as f:
                plans_data = json.load(f)
                for user_id, plan_data in plans_data.items():
                    plan = Plan(
                        user_id=user_id,
                        daily_goals=json.dumps(plan_data.get('daily_goals', {})),
                        weekly_goals=json.dumps(plan_data.get('weekly_goals', {})),
                        created_at=datetime.fromisoformat(plan_data.get('created_at', datetime.now().isoformat())),
                        updated_at=datetime.fromisoformat(plan_data.get('updated_at', datetime.now().isoformat()))
                    )
                    db.session.add(plan)
            
            print(f"✅ 迁移了 {len(plans_data)} 个计划")
        
        # 迁移会话数据
        sessions_file = 'sessions.json'
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                for session_id, session_data in sessions_data.items():
                    session = Session(
                        session_id=session_id,
                        user_id=session_data.get('user_id'),
                        exercise_type=session_data.get('exercise_type', 'unknown'),
                        start_time=datetime.fromisoformat(session_data.get('start_time')),
                        end_time=datetime.fromisoformat(session_data.get('end_time')) if session_data.get('end_time') else None,
                        total_count=session_data.get('total_count', 0),
                        correct_count=session_data.get('correct_count', 0),
                        status=session_data.get('status', 'completed'),
                        scores=json.dumps(session_data.get('scores', []))
                    )
                    db.session.add(session)
            
            print(f"✅ 迁移了 {len(sessions_data)} 个会话")
        
        # 迁移成就数据
        achievements_file = 'achievements.json'
        if os.path.exists(achievements_file):
            with open(achievements_file, 'r', encoding='utf-8') as f:
                achievements_data = json.load(f)
                for user_id, user_achievements in achievements_data.items():
                    for achievement_id, achievement_data in user_achievements.items():
                        achievement = UserAchievement(
                            user_id=user_id,
                            achievement_id=achievement_id,
                            unlocked_at=datetime.fromisoformat(achievement_data.get('unlocked_at', datetime.now().isoformat()))
                        )
                        db.session.add(achievement)
            
            print(f"✅ 迁移了成就数据")
        
        # 迁移打卡数据
        checkins_file = 'checkins.json'
        if os.path.exists(checkins_file):
            with open(checkins_file, 'r', encoding='utf-8') as f:
                checkins_data = json.load(f)
                for user_id, checkin_data in checkins_data.items():
                    checkin_history = checkin_data.get('checkin_history', [])
                    for date_str in checkin_history:
                        try:
                            checkin = Checkin(
                                user_id=user_id,
                                checkin_date=datetime.fromisoformat(date_str).date()
                            )
                            db.session.add(checkin)
                        except:
                            pass
            
            print(f"✅ 迁移了打卡数据")
        
        # 迁移挑战完成数据
        challenges_file = 'challenges.json'
        if os.path.exists(challenges_file):
            with open(challenges_file, 'r', encoding='utf-8') as f:
                challenges_data = json.load(f)
                for user_id, user_challenges in challenges_data.items():
                    for date_str, challenge_list in user_challenges.items():
                        for challenge_data in challenge_list:
                            try:
                                completion = ChallengeCompletion(
                                    user_id=user_id,
                                    challenge_id=challenge_data.get('challenge_id'),
                                    completion_date=datetime.fromisoformat(date_str).date()
                                )
                                db.session.add(completion)
                            except:
                                pass
            
            print(f"✅ 迁移了挑战完成数据")
        
        db.session.commit()
        print("🎉 数据迁移完成！")

