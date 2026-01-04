"""
工具函数和辅助类
提供输入验证、错误处理等工具
"""
import re
import logging
from functools import wraps
from flask import jsonify
from database import db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_email(email):
    """验证邮箱格式"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username):
    """验证用户名格式"""
    if not username:
        return False
    # 用户名：3-20个字符，只能包含字母、数字、下划线
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))


def validate_password(password):
    """验证密码强度"""
    if not password:
        return False
    # 密码：至少6位
    if len(password) < 6:
        return False
    return True


def validate_height(height):
    """验证身高（cm）"""
    try:
        h = float(height)
        return 50 <= h <= 250  # 合理范围：50-250cm
    except (ValueError, TypeError):
        return False


def validate_weight(weight):
    """验证体重（kg）"""
    try:
        w = float(weight)
        return 20 <= w <= 300  # 合理范围：20-300kg
    except (ValueError, TypeError):
        return False


def validate_age(age):
    """验证年龄"""
    try:
        a = int(age)
        return 1 <= a <= 150  # 合理范围：1-150岁
    except (ValueError, TypeError):
        return False


def db_transaction(f):
    """数据库事务装饰器，自动处理回滚"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            logger.error(f"数据库操作失败: {str(e)}", exc_info=True)
            raise
    return decorated_function


def handle_db_error(f):
    """数据库错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"数据库错误: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({
                "error": "数据库操作失败",
                "message": str(e)
            }), 500
    return decorated_function


def sanitize_input(text, max_length=None):
    """清理用户输入"""
    if not text:
        return ""
    # 移除危险字符
    text = text.strip()
    # 限制长度
    if max_length and len(text) > max_length:
        text = text[:max_length]
    return text


def validate_exercise_type(exercise_type):
    """验证运动类型"""
    valid_types = ['squat', 'pushup', 'plank', 'jumping_jack']
    return exercise_type in valid_types


def validate_session_data(data):
    """验证会话数据"""
    required_fields = ['session_id', 'user_id', 'exercise_type', 'start_time']
    for field in required_fields:
        if field not in data:
            return False, f"缺少必需字段: {field}"
    
    if not validate_exercise_type(data['exercise_type']):
        return False, "无效的运动类型"
    
    return True, None

