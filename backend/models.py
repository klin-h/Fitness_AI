from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200))
    email = db.Column(db.String(120))
    nickname = db.Column(db.String(100))
    avatar = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 存储身高、体重等个人信息
    profile = db.Column(JSON, default={})

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "profile": self.profile
        }

class Plan(db.Model):
    __tablename__ = 'plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), unique=True)
    daily_goals = db.Column(JSON, default={})
    weekly_goals = db.Column(JSON, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "daily_goals": self.daily_goals,
            "weekly_goals": self.weekly_goals,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Session(db.Model):
    __tablename__ = 'sessions'
    
    session_id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'))
    exercise_type = db.Column(db.String(50))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    total_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20))
    # 存储详细的评分数组
    scores = db.Column(JSON, default=[])

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "exercise_type": self.exercise_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_count": self.total_count,
            "correct_count": self.correct_count,
            "status": self.status,
            "scores": self.scores
        }

class Token(db.Model):
    __tablename__ = 'tokens'
    
    token = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'))
    expire_time = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "token": self.token,
            "user_id": self.user_id,
            "expire_time": self.expire_time.isoformat() if self.expire_time else None
        }
