from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime, timedelta, date
import os
import hashlib
import secrets
from functools import wraps
import math
import requests
from dotenv import load_dotenv
import logging
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
try:
    from zhipuai import ZhipuAI
except ImportError:
    ZhipuAI = None
    print("[Warning] zhipuai library not found. Please install it via 'pip install zhipuai'")

from utils import (
    validate_email, validate_username, validate_password,
    validate_height, validate_weight, validate_age,
    sanitize_input, db_transaction, handle_db_error,
    validate_exercise_type
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
# 强制加载当前文件所在目录下的 .env 文件
from pathlib import Path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# 调试：打印API Key状态（仅打印前几位，保护隐私）
api_key = os.getenv('ZHIPU_API_KEY')
if api_key:
    masked_key = api_key[:5] + '*' * (len(api_key) - 5) if len(api_key) > 5 else '*****'
    print(f"[Config] ZHIPU_API_KEY loaded: {masked_key}")
else:
    print("[Config] ZHIPU_API_KEY not found in environment variables")

app = Flask(__name__)
# 配置 CORS，允许所有来源和所有方法（开发环境）
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 数据库配置
# 必须使用PostgreSQL，不支持SQLite
# PostgreSQL连接字符串格式: postgresql://用户名:密码@主机:端口/数据库名
# 示例: postgresql://postgres:password@localhost:5432/fitnessai
database_url = os.getenv('DATABASE_URL')

if not database_url:
    raise ValueError(
        "❌ DATABASE_URL 环境变量未设置！\n"
        "请设置 PostgreSQL 数据库连接字符串。\n"
        "格式: postgresql://用户名:密码@主机:端口/数据库名\n"
        "示例: postgresql://postgres:password@localhost:5432/fitnessai\n"
        "请在 .env 文件中设置 DATABASE_URL，或在环境变量中设置。"
    )

# 检查是否使用了 SQLite（不允许）
if 'sqlite' in database_url.lower():
    raise ValueError(
        "❌ 不支持 SQLite！必须使用 PostgreSQL。\n"
        "请设置 PostgreSQL 数据库连接字符串。\n"
        "格式: postgresql://用户名:密码@主机:端口/数据库名\n"
        "示例: postgresql://postgres:password@localhost:5432/fitnessai"
    )

# 验证是否为 PostgreSQL 连接字符串
if 'postgresql' not in database_url.lower() and 'postgres' not in database_url.lower():
    raise ValueError(
        f"❌ 无效的数据库连接字符串: {database_url}\n"
        "必须使用 PostgreSQL 数据库。\n"
        "格式: postgresql://用户名:密码@主机:端口/数据库名"
    )

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PostgreSQL 连接池配置
# 对于云数据库（如 Neon），需要特殊配置
engine_options = {
    'pool_pre_ping': True,  # 自动重连
    'pool_recycle': 300,    # 连接回收时间（5分钟）
    'pool_size': 5,         # 连接池大小（云数据库建议较小）
    'max_overflow': 10,     # 最大溢出连接数
}

# 如果是云数据库（Neon等），可能需要 SSL 配置
if 'neon.tech' in database_url.lower() or 'pooler' in database_url.lower():
    # Neon 数据库通常需要 SSL，连接字符串中应该已经包含
    # 如果连接失败，可能需要添加 ?sslmode=require
    if '?sslmode=' not in database_url and '?ssl=' not in database_url:
        logger.info("💡 检测到 Neon 数据库，建议在连接字符串中添加 SSL 参数")
        logger.info("💡 如果连接失败，尝试添加 ?sslmode=require 到连接字符串末尾")

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options

# 初始化数据库
from database import db, init_db, Session, User, UserProfile, Plan, UserAchievement, Checkin, ChallengeCompletion, Token
db.init_app(app)

# 导入数据库适配层
from db_adapter import (
    load_users, get_user_by_id, get_user_by_username, create_user, update_user,
    load_tokens, save_token, delete_token, get_token,
    load_plans, get_user_plan, save_user_plan,
    load_sessions, get_session, create_session, update_session, get_user_sessions,
    load_achievements, get_user_achievements, unlock_achievement,
    get_user_checkin_stats, add_checkin, get_checkin_calendar,
    get_challenge_completions, complete_challenge
)

# 数据存储（已迁移到数据库）
exercise_data = {}

# 数据库初始化（应用启动时）
# 使用延迟初始化，避免启动时因数据库连接问题阻塞
def init_database():
    """延迟初始化数据库，避免启动时阻塞"""
    import time
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                # 确保数据库表存在
                db.create_all()
                print("✅ 数据库连接成功")
                
                # 检查是否需要迁移JSON数据（仅在首次运行时）
                from database import User
                user_count = User.query.count()
                if user_count == 0:
                    print("📥 检测到空数据库，尝试迁移JSON数据...")
                    try:
                        from database import migrate_from_json
                        migrate_from_json(app)
                    except Exception as e:
                        print(f"⚠️  数据迁移失败（可能是首次运行）: {e}")
                else:
                    print(f"✅ 数据库已包含 {user_count} 个用户")
                return  # 成功则返回
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  数据库连接失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                print(f"💡 {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"❌ 数据库连接失败（已重试 {max_retries} 次）: {e}")
                print("💡 请确保PostgreSQL已安装并运行，且数据库已创建")
                if 'neon.tech' in database_url.lower():
                    print("💡 如果是 Neon 数据库，请检查:")
                    print("   1. 网络连接是否正常")
                    print("   2. 连接字符串是否正确")
                    print("   3. 数据库是否已创建")
                else:
                    print("💡 可以使用以下命令创建数据库:")
                    print("   createdb -U postgres fitnessai")
                    print("💡 或使用 psql:")
                    print("   psql -U postgres")
                    print("   CREATE DATABASE fitnessai;")
                print("💡 检查 .env 文件中的 DATABASE_URL 配置是否正确")
                masked_url = database_url[:50] + "..." if len(database_url) > 50 else database_url
                print(f"💡 当前 DATABASE_URL: {masked_url}")
                # 不抛出异常，允许应用启动（数据库连接会在实际使用时重试）

# 在后台线程中初始化数据库，避免阻塞启动
import threading
db_init_thread = threading.Thread(target=init_database, daemon=True)
db_init_thread.start()

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    """生成token"""
    return secrets.token_urlsafe(32)

def verify_token(token):
    """验证token"""
    token_obj = get_token(token)
    if token_obj and datetime.now() < token_obj.expire_time:
        return token_obj.user_id
    return None

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # OPTIONS 预检请求不需要认证
        if request.method == 'OPTIONS':
            response = jsonify({})
            # 显式添加CORS头，防止某些情况下CORS中间件未生效
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response, 200
        
        token = request.headers.get('Authorization')
        if not token:
            print("❌ [Auth] 未提供认证token")
            return jsonify({"error": "未提供认证token"}), 401
        
        # 移除 "Bearer " 前缀（如果存在）
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            print(f"❌ [Auth] 无效或过期的token: {token[:10]}...")
            return jsonify({"error": "无效或过期的token"}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """首页接口"""
    return jsonify({
        "message": "FitnessAI Backend API",
        "version": "1.0.0",
        "status": "running"
    })

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """
    获取支持的运动类型列表
    
    Returns:
        JSON: 运动类型列表，包含每种运动的详细信息
    """
    exercises = [
        {
            "id": "squat",
            "name": "深蹲",
            "description": "训练大腿和臀部肌肉的经典动作",
            "difficulty": "easy",
            "target_muscles": ["大腿", "臀部", "核心"],
            "instructions": [
                "双脚与肩同宽站立",
                "膝盖弯曲，臀部向后坐",
                "保持背部挺直",
                "大腿与地面平行时停止",
                "缓慢回到起始位置"
            ]
        },
        {
            "id": "pushup",
            "name": "俯卧撑",
            "description": "上肢力量训练的基础动作",
            "difficulty": "medium",
            "target_muscles": ["胸部", "肩部", "三头肌"],
            "instructions": [
                "俯卧撑起始位置",
                "手掌与肩同宽",
                "身体保持一条直线",
                "胸部贴近地面",
                "推起回到起始位置"
            ]
        }
    ]
    return jsonify(exercises)

@app.route('/api/session/start', methods=['POST'])
def start_session():
    """
    开始新的锻炼会话
    
    Request Body:
        - exercise_type: 运动类型
        - user_id: 用户ID（可选）
    
    Returns:
        JSON: 会话ID和初始数据
    """
    try:
        data = request.get_json() or {}
        exercise_type = data.get('exercise_type', 'squat')
        user_id = data.get('user_id', 'anonymous')
        
        # 验证运动类型
        if not validate_exercise_type(exercise_type):
            return jsonify({"error": "无效的运动类型"}), 400
        
        session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "exercise_type": exercise_type,
            "start_time": datetime.now().isoformat(),
            "total_count": 0,
            "correct_count": 0,
            "status": "active",
            "scores": []
        }
        
        logger.info(f"准备创建会话: {session_id}, user_id={user_id}, exercise_type={exercise_type}")
        
        # create_session 已经使用了 @db_transaction 装饰器，会自动处理事务
        try:
            session = create_session(session_data)
            logger.info(f"✅ 创建运动会话成功: {session_id} - {user_id} - {exercise_type}")
            
            return jsonify({
                "session_id": session_id,
                "message": "Session started successfully"
            })
        except ValueError as e:
            logger.error(f"❌ 创建会话失败（验证错误）: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 400
        except IntegrityError as e:
            logger.error(f"❌ 创建会话失败（数据冲突）: {str(e)}", exc_info=True)
            return jsonify({"error": "会话ID已存在，请稍后重试"}), 409
        except Exception as e:
            logger.error(f"❌ 创建会话失败: {str(e)}", exc_info=True)
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"详细错误堆栈:\n{error_details}")
            return jsonify({
                "error": "创建会话失败",
                "message": str(e),
                "details": error_details if app.debug else None
            }), 500
    except Exception as e:
        logger.error(f"❌ 处理会话创建请求失败: {str(e)}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"详细错误堆栈:\n{error_details}")
        return jsonify({
            "error": "服务器错误",
            "message": str(e),
            "details": error_details if app.debug else None
        }), 500

@app.route('/api/session/<session_id>/data', methods=['POST'])
def submit_exercise_data(session_id):
    """
    提交运动数据
    
    Path Parameters:
        - session_id: 会话ID
    
    Request Body:
        - pose_data: 姿态关键点数据
        - is_correct: 动作是否正确
        - score: 动作得分
        - feedback: 反馈信息
    
    Returns:
        JSON: 处理结果
    """
    try:
        # 获取当前会话对象
        session_obj = Session.query.get(session_id)
        if not session_obj:
            logger.warning(f"会话不存在: {session_id}")
            return jsonify({"error": "Session not found"}), 404
        
        data = request.get_json() or {}
        is_correct = bool(data.get('is_correct', False))
        
        # 安全地转换 score，处理字符串和 None 的情况
        try:
            score_value = data.get('score', 0)
            if isinstance(score_value, str):
                score = max(0, min(100, int(float(score_value))))
            elif score_value is None:
                score = 0
            else:
                score = max(0, min(100, int(score_value)))
        except (ValueError, TypeError) as e:
            logger.warning(f"分数转换失败: {score_value}, 使用默认值 0, 错误: {e}")
            score = 0
        
        feedback = sanitize_input(data.get('feedback', ''), max_length=500)
        
        # 对于平板支撑，不增加计数，而是使用时长
        # 对于其他运动，增加计数
        if session_obj.exercise_type != 'plank':
            session_obj.total_count += 1
            if is_correct:
                session_obj.correct_count += 1
            # 确保correct_count不超过total_count（防止数据异常）
            if session_obj.correct_count > session_obj.total_count:
                session_obj.correct_count = session_obj.total_count
        # 平板支撑的时长会在 end_session 时通过 end_time - start_time 计算
    
        # 更新分数记录 - 安全地处理 None 和空字符串
        scores = []
        if session_obj.scores:
            if isinstance(session_obj.scores, str):
                try:
                    if session_obj.scores.strip():
                        scores = json.loads(session_obj.scores)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"解析分数记录失败: {e}, 使用空列表")
                    scores = []
            elif isinstance(session_obj.scores, (list, dict)):
                scores = session_obj.scores
        
        scores.append({
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "is_correct": is_correct,
            "feedback": feedback
        })
        session_obj.scores = json.dumps(scores)
        
        try:
            db.session.commit()
            
            # 对于平板支撑，计算当前时长
            is_plank = session_obj.exercise_type == 'plank'
            if is_plank:
                duration_seconds = int((datetime.now() - session_obj.start_time).total_seconds())
                logger.info(f"✅ 提交运动数据成功: {session_id}, duration={duration_seconds}秒, score={score}")
                return jsonify({
                    "message": "Data submitted successfully",
                    "session_stats": {
                        "duration": duration_seconds,  # 秒
                        "duration_minutes": round(duration_seconds / 60, 1),  # 分钟
                        "score": score,
                        "is_correct": is_correct
                    }
                })
            else:
                logger.info(f"✅ 提交运动数据成功: {session_id}, count={session_obj.total_count}, score={score}")
                # 确保准确率不超过100%
                accuracy = round(min(100, (session_obj.correct_count / session_obj.total_count * 100) if session_obj.total_count > 0 else 0), 2)
                return jsonify({
                    "message": "Data submitted successfully",
                    "session_stats": {
                        "total_count": session_obj.total_count,
                        "correct_count": session_obj.correct_count,
                        "accuracy": accuracy
                    }
                })
        except Exception as e:
            logger.error(f"❌ 提交运动数据失败（数据库错误）: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({
                "error": "提交数据失败",
                "message": str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"❌ 处理提交运动数据请求失败: {str(e)}", exc_info=True)
        db.session.rollback()
        import traceback
        return jsonify({
            "error": "服务器错误",
            "message": str(e),
            "details": traceback.format_exc() if app.debug else None
        }), 500

from datetime import datetime, timedelta
from sqlalchemy import func

@app.route('/api/user/stats/weekly', methods=['GET'])
@require_auth
def get_weekly_stats():
    """获取用户本周运动统计数据"""
    user_id = request.user_id
    
    # 计算本周起始日期（周一）
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # 查询本周的所有会话
    sessions = Session.query.filter(
        Session.user_id == user_id,
        Session.start_time >= datetime.combine(start_of_week, datetime.min.time()),
        Session.start_time <= datetime.combine(end_of_week, datetime.max.time())
    ).all()
    
    # 初始化每日数据
    daily_stats = {
        (start_of_week + timedelta(days=i)).strftime('%Y-%m-%d'): {"count": 0, "duration": 0}
        for i in range(7)
    }
    
    # 填充数据
    for session in sessions:
        date_str = session.start_time.strftime('%Y-%m-%d')
        if date_str in daily_stats:
            daily_stats[date_str]["count"] += session.total_count
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60  # 分钟
                daily_stats[date_str]["duration"] += duration
                
    # 格式化返回数据
    result = [
        {
            "date": date,
            "day": (datetime.strptime(date, '%Y-%m-%d')).strftime('%a'), # 周几
            "count": stats["count"],
            "duration": round(stats["duration"], 1)
        }
        for date, stats in daily_stats.items()
    ]
    
    return jsonify(result)

@app.route('/api/user/stats/exercise-distribution', methods=['GET'])
@require_auth
def get_exercise_distribution():
    """获取用户运动类型分布"""
    user_id = request.user_id
    
    # 聚合查询各种运动类型的总次数
    stats = db.session.query(
        Session.exercise_type,
        func.sum(Session.total_count).label('total_count')
    ).filter(
        Session.user_id == user_id
    ).group_by(Session.exercise_type).all()
    
    result = [
        {"name": stat.exercise_type, "value": stat.total_count or 0}
        for stat in stats
    ]
    
    return jsonify(result)

@app.route('/api/session/<session_id>/end', methods=['POST'])
def end_session(session_id):
    """
    结束锻炼会话
    
    Path Parameters:
        - session_id: 会话ID
    
    Returns:
        JSON: 会话总结数据
    """
    try:
        session_obj = Session.query.get(session_id)
        if not session_obj:
            logger.warning(f"会话不存在: {session_id}")
            return jsonify({"error": "Session not found"}), 404
        
        # 更新会话状态
        session_obj.end_time = datetime.now()
        session_obj.status = 'completed'
        
        # 计算时长
        # 优先使用前端传入的实际运动时长（扣除了暂停时间），否则使用时间戳差值
        data = request.get_json() or {}
        actual_duration_seconds = data.get('duration')
        
        if actual_duration_seconds is not None:
             duration_seconds = float(actual_duration_seconds)
        else:
             duration_seconds = (session_obj.end_time - session_obj.start_time).total_seconds()

        duration_minutes = int(duration_seconds / 60)
        
        # 对于平板支撑，使用时长而不是次数
        is_plank = session_obj.exercise_type == 'plank'
        
        if is_plank:
            # 平板支撑：使用时长（秒）作为主要指标
            total_count = int(duration_seconds)  # 秒数
            correct_count = int(duration_seconds)  # 平板支撑没有"正确次数"的概念，使用总时长
            accuracy = 100  # 平板支撑的准确率基于姿势质量，这里简化处理
        else:
            # 其他运动：使用次数
            total_count = session_obj.total_count or 0
            correct_count = session_obj.correct_count or 0
            # 确保准确率不超过100%，并且correct_count不超过total_count
            correct_count = min(correct_count, total_count)  # 防止correct_count超过total_count
            accuracy = min(100, (correct_count / total_count * 100) if total_count > 0 else 0)
        
        # 安全地解析分数记录
        scores = []
        if session_obj.scores:
            if isinstance(session_obj.scores, str):
                try:
                    if session_obj.scores.strip():
                        scores = json.loads(session_obj.scores)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"解析分数记录失败: {e}, 使用空列表")
                    scores = []
            elif isinstance(session_obj.scores, (list, dict)):
                scores = session_obj.scores
        
        avg_score = sum([s.get('score', 0) for s in scores]) / len(scores) if scores else 0
        
        # 计算卡路里消耗 (估算值)
        # METs (Metabolic Equivalent of Task) 参考值:
        # 深蹲 (Squats): 5.0
        # 俯卧撑 (Push-ups): 3.8
        # 开合跳 (Jumping Jacks): 8.0
        # 平板支撑 (Plank): 3.5
        mets_table = {
            "squat": 5.0,
            "pushup": 3.8,
            "jumping_jack": 8.0,
            "plank": 3.5
        }
        met = mets_table.get(session_obj.exercise_type, 4.0)
        
        # 尝试获取用户体重，如果获取不到则使用默认值 70kg
        user_weight = 70.0
        try:
            user = get_user_by_id(session_obj.user_id)
            if user and user.profile and user.profile.weight:
                user_weight = user.profile.weight
        except:
            pass
            
        # 卡路里计算公式: Calories = MET * Weight(kg) * Duration(hours)
        duration_hours = duration_seconds / 3600
        calories_burned = round(met * user_weight * duration_hours, 1)

        # AI 生成训练总结
        # 使用 Zhipu AI 生成简短的改进建议
        # 优化 Prompt 以提高生成速度和质量
        ai_summary = None
        try:
            from app import call_zhipu_ai_api # Import locally to avoid circular dependency
            
            # 构建一个更加精简的 Prompt，减少Token输出，提高速度
            prompt = f"""
            为用户生成30字以内的健身简评。
            项目:{session_obj.exercise_type}
            数据:时长{duration_seconds}s,次数{total_count},准确率{accuracy:.0f}%,均分{avg_score:.1f}
            包含:肯定+1条改进建议。
            """
            
            # 异步或快速调用 AI (为了不阻塞太久，使用快速模型 glm-4-flash)
            # 设置 max_tokens 限制输出长度
            ai_text, error = call_zhipu_ai_api(prompt, max_retries=1)
            if ai_text:
                ai_summary = ai_text.strip()
            else:
                ai_summary = "训练不错！注意保持动作节奏，期待您下次的表现。"
                
        except Exception as e:
            logger.error(f"AI 生成总结失败: {e}")
            ai_summary = "训练完成！继续保持，注意休息。"

        # 保存总结数据到数据库
        session_obj.calories = calories_burned
        session_obj.ai_comment = ai_summary

        try:
            db.session.commit()
            if is_plank:
                logger.info(f"✅ 会话结束: {session_id} - 时长: {duration_seconds:.1f}秒")
            else:
                logger.info(f"✅ 会话结束: {session_id} - 总次数: {total_count}, 准确率: {accuracy:.2f}%")
            
            return jsonify({
                "session_id": session_id,
                "summary": {
                    "total_count": total_count if not is_plank else int(duration_seconds),  # 平板支撑返回秒数
                    "correct_count": correct_count if not is_plank else int(duration_seconds),
                    "accuracy": round(accuracy, 2) if accuracy is not None else 0,
                    "average_score": round(avg_score, 2) if avg_score is not None else 0,
                    "duration": round(duration_seconds / 60, 1) if duration_seconds is not None else 0,  # 分钟，保留一位小数
                    "duration_seconds": int(duration_seconds) if is_plank else None,  # 平板支撑返回秒数
                    "exercise_type": session_obj.exercise_type or '',
                    "calories": calories_burned if calories_burned is not None else 0,
                    "ai_comment": ai_summary or "训练完成！继续保持，注意休息。"
                },
                "message": "Session ended successfully"
            })
        except Exception as e:
            logger.error(f"❌ 结束会话失败（数据库错误）: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({
                "error": "结束会话失败",
                "message": str(e)
            }), 500
    except Exception as e:
        logger.error(f"❌ 处理结束会话请求失败: {str(e)}", exc_info=True)
        db.session.rollback()
        import traceback
        return jsonify({
            "error": "服务器错误",
            "message": str(e),
            "details": traceback.format_exc() if app.debug else None
        }), 500

@app.route('/api/user/<user_id>/history', methods=['GET'])
@handle_db_error
def get_user_history(user_id):
    """
    获取用户历史记录
    
    Path Parameters:
        - user_id: 用户ID
    
    Query Parameters:
        - limit: 返回记录数量限制（默认10）
        - exercise_type: 过滤特定运动类型
    
    Returns:
        JSON: 用户历史会话列表
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        exercise_type = request.args.get('exercise_type')
        
        # 限制查询数量，防止过大
        limit = min(max(1, limit), 100)  # 限制在1-100之间
        
        sessions = get_user_sessions(user_id, limit=limit, exercise_type=exercise_type)
        
        return jsonify({
            "user_id": user_id,
            "sessions": sessions,
            "total_sessions": len(sessions)
        })
    except Exception as e:
        logger.error(f"获取用户历史失败: {str(e)}", exc_info=True)
        # 返回具体的错误信息以便调试
        return jsonify({"error": "获取历史记录失败", "details": str(e)}), 500

@app.route('/api/analytics/pose', methods=['POST'])
def analyze_pose():
    """
    分析姿态数据（占位符接口）
    
    Request Body:
        - pose_landmarks: MediaPipe姿态关键点数据
        - exercise_type: 运动类型
    
    Returns:
        JSON: 分析结果
    
    注意：这个接口需要实现具体的姿态分析算法
    """
    data = request.get_json()
    pose_landmarks = data.get('pose_landmarks')
    exercise_type = data.get('exercise_type', 'squat')
    
    # TODO: 实现具体的姿态分析逻辑
    # 这里应该包含：
    # 1. 关键点角度计算
    # 2. 动作标准性判断
    # 3. 错误检测和反馈生成
    # 4. 计数逻辑
    
    # 模拟分析结果
    analysis_result = {
        "is_correct": True,  # 动作是否正确
        "score": 85,  # 动作得分 (0-100)
        "feedback": "动作标准，继续保持！",
        "suggestions": [],  # 改进建议
        "key_points": {  # 关键点分析
            "knee_angle": 90,
            "hip_angle": 85,
            "back_straight": True
        }
    }
    
    return jsonify(analysis_result)

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """
    获取个性化推荐
    
    Query Parameters:
        - user_id: 用户ID
        - current_exercise: 当前运动类型
    
    Returns:
        JSON: 推荐的运动和训练计划
    """
    user_id = request.args.get('user_id', 'anonymous')
    current_exercise = request.args.get('current_exercise', 'squat')
    
    # TODO: 基于用户历史数据生成个性化推荐
    
    recommendations = {
        "next_exercises": [
            {"id": "pushup", "name": "俯卧撑", "reason": "增强上肢力量"},
            {"id": "plank", "name": "平板支撑", "reason": "强化核心稳定"}
        ],
        "difficulty_adjustment": "maintain",  # increase, decrease, maintain
        "suggested_sets": 3,
        "suggested_reps": 15,
        "rest_time": 60  # 秒
    }
    
    return jsonify(recommendations)

# ==================== 用户认证相关API ====================

@app.route('/api/auth/register', methods=['POST'])
@handle_db_error
def register():
    """
    用户注册
    
    Request Body:
        - username: 用户名
        - password: 密码
        - email: 邮箱（可选）
        - nickname: 昵称（可选）
    
    Returns:
        JSON: 注册结果和token
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        username = sanitize_input(data.get('username'), max_length=20)
        password = data.get('password')
        email = sanitize_input(data.get('email', ''), max_length=255)
        nickname = sanitize_input(data.get('nickname', username), max_length=100)
        
        # 输入验证
        if not username:
            return jsonify({"error": "用户名不能为空"}), 400
        
        if not validate_username(username):
            return jsonify({"error": "用户名格式不正确（3-20个字符，只能包含字母、数字、下划线）"}), 400
        
        if not password:
            return jsonify({"error": "密码不能为空"}), 400
        
        if not validate_password(password):
            return jsonify({"error": "密码长度至少6位"}), 400
        
        if email and not validate_email(email):
            return jsonify({"error": "邮箱格式不正确"}), 400
    
        # 检查用户名是否已存在
        existing_user = get_user_by_username(username)
        if existing_user:
            return jsonify({"error": "用户名已存在"}), 400
        
        # 创建新用户
        user_id = username
        try:
            user = create_user({
                "user_id": user_id,
                "username": username,
                "password_hash": hash_password(password),
                "email": email,
                "nickname": nickname or username,
                "avatar": ""
            })
            
            # 创建用户资料
            from database import UserProfile
            profile = UserProfile(
                user_id=user_id,
                height=0,
                weight=0,
                age=0,
                gender=""
            )
            db.session.add(profile)
            db.session.commit()
            
            # 生成token
            token = generate_token()
            expire_time = datetime.now() + timedelta(days=1)  # 24小时后过期
            save_token(token, user_id, expire_time)
            
            logger.info(f"新用户注册成功: {username}")
            
            return jsonify({
                "message": "注册成功",
                "token": token,
                "user": {
                    "user_id": user_id,
                    "username": username,
                    "nickname": nickname,
                    "email": email
                }
            }), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"注册失败: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({"error": "注册失败，请稍后重试"}), 500
    except Exception as e:
        logger.error(f"注册请求处理失败: {str(e)}", exc_info=True)
        return jsonify({"error": "请求处理失败"}), 500

@app.route('/api/auth/login', methods=['POST'])
@handle_db_error
def login():
    """
    用户登录
    
    Request Body:
        - username: 用户名
        - password: 密码
    
    Returns:
        JSON: 登录结果和token
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        username = sanitize_input(data.get('username'), max_length=20)
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "用户名和密码不能为空"}), 400
        
        # 从数据库查找用户
        user = get_user_by_username(username)
        if not user:
            logger.warning(f"登录失败: 用户不存在 - {username}")
            return jsonify({"error": "用户名或密码错误"}), 401
        
        password_hash = hash_password(password)
        if user.password_hash != password_hash:
            logger.warning(f"登录失败: 密码错误 - {username}")
            return jsonify({"error": "用户名或密码错误"}), 401
        
        # 生成token
        token = generate_token()
        expire_time = datetime.now() + timedelta(days=1)  # 24小时后过期
        try:
            save_token(token, user.user_id, expire_time)
        except Exception as e:
            logger.error(f"保存token失败: {str(e)}")
            return jsonify({"error": "登录失败，请稍后重试"}), 500
        
        logger.info(f"用户登录成功: {username}")
        
        return jsonify({
            "message": "登录成功",
            "token": token,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email
            }
        })
    except Exception as e:
        logger.error(f"登录请求处理失败: {str(e)}", exc_info=True)
        return jsonify({"error": "请求处理失败"}), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
@handle_db_error
def get_current_user():
    """
    获取当前用户信息（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Returns:
        JSON: 用户信息
    """
    try:
        user_id = request.user_id
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        # to_dict() 方法已经安全处理了 profile 为 None 的情况
        # 不需要强制创建 profile，让用户在更新时自动创建
        user_dict = user.to_dict()
        # 移除敏感信息
        user_dict.pop('password_hash', None)
        
        return jsonify(user_dict)
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {str(e)}", exc_info=True)
        db.session.rollback()
        raise

@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
@handle_db_error
def change_password():
    """
    修改密码（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Request Body:
        - old_password: 旧密码
        - new_password: 新密码
    
    Returns:
        JSON: 修改结果
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({"error": "旧密码和新密码不能为空"}), 400
        
        if not validate_password(new_password):
            return jsonify({"error": "新密码长度至少6位"}), 400
        
        if old_password == new_password:
            return jsonify({"error": "新密码不能与旧密码相同"}), 400
        
        user_id = request.user_id
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        # 验证旧密码
        if user.password_hash != hash_password(old_password):
            logger.warning(f"密码修改失败: 旧密码错误 - {user_id}")
            return jsonify({"error": "旧密码错误"}), 400
        
        # 更新密码
        user.password_hash = hash_password(new_password)
        db.session.commit()
        
        logger.info(f"密码修改成功: {user_id}")
        return jsonify({"message": "密码修改成功"})
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": "修改失败，请稍后重试"}), 500

@app.route('/api/user/profile', methods=['GET'])
@require_auth
@handle_db_error
def get_user_profile():
    """
    获取用户个人资料（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Returns:
        JSON: 用户个人资料
    """
    try:
        user_id = request.user_id
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        # to_dict() 方法已经安全处理了 profile 为 None 的情况
        # 不需要强制创建 profile，让用户在更新时自动创建
        user_dict = user.to_dict()
        return jsonify(user_dict)
    except Exception as e:
        logger.error(f"获取用户个人资料失败: {str(e)}", exc_info=True)
        db.session.rollback()
        raise

@app.route('/api/user/profile', methods=['PUT'])
@require_auth
@handle_db_error
def update_user_profile():
    """
    更新用户个人资料（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Request Body:
        - nickname: 昵称（可选）
        - email: 邮箱（可选）
        - avatar: 头像URL（可选）
        - profile: 个人资料对象（可选）
            - height: 身高（可选）
            - weight: 体重（可选）
            - age: 年龄（可选）
            - gender: 性别（可选）
    
    Returns:
        JSON: 更新后的用户信息
    """
    data = request.get_json()
    user_id = request.user_id
    user = get_user_by_id(user_id)
    
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    # 更新允许修改的字段
    if 'nickname' in data:
        user.nickname = data['nickname']
    if 'email' in data:
        user.email = data['email']
    if 'avatar' in data:
        user.avatar = data['avatar']
    
    # 更新用户资料
    if 'profile' in data:
        if not user.profile:
            from database import UserProfile
            user.profile = UserProfile(user_id=user_id)
            db.session.add(user.profile)
        
        profile_data = data['profile']
        if 'height' in profile_data:
            user.profile.height = profile_data['height']
        if 'weight' in profile_data:
            user.profile.weight = profile_data['weight']
        if 'age' in profile_data:
            user.profile.age = profile_data['age']
        if 'gender' in profile_data:
            user.profile.gender = profile_data['gender']
        if 'body_fat' in profile_data:
            user.profile.body_fat = profile_data['body_fat']
    
    db.session.commit()
    
    # 返回更新后的用户信息
    updated_user = user.to_dict()
    return jsonify(updated_user)

@app.route('/api/user/plan', methods=['GET'])
@require_auth
@handle_db_error
def get_user_plan_api():
    """
    获取用户的健身计划（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Returns:
        JSON: 用户的健身计划
    """
    try:
        user_id = request.user_id
        plan = get_user_plan(user_id)
        
        if plan:
            return jsonify(plan)
        else:
            # 返回默认计划
            default_plan = {
            "daily_goals": {
                "squat": 20,
                "pushup": 15,
                "plank": 60,  # 秒
                "jumping_jack": 30
            },
            "weekly_goals": {
                "total_sessions": 5,
                "total_duration": 150  # 分钟
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            return jsonify(default_plan)
    except Exception as e:
        logger.error(f"获取用户计划失败: {str(e)}", exc_info=True)
        # 返回默认计划而不是错误
        default_plan = {
            "daily_goals": {
                "squat": 20,
                "pushup": 15,
                "plank": 60,
                "jumping_jack": 30
            },
            "weekly_goals": {
                "total_sessions": 5,
                "total_duration": 150
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return jsonify(default_plan)

@app.route('/api/user/plan', methods=['PUT'])
@require_auth
def update_user_plan():
    """
    更新用户的健身计划（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Request Body:
        - daily_goals: 每日目标（可选）
            - squat: 深蹲次数
            - pushup: 俯卧撑次数
            - plank: 平板支撑秒数
            - jumping_jack: 开合跳次数
        - weekly_goals: 每周目标（可选）
            - total_sessions: 总运动次数
            - total_duration: 总运动时长（分钟）
    
    Returns:
        JSON: 更新后的健身计划
    """
    data = request.get_json()
    user_id = request.user_id
    
    plan = save_user_plan(user_id, data)
    
    return jsonify(plan.to_dict())

def calculate_bmi(height_cm, weight_kg):
    """计算BMI指数"""
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        return None
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)

def get_fitness_level(bmi, age):
    """根据BMI和年龄判断健身水平"""
    if bmi is None:
        return "beginner"
    
    if bmi < 18.5:
        return "underweight"
    elif bmi < 24:
        return "normal"
    elif bmi < 28:
        return "overweight"
    else:
        return "obese"

def call_zhipu_ai_api(prompt, max_retries=2):
    """
    调用智谱AI API（GLM模型），带重试机制
    
    参数:
        prompt: 提示词
        max_retries: 最大重试次数
    
    返回:
        (ai_content, error_code)
        ai_content: AI生成的文本，如果失败则为None
        error_code: 错误代码 (None, 'missing_key', 'timeout', 'connection_error', 'api_error', 'unknown_error')
    """
    api_key = os.getenv('ZHIPU_API_KEY')
    
    # 增强的Key获取逻辑：如果环境变量为空，尝试直接读取文件
    if not api_key or api_key == 'your_zhipu_api_key_here':
        try:
            from pathlib import Path
            env_path = Path(__file__).parent / '.env'
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('ZHIPU_API_KEY='):
                            file_key = line.split('=', 1)[1].strip()
                            if file_key and file_key != 'your_zhipu_api_key_here':
                                api_key = file_key
                                print(f"⚠️ [AI] 从.env文件直接读取到API Key")
                                break
        except Exception as e:
            print(f"❌ [AI] 读取.env文件失败: {e}")

    # 如果仍然没有配置API Key，返回None（将使用规则引擎）
    if not api_key or api_key == 'your_zhipu_api_key_here':
        print("⚠️  [AI] API Key未配置，将使用规则引擎")
        # 打印当前环境变量以便调试
        print(f"🔍 [Debug] Current Env Keys: {[k for k in os.environ.keys() if 'API' in k]}")
        return None, "missing_key"
    
    print(f"🤖 [AI] 正在调用智谱AI官方API (open.bigmodel.cn)...")
    print(f"🔑 [AI] API Key状态: {'已配置' if api_key else '未配置'} (长度: {len(api_key)})")
    print(f"📝 [AI] 提示词长度: {len(prompt)} 字符")
    
    # 使用官方SDK或直接HTTP请求
    # 优先使用 glm-4-flash (免费且速度快)
    model = "glm-4-flash"
    
    last_error = "unknown_error"
    
    # 重试机制
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"🔄 [AI] 第 {attempt + 1} 次尝试...")
            
            if ZhipuAI:
                client = ZhipuAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的健身教练，擅长根据用户的身体指标制定个性化的健身计划。请用中文回答，提供具体、可执行的建议。回答格式要清晰，包含具体的数值。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                ai_content = response.choices[0].message.content
            else:
                # Fallback to requests if SDK not installed
                url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一位专业的健身教练，擅长根据用户的身体指标制定个性化的健身计划。请用中文回答，提供具体、可执行的建议。回答格式要清晰，包含具体的数值。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                resp = requests.post(url, headers=headers, json=data, timeout=(5, 30))
                resp.raise_for_status()
                ai_content = resp.json()['choices'][0]['message']['content']

            print(f"✅ [AI] API调用成功！")
            print(f"📄 [AI] AI返回内容长度: {len(ai_content)} 字符")
            return ai_content, None
                
        except Exception as e:
            print(f"❌ [AI] API调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            last_error = str(e)
            if attempt < max_retries:
                import time
                time.sleep(2)
            else:
                pass
    
    return None, last_error

def parse_ai_response(ai_text, height, weight, age, gender):
    """
    解析AI返回的文本，提取健身计划数据
    
    参数:
        ai_text: AI返回的文本
        height: 身高
        weight: 体重
        age: 年龄
        gender: 性别
    
    返回:
        解析后的健身计划字典
    """
    import re
    
    # 默认值
    daily_goals = {
        "squat": 20,
        "pushup": 15,
        "plank": 60,
        "jumping_jack": 30
    }
    weekly_goals = {
        "total_sessions": 5,
        "total_duration": 150
    }
    suggestions = []
    
    print(f"🔍 [AI] 开始解析AI响应...")
    
    # --- 安全限制函数 ---
    def clamp(value, min_val, max_val):
        return max(min_val, min(value, max_val))
        
    # 设定合理的上限（防止AI生成"200个深蹲"这种离谱数据）
    MAX_SQUAT = 60
    MAX_PUSHUP = 50
    MAX_PLANK = 120
    MAX_JACK = 100
    
    # 改进的解析逻辑：优先匹配"每组X次"或"X次"，如果没有则匹配"X组"
    # 深蹲：匹配"每组(\d+)次"或"(\d+)次"或"(\d+)组"
    squat_patterns = [
        r'深蹲[：:].*?每组\s*(\d+)\s*次',  # 深蹲：3组，每组15次
        r'深蹲[：:].*?(\d+)\s*次(?!组)',  # 深蹲：15次
        r'深蹲[：:].*?(\d+)\s*组',  # 深蹲：3组
        r'深蹲[：:]\s*(\d+)',  # 深蹲：15
    ]
    for pattern in squat_patterns:
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            # 如果值太小（可能是组数），尝试找每组次数
            if value < 10:
                each_match = re.search(r'深蹲[：:].*?每组\s*(\d+)\s*次', ai_text, re.IGNORECASE)
                if each_match:
                    value = int(each_match.group(1)) * value  # 组数 * 每组次数
            
            # 安全限制
            original_value = value
            value = clamp(value, 10, MAX_SQUAT)
            daily_goals["squat"] = value
            print(f"✅ [AI] 解析深蹲: {original_value}次 -> 修正为: {value}次")
            break
    
    # 俯卧撑
    pushup_patterns = [
        r'俯卧撑[：:].*?每组\s*(\d+)\s*次',
        r'俯卧撑[：:].*?(\d+)\s*次(?!组)',
        r'俯卧撑[：:].*?(\d+)\s*组',
        r'俯卧撑[：:]\s*(\d+)',
    ]
    for pattern in pushup_patterns:
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if value < 10:
                each_match = re.search(r'俯卧撑[：:].*?每组\s*(\d+)\s*次', ai_text, re.IGNORECASE)
                if each_match:
                    value = int(each_match.group(1)) * value
            
            # 安全限制
            original_value = value
            value = clamp(value, 5, MAX_PUSHUP)
            daily_goals["pushup"] = value
            print(f"✅ [AI] 解析俯卧撑: {original_value}次 -> 修正为: {value}次")
            break
    
    # 平板支撑（单位是秒）
    plank_patterns = [
        r'平板支撑[：:].*?每组\s*(\d+)\s*秒',
        r'平板支撑[：:].*?(\d+)\s*秒(?!组)',
        r'平板支撑[：:].*?(\d+)\s*组',
        r'平板支撑[：:]\s*(\d+)',
    ]
    for pattern in plank_patterns:
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if value < 20:  # 如果值太小，可能是组数
                each_match = re.search(r'平板支撑[：:].*?每组\s*(\d+)\s*秒', ai_text, re.IGNORECASE)
                if each_match:
                    value = int(each_match.group(1))  # 平板支撑通常取每组秒数
            
            # 安全限制
            original_value = value
            value = clamp(value, 20, MAX_PLANK)
            daily_goals["plank"] = value
            print(f"✅ [AI] 解析平板支撑: {original_value}秒 -> 修正为: {value}秒")
            break
    
    # 开合跳
    jack_patterns = [
        r'开合跳[：:].*?每组\s*(\d+)\s*次',
        r'开合跳[：:].*?(\d+)\s*次(?!组)',
        r'开合跳[：:].*?(\d+)\s*组',
        r'开合跳[：:]\s*(\d+)',
    ]
    for pattern in jack_patterns:
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if value < 10:
                each_match = re.search(r'开合跳[：:].*?每组\s*(\d+)\s*次', ai_text, re.IGNORECASE)
                if each_match:
                    value = int(each_match.group(1)) * value
            
            # 安全限制
            original_value = value
            value = clamp(value, 15, MAX_JACK)
            daily_goals["jumping_jack"] = value
            print(f"✅ [AI] 解析开合跳: {original_value}次 -> 修正为: {value}次")
            break
    
    # 每周运动次数
    sessions_patterns = [
        r'总运动次数[：:]\s*(\d+)',
        r'每周.*?(\d+)\s*次(?!运动)',
        r'运动次数[：:]\s*(\d+)',
    ]
    for pattern in sessions_patterns:
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match:
            weekly_goals["total_sessions"] = int(match.group(1))
            print(f"✅ [AI] 解析每周运动次数: {weekly_goals['total_sessions']}次")
            break
    
    # 每周运动时长（分钟）
    duration_patterns = [
        r'总运动时长[：:].*?(\d+)\s*分钟',
        r'每次运动.*?(\d+)[-~](\d+)\s*分钟',  # 45-60分钟
        r'每次运动.*?约\s*(\d+)\s*分钟',
        r'每周.*?(\d+)\s*分钟',
    ]
    for pattern in duration_patterns:
        match = re.search(pattern, ai_text, re.IGNORECASE)
        if match:
            # 如果是范围（如45-60），取平均值
            if len(match.groups()) == 2:
                min_val = int(match.group(1))
                max_val = int(match.group(2))
                weekly_goals["total_duration"] = (min_val + max_val) // 2 * weekly_goals["total_sessions"]
            else:
                duration = int(match.group(1))
                # 如果是每次时长，需要乘以次数
                if '每次' in match.group(0):
                    weekly_goals["total_duration"] = duration * weekly_goals["total_sessions"]
                else:
                    weekly_goals["total_duration"] = duration
            print(f"✅ [AI] 解析每周运动时长: {weekly_goals['total_duration']}分钟")
            break
    
    # 提取AI教练建议
    ai_advice = ""
    
    # 调试：打印原始文本的最后500个字符，看看AI到底返回了什么
    print(f"🔍 [AI Debug] 原始响应末尾预览:\n{ai_text[-500:]}")

    # 策略1：标准匹配 "教练建议"
    advice_match = re.search(r'###\s*教练建议\s*(.*?)(?=###|$)', ai_text, re.DOTALL)
    
    # 策略2：兼容 "AI教练深度指导"
    if not advice_match:
        advice_match = re.search(r'###\s*AI教练深度指导\s*(.*?)(?=###|$)', ai_text, re.DOTALL)
        
    # 策略3：兼容 "AI教练寄语"
    if not advice_match:
        advice_match = re.search(r'###\s*AI教练寄语\s*(.*?)(?=###|$)', ai_text, re.DOTALL)
        
    # 策略4：兼容 "AI教练对话"
    if not advice_match:
        advice_match = re.search(r'###\s*AI教练对话\s*(.*?)(?=###|$)', ai_text, re.DOTALL)

    # 策略5：寻找最后一个 "###" 标题之后的内容（通常是总结或寄语）
    if not advice_match:
        # 找到最后一个 ### 标题
        last_header_match = list(re.finditer(r'###\s*(.*?)\n', ai_text))
        if last_header_match:
            last_header = last_header_match[-1]
            # 如果最后一个标题包含 "指导"、"寄语"、"建议"、"总结" 等关键词
            header_text = last_header.group(1)
            if any(k in header_text for k in ['指导', '寄语', '建议', '总结', '话', 'Guide', 'Advice']):
                start_pos = last_header.end()
                ai_advice = ai_text[start_pos:].strip()
                print(f"✅ [AI] 策略5匹配成功 (标题: {header_text}): {ai_advice[:20]}...")

    if advice_match:
        ai_advice = advice_match.group(1).strip()
        print(f"✅ [AI] 精确匹配成功: {ai_advice[:20]}...")
    elif not ai_advice:
        # 策略6：实在找不到，尝试提取最后一段长文本
        print(f"⚠️ [AI] 未找到明确标记，尝试提取最后一段长文本...")
        paragraphs = [p.strip() for p in ai_text.split('\n\n') if len(p.strip()) > 50]
        if paragraphs:
            # 取最后一段，但要排除包含大量数字或列表项的段落
            potential_advice = paragraphs[-1]
            if not re.search(r'^\d+\.', potential_advice) and not re.search(r'^\-', potential_advice):
                ai_advice = potential_advice
                print(f"✅ [AI] 宽松匹配找到文本: {ai_advice[:20]}...")
            else:
                # 如果最后一段像列表，可能倒数第二段是建议
                if len(paragraphs) > 1:
                    ai_advice = paragraphs[-2]
                    print(f"✅ [AI] 宽松匹配找到倒数第二段: {ai_advice[:20]}...")

    # 提取专业建议
    suggestions_match = re.search(r'### 专业建议\s*(.*?)(?=###|$)', ai_text, re.DOTALL)
    if suggestions_match:
        suggestions_text = suggestions_match.group(1).strip()
        # 提取每一行作为建议
        suggestions = [line.strip() for line in suggestions_text.split('\n') if line.strip() and (line.strip().startswith('-') or line.strip()[0].isdigit())]
        # 去掉开头的序号或破折号
        suggestions = [re.sub(r'^[\d\.\-\s]+', '', s) for s in suggestions]
        print(f"✅ [AI] 解析专业建议: {len(suggestions)}条")
    else:
        # 旧的宽松解析逻辑
        lines = [line.strip() for line in ai_text.split('\n') if line.strip()]
        for line in lines:
            # 跳过标题、数字行、空行
            if (len(line) > 20 and 
                not re.match(r'^[#*\-•\d\s]+$', line) and 
                not re.match(r'^[###\s]+', line) and
                '建议' not in line and '目标' not in line and '情感激励' not in line and 'AI教练对话' not in line and 'AI教练寄语' not in line and 'AI教练深度指导' not in line and
                line not in ai_advice):
                suggestions.append(line)
    
    suggestions = suggestions[:5]  # 最多5条建议
    
    print(f"📋 [AI] 最终解析结果:")
    print(f"   深蹲: {daily_goals['squat']}次, 俯卧撑: {daily_goals['pushup']}次")
    print(f"   平板支撑: {daily_goals['plank']}秒, 开合跳: {daily_goals['jumping_jack']}次")
    print(f"   每周: {weekly_goals['total_sessions']}次, {weekly_goals['total_duration']}分钟")
    
    return {
        "daily_goals": daily_goals,
        "weekly_goals": weekly_goals,
        "suggestions": suggestions,
        "ai_advice": ai_advice,
        "ai_response": ai_text
    }

def ai_generate_fitness_plan(height, weight, age, gender, body_fat=None, custom_goal=None):
    """
    AI Agent: 根据用户生命体征生成个性化健身计划建议
    优先使用智谱AI API，如果失败则使用规则引擎
    
    参数:
        height: 身高（cm）
        weight: 体重（kg）
        age: 年龄
        gender: 性别（male/female/other）
        body_fat: 体脂率（%）
        custom_goal: 自定义目标（如：减脂、增肌、塑形）
    
    返回:
        包含每日目标和每周目标的字典
    """
    # 计算BMI
    bmi = calculate_bmi(height, weight)
    fitness_level = get_fitness_level(bmi, age) if bmi else "beginner"
    
    # 构建AI提示词
    gender_text = {"male": "男性", "female": "女性", "other": "其他"}.get(gender, "未知")
    age_text = f"{age}岁" if age else "未知"
    bmi_text = f"{round(bmi, 1)}" if bmi else "未知"
    body_fat_text = f"{body_fat}%" if body_fat else "未知"
    goal_text = custom_goal if custom_goal else "综合健康"
    
    prompt = f"""请根据以下用户信息，制定一份个性化的健身计划：

用户信息：
- 身高：{height}cm
- 体重：{weight}kg
- BMI：{bmi_text}
- 体脂率：{body_fat_text}
- 年龄：{age_text}
- 性别：{gender_text}
- 健身水平：{fitness_level}
- 健身目标：{goal_text}

请提供以下内容：

### 每日目标
- 深蹲：XX次（直接写总次数）
- 俯卧撑：XX次（直接写总次数）
- 平板支撑：XX秒（直接写总秒数）
- 开合跳：XX次（直接写总次数）

### 每周目标
- 总运动次数：X次
- 总运动时长：X分钟

重要：
1. 每日目标请直接写总次数/总秒数，不要写"X组，每组X次"的格式。
2. 运动强度必须合理，适合普通人。深蹲不要超过50次，俯卧撑不要超过40次，平板支撑不要超过90秒。
3. 不需要提供任何文字建议，只需要返回上述数据即可。"""
    
    # 尝试调用智谱AI API
    print(f"\n{'='*60}")
    print(f"🤖 [AI] 开始生成健身计划")
    print(f"📊 [AI] 用户信息: 身高{height}cm, 体重{weight}kg, 年龄{age_text}, 性别{gender_text}, BMI{bmi_text}, 体脂{body_fat_text}, 目标{goal_text}")
    print(f"{'='*60}\n")
    
    ai_response, ai_error = call_zhipu_ai_api(prompt)
    
    if ai_response:
        print(f"✅ [AI] 使用智谱AI生成计划")
        # 解析AI返回的结果
        result = parse_ai_response(ai_response, height, weight, age, gender)
        result["bmi"] = round(bmi, 1) if bmi else None
        result["fitness_level"] = fitness_level
        result["reasoning"] = f"基于您的身体指标（BMI: {round(bmi, 1) if bmi else '未提供'}, 体脂: {body_fat_text}, 目标: {goal_text}），智谱AI为您生成了个性化的健身计划。"
        result["ai_used"] = True
        result["ai_status"] = "success"
        result["ai_raw_response"] = ai_response  # 保存原始AI响应
        print(f"📋 [AI] 解析后的计划: 深蹲{result['daily_goals']['squat']}次, 俯卧撑{result['daily_goals']['pushup']}次")
        print(f"{'='*60}\n")
        return result
    else:
        print(f"⚠️  [AI] API调用失败 ({ai_error})，使用规则引擎生成计划")
    
    # 如果AI API调用失败，使用规则引擎（原有逻辑）
    # 基础建议值（根据健身水平调整）
    base_daily = {
        "beginner": {"squat": 15, "pushup": 10, "plank": 30, "jumping_jack": 20},
        "underweight": {"squat": 20, "pushup": 15, "plank": 45, "jumping_jack": 25},
        "normal": {"squat": 25, "pushup": 20, "plank": 60, "jumping_jack": 30},
        "overweight": {"squat": 30, "pushup": 25, "plank": 75, "jumping_jack": 40},
        "obese": {"squat": 35, "pushup": 30, "plank": 90, "jumping_jack": 50}
    }
    
    # 根据年龄调整（年龄越大，建议值适当降低）
    age_factor = 1.0
    if age:
        if age < 18:
            age_factor = 0.8  # 青少年适当降低
        elif age < 30:
            age_factor = 1.0  # 青年
        elif age < 40:
            age_factor = 0.9  # 中年
        elif age < 50:
            age_factor = 0.85
        else:
            age_factor = 0.75  # 中老年
    
    # 根据性别调整（男性通常力量更强）
    gender_factor = 1.0
    if gender == "male":
        gender_factor = 1.1
    elif gender == "female":
        gender_factor = 0.9
    
    # 生成每日目标
    base_values = base_daily.get(fitness_level, base_daily["beginner"])
    daily_goals = {
        "squat": max(10, int(base_values["squat"] * age_factor * gender_factor)),
        "pushup": max(5, int(base_values["pushup"] * age_factor * gender_factor)),
        "plank": max(20, int(base_values["plank"] * age_factor)),
        "jumping_jack": max(15, int(base_values["jumping_jack"] * age_factor * gender_factor))
    }

    # 根据自定义目标调整
    if custom_goal:
        if custom_goal == "减脂":
            daily_goals["jumping_jack"] = int(daily_goals["jumping_jack"] * 1.5)  # 增加有氧
            daily_goals["squat"] = int(daily_goals["squat"] * 1.2)  # 增加大肌群消耗
        elif custom_goal == "增肌":
            daily_goals["pushup"] = int(daily_goals["pushup"] * 1.3)  # 增加力量
            daily_goals["squat"] = int(daily_goals["squat"] * 1.3)
            daily_goals["jumping_jack"] = int(daily_goals["jumping_jack"] * 0.8)  # 减少有氧
        elif custom_goal == "塑形":
            daily_goals["plank"] = int(daily_goals["plank"] * 1.3)  # 增加核心
            daily_goals["squat"] = int(daily_goals["squat"] * 1.2)
        elif custom_goal == "增强体能":
            daily_goals["jumping_jack"] = int(daily_goals["jumping_jack"] * 1.3)
            daily_goals["pushup"] = int(daily_goals["pushup"] * 1.2)
    
    # 生成每周目标（基于每日目标计算）
    # 建议每周运动5-6次，每次约30-45分钟
    weekly_goals = {
        "total_sessions": 5 if fitness_level in ["beginner", "obese"] else 6,
        "total_duration": 150 if fitness_level in ["beginner", "obese"] else 180
    }

    # 根据目标调整每周计划
    if custom_goal == "减脂":
        weekly_goals["total_sessions"] = 6
        weekly_goals["total_duration"] = 200
    elif custom_goal == "增肌":
        weekly_goals["total_sessions"] = 4  # 增肌需要休息
        weekly_goals["total_duration"] = 160
    
    # 生成建议说明
    suggestions = []
    if bmi:
        if bmi < 18.5:
            suggestions.append("您的BMI偏低，建议增加力量训练，同时注意营养补充。")
        elif bmi >= 28:
            suggestions.append("您的BMI偏高，建议增加有氧运动（如开合跳），并配合力量训练。")
        else:
            suggestions.append("您的BMI在正常范围内，建议保持均衡的有氧和力量训练。")
    
    if age:
        if age >= 50:
            suggestions.append("考虑到您的年龄，建议从较低强度开始，循序渐进。")
        elif age < 18:
            suggestions.append("青少年时期是身体发育的关键期，建议适度运动，避免过度训练。")
    
    if gender == "female":
        suggestions.append("女性训练建议：可以适当增加平板支撑等核心训练，有助于塑造体形。")

    # 生成模板化的AI建议（当AI服务不可用时）
    # 根据目标定制更详细的建议
    diet_advice = ""
    exercise_advice = ""
    
    if custom_goal == "减脂":
        diet_advice = "在饮食方面，试着把晚餐的主食减半，换成粗粮（如玉米、红薯）。早餐可以吃得丰富些，比如全麦面包配鸡蛋和牛奶。记得少吃油炸食品和甜点，它们是热量炸弹哦！"
        exercise_advice = "运动时，保持心率在燃脂区间很重要。做开合跳时，注意膝盖微屈缓冲，避免关节受伤。如果觉得累，可以放慢节奏，但尽量不要停下来。"
    elif custom_goal == "增肌":
        diet_advice = "增肌需要足够的燃料！运动后30分钟内补充蛋白质非常关键，比如喝一杯蛋白粉或者吃两个蛋白。平时多吃牛肉、鸡胸肉，保证碳水化合物的摄入来维持训练强度。"
        exercise_advice = "做俯卧撑和深蹲时，动作要慢，感受肌肉的发力。宁可少做几个，也要保证动作标准。每组之间休息60-90秒，让肌肉得到恢复。"
    elif custom_goal == "塑形":
        diet_advice = "塑形期要注重蛋白质和维生素的摄入。多吃深色蔬菜，它们富含抗氧化剂。晚餐尽量清淡，避免水肿。"
        exercise_advice = "平板支撑是塑形的神器！做的时候收紧核心，不要塌腰。试着每天多坚持5秒，你会发现线条越来越紧致。"
    else:
        diet_advice = "保持均衡饮食是关键。每天保证一斤蔬菜半斤水果，多喝水促进代谢。少吃加工食品，回归天然食材。"
        exercise_advice = "循序渐进是最好的策略。运动前充分热身，运动后拉伸放松。听从身体的声音，累了就休息，不要勉强。"

    ai_advice_template = f"""你好呀！我是你的AI健身教练。很高兴能陪伴你开始这段"{custom_goal or '健康'}"之旅！

{diet_advice}

{exercise_advice}

改变从来都不是一件容易的事，但我看到了你的决心。不要急于求成，身体的改变需要时间。每一滴汗水都不会白流，坚持下去，你一定能遇到更好的自己。加油，我看好你！"""
    
    gender_text = {"male": "男性", "female": "女性", "other": "其他"}.get(gender, "未知")
    print(f"📋 [规则引擎] 生成的计划: 深蹲{daily_goals['squat']}次, 俯卧撑{daily_goals['pushup']}次")
    print(f"{'='*60}\n")
    return {
        "daily_goals": daily_goals,
        "weekly_goals": weekly_goals,
        "suggestions": suggestions,
        "ai_advice": ai_advice_template,
        "bmi": round(bmi, 1) if bmi else None,
        "fitness_level": fitness_level,
        "reasoning": f"基于您的身体指标（BMI: {round(bmi, 1) if bmi else '未提供'}, 年龄: {age or '未提供'}, 性别: {gender_text}），系统为您生成了个性化的健身计划。",
        "ai_used": False,
        "ai_status": ai_error if 'ai_error' in locals() else "unknown_error"
    }

@app.route('/api/ai/chat', methods=['POST'])
@require_auth
def chat_with_coach():
    """
    AI Coach Chat: 与AI教练进行实时对话
    
    Request Body:
        - message: 用户发送的消息
        - history: 历史消息列表 (可选)
    
    Returns:
        JSON: AI的回复
    """
    data = request.get_json() or {}
    user_message = data.get('message')
    history = data.get('history', [])
    
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
        
    # 构建对话上下文
    messages = [
        {
            "role": "system",
            "content": "你是一位专业的健身教练，语气亲切、专业且富有感染力。请根据用户的问题提供具体的健身、饮食或健康建议。回答要简洁明了，不要长篇大论。"
        }
    ]
    
    # 添加历史记录（限制最近5轮对话，避免token溢出）
    for msg in history[-10:]:
        messages.append({
            "role": msg.get('role'),
            "content": msg.get('content')
        })
        
    # 添加当前用户消息
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # 调用AI API
    api_key = os.getenv('ZHIPU_API_KEY')
    if not api_key or api_key == 'your_zhipu_api_key_here':
        # 尝试从文件读取
        try:
            from pathlib import Path
            env_path = Path(__file__).parent / '.env'
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('ZHIPU_API_KEY='):
                            file_key = line.split('=', 1)[1].strip()
                            if file_key and file_key != 'your_zhipu_api_key_here':
                                api_key = file_key
                                break
        except:
            pass
            
    if not api_key or api_key == 'your_zhipu_api_key_here':
        print("❌ [Chat] API Key未配置")
        return jsonify({"error": "AI服务未配置"}), 503
        
    # 打印Key的掩码以便调试 (只显示前4位和后4位)
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    print(f"🔑 [Chat] 使用API Key: {masked_key}")

    # 使用官方SDK或直接HTTP请求
    # 优先使用 glm-4-flash (免费且速度快)
    models_to_try = [
        "glm-4-flash"
    ]
    
    import time
    
    last_error = None
    
    for model in models_to_try:
        print(f"🤖 [Chat] 尝试使用模型: {model}")
        
        try:
            if ZhipuAI:
                client = ZhipuAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                ai_reply = response.choices[0].message.content
                return jsonify({"reply": ai_reply})
            else:
                # Fallback to requests if SDK not installed
                url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                # 增加超时时间到60秒
                response = requests.post(url, headers=headers, json=payload, timeout=60) 
                
                # 如果成功，直接返回
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        ai_reply = result['choices'][0]['message']['content']
                        return jsonify({"reply": ai_reply})
                
                # 如果失败，记录错误并尝试下一个模型
                error_detail = response.text
                print(f"⚠️ [Chat] 模型 {model} 调用失败 ({response.status_code}): {error_detail}")
                last_error = error_detail
                
                # 如果是 50603 (System busy) 或 429 (Rate limit)，等待一下再试下一个
                if response.status_code in [429, 500, 502, 503, 504]:
                    time.sleep(1) # 简单的退避
                    continue
                else:
                    continue

        except Exception as e:
            print(f"⚠️ [Chat] 模型 {model} 发生异常: {str(e)}")
            last_error = str(e)
            continue
            
    # 所有模型都失败了
    print(f"❌ [Chat] 所有模型均调用失败。最后一次错误: {last_error}")
    return jsonify({
        "error": "AI服务繁忙", 
        "details": f"所有可用模型均繁忙或不可用。最后错误: {last_error}"
    }), 503

@app.route('/api/ai/generate-plan', methods=['POST'])
@require_auth
def generate_ai_plan():
    """
    AI Agent: 根据用户生命体征生成个性化健身计划建议（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Request Body:
        - height: 身高（cm，可选，从用户资料获取）
        - weight: 体重（kg，可选，从用户资料获取）
        - age: 年龄（可选，从用户资料获取）
        - gender: 性别（可选，从用户资料获取）
    
    Returns:
        JSON: AI生成的健身计划建议
            - daily_goals: 每日目标
            - weekly_goals: 每周目标
            - suggestions: 建议说明
            - bmi: BMI指数
            - fitness_level: 健身水平
            - reasoning: 生成理由
    """
    data = request.get_json() or {}
    user_id = request.user_id
    
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    profile = user.profile.to_dict() if user.profile else {}
    
    # 优先使用请求中的数据，否则从用户资料中获取
    height = data.get('height') or profile.get('height')
    weight = data.get('weight') or profile.get('weight')
    age = data.get('age') or profile.get('age')
    gender = data.get('gender') or profile.get('gender')
    body_fat = data.get('body_fat') or profile.get('body_fat')
    custom_goal = data.get('custom_goal')
    
    # 检查是否有足够的信息
    if not height or not weight:
        return jsonify({
            "error": "缺少必要信息",
            "message": "请先在个人资料中填写身高和体重，以便AI生成个性化建议"
        }), 400
    
    # 调用AI agent生成建议
    ai_plan = ai_generate_fitness_plan(height, weight, age, gender, body_fat, custom_goal)
    
    return jsonify(ai_plan)

# ==================== 成就系统API ====================

# 成就定义
ACHIEVEMENT_DEFINITIONS = {
    "first_exercise": {"name": "初出茅庐", "icon": "🎯", "description": "完成第一次运动"},
    "exercise_10": {"name": "小试牛刀", "icon": "💪", "description": "累计完成10次运动"},
    "exercise_100": {"name": "百炼成钢", "icon": "🔥", "description": "累计完成100次运动"},
    "streak_3": {"name": "三日坚持", "icon": "📅", "description": "连续3天运动"},
    "streak_7": {"name": "一周坚持", "icon": "🔥", "description": "连续7天运动"},
    "streak_30": {"name": "月度坚持", "icon": "⭐", "description": "连续30天运动"},
    "squat_100": {"name": "深蹲达人", "icon": "💪", "description": "累计完成100次深蹲"},
    "pushup_100": {"name": "俯卧撑达人", "icon": "💪", "description": "累计完成100次俯卧撑"},
    "accuracy_90": {"name": "精准大师", "icon": "🎯", "description": "单次准确率达到90%"},
    "accuracy_100": {"name": "完美无缺", "icon": "👑", "description": "单次准确率达到100%"},
    "duration_10h": {"name": "时间管理大师", "icon": "⏰", "description": "累计运动时长达到10小时"},
    "all_exercises": {"name": "全能战士", "icon": "🏆", "description": "完成所有运动类型"},
    # 挑战相关成就
    "challenge_first": {"name": "挑战新手", "icon": "🎖️", "description": "完成第一个每日挑战"},
    "challenge_7": {"name": "挑战周星", "icon": "⭐", "description": "完成7个每日挑战"},
    "challenge_30": {"name": "挑战月神", "icon": "👑", "description": "完成30个每日挑战"},
    "challenge_streak_3": {"name": "挑战连击", "icon": "🔥", "description": "连续3天完成每日挑战"},
    "challenge_streak_7": {"name": "挑战大师", "icon": "💎", "description": "连续7天完成每日挑战"},
    "challenge_combo": {"name": "组合挑战者", "icon": "🎯", "description": "完成一次组合挑战"},
    "challenge_perfect": {"name": "完美挑战", "icon": "🏅", "description": "单次挑战准确率达到100%"}
}

def check_achievements(user_id):
    """检查并解锁用户成就"""
    try:
        # 从数据库获取用户会话
        user_sessions = Session.query.filter(
            Session.user_id == user_id,
            Session.status == 'completed'
        ).all()
        
        total_sessions = len(user_sessions)
        total_count = sum(s.total_count for s in user_sessions)
        
        # 统计各运动类型
        exercise_counts = {}
        for session in user_sessions:
            ex_type = session.exercise_type
            exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + session.total_count
        
        # 统计准确率
        max_accuracy = 0
        for session in user_sessions:
            if session.total_count > 0:
                # 确保correct_count不超过total_count，准确率不超过100%
                correct_count = min(session.correct_count or 0, session.total_count)
                accuracy = min(100, (correct_count / session.total_count) * 100)
                max_accuracy = max(max_accuracy, accuracy)
        
        # 统计总时长
        total_duration = 0
        for session in user_sessions:
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds() / 3600  # 小时
                total_duration += duration
        
        # 获取连续打卡天数
        checkin_stats = get_user_checkin_stats(user_id)
        current_streak = checkin_stats.get('current_streak', 0)
        
        # 获取挑战完成记录
        challenge_completions = get_challenge_completions(user_id)
        total_challenges = len(challenge_completions)
        
        # 计算连续完成挑战天数
        challenge_streak = 0
        today = date.today()
        check_date = today
        while True:
            date_str = check_date.isoformat()
            completions_on_date = get_challenge_completions(user_id, date_str)
            if completions_on_date:
                challenge_streak += 1
                check_date = check_date - timedelta(days=1)
            else:
                break
        
        # 检查是否有组合挑战完成记录
        has_combo_challenge = any('combo' in cid for cid in challenge_completions)
        
        # 获取已解锁成就
        user_achievements_dict = get_user_achievements(user_id)
        unlocked_ids = set(user_achievements_dict.keys())
        
        new_achievements = []
        
        # 检查成就
        checks = [
            ("first_exercise", total_sessions >= 1),
            ("exercise_10", total_sessions >= 10),
            ("exercise_100", total_sessions >= 100),
            ("streak_3", current_streak >= 3),
            ("streak_7", current_streak >= 7),
            ("streak_30", current_streak >= 30),
            ("squat_100", exercise_counts.get('squat', 0) >= 100),
            ("pushup_100", exercise_counts.get('pushup', 0) >= 100),
            ("accuracy_90", max_accuracy >= 90),
            ("accuracy_100", max_accuracy >= 100),
            ("duration_10h", total_duration >= 10),
            ("all_exercises", len([k for k in exercise_counts.keys() if k in ['squat', 'pushup', 'plank', 'jumping_jack']]) >= 4),
            # 挑战相关成就
            ("challenge_first", total_challenges >= 1),
            ("challenge_7", total_challenges >= 7),
            ("challenge_30", total_challenges >= 30),
            ("challenge_streak_3", challenge_streak >= 3),
            ("challenge_streak_7", challenge_streak >= 7),
            ("challenge_combo", has_combo_challenge)
        ]
        
        for achievement_id, condition in checks:
            if condition and achievement_id not in unlocked_ids:
                if unlock_achievement(user_id, achievement_id):
                    new_achievements.append(achievement_id)
                    logger.info(f"用户 {user_id} 解锁成就: {achievement_id}")
        
        return new_achievements
    except Exception as e:
        logger.error(f"检查成就失败: {str(e)}", exc_info=True)
        return []

@app.route('/api/user/achievements', methods=['GET'])
@require_auth
@handle_db_error
def get_user_achievements_api():
    """获取用户成就列表"""
    try:
        user_id = request.user_id
        user_achievements_dict = get_user_achievements(user_id)
        
        # 返回所有成就（已解锁和未解锁）
        result = []
        for achievement_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if achievement_id in user_achievements_dict:
                achievement_data = user_achievements_dict[achievement_id]
                result.append({
                    "id": achievement_id,
                    "name": definition["name"],
                    "icon": definition["icon"],
                    "description": definition["description"],
                    "unlocked": True,
                    "unlocked_at": achievement_data.get("unlocked_at")
                })
            else:
                result.append({
                    "id": achievement_id,
                    "name": definition["name"],
                    "icon": definition["icon"],
                    "description": definition["description"],
                    "unlocked": False
                })
        
        return jsonify({"achievements": result})
    except Exception as e:
        logger.error(f"获取成就列表失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取成就列表失败"}), 500

@app.route('/api/user/achievements/check', methods=['POST'])
@require_auth
@handle_db_error
def check_user_achievements():
    """检查并解锁新成就"""
    try:
        user_id = request.user_id
        new_achievement_ids = check_achievements(user_id)
        
        user_achievements_dict = get_user_achievements(user_id)
        
        result = []
        for achievement_id in new_achievement_ids:
            achievement_data = user_achievements_dict.get(achievement_id, {})
            result.append({
                "id": achievement_id,
                "name": ACHIEVEMENT_DEFINITIONS[achievement_id]["name"],
                "icon": ACHIEVEMENT_DEFINITIONS[achievement_id]["icon"],
                "description": ACHIEVEMENT_DEFINITIONS[achievement_id]["description"],
                "unlocked_at": achievement_data.get("unlocked_at")
            })
        
        return jsonify({
            "new_achievements": result,
            "count": len(new_achievement_ids)
        })
    except Exception as e:
        logger.error(f"检查成就失败: {str(e)}", exc_info=True)
        return jsonify({"error": "检查成就失败"}), 500

# ==================== 排行榜API ====================

@app.route('/api/leaderboard/weekly-count', methods=['GET'])
@require_auth
@handle_db_error
def get_weekly_count_leaderboard():
    """获取本周运动次数排行榜"""
    try:
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        
        # 从数据库查询本周完成的会话
        from sqlalchemy import func
        from database import Session, User
        
        leaderboard_query = db.session.query(
            Session.user_id,
            func.sum(Session.total_count).label('total_count')
        ).filter(
            Session.status == 'completed',
            Session.start_time >= week_start,
            Session.start_time < week_end
        ).group_by(Session.user_id).order_by(func.sum(Session.total_count).desc()).limit(20).all()
        
        result = []
        for rank, (user_id, count) in enumerate(leaderboard_query, 1):
            user = get_user_by_id(user_id)
            if user:
                result.append({
                    "rank": rank,
                    "user_id": user_id,
                    "username": user.username,
                    "nickname": user.nickname or user.username,
                    "count": int(count) if count else 0
                })
        
        return jsonify({"leaderboard": result})
    except Exception as e:
        logger.error(f"获取排行榜失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取排行榜失败"}), 500

@app.route('/api/leaderboard/weekly-duration', methods=['GET'])
@require_auth
@handle_db_error
def get_weekly_duration_leaderboard():
    """获取本周运动时长排行榜"""
    try:
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        
        # 从数据库查询本周完成的会话
        from sqlalchemy import func
        from database import Session
        
        sessions = Session.query.filter(
            Session.status == 'completed',
            Session.start_time >= week_start,
            Session.start_time < week_end,
            Session.end_time.isnot(None)
        ).all()
        
        user_durations = {}
        for session in sessions:
            duration = (session.end_time - session.start_time).total_seconds() / 60  # 分钟
            user_durations[session.user_id] = user_durations.get(session.user_id, 0) + duration
        
        leaderboard = sorted(user_durations.items(), key=lambda x: x[1], reverse=True)[:20]
        
        result = []
        for rank, (user_id, duration) in enumerate(leaderboard, 1):
            user = get_user_by_id(user_id)
            if user:
                result.append({
                    "rank": rank,
                    "user_id": user_id,
                    "username": user.username,
                    "nickname": user.nickname or user.username,
                    "duration": round(duration, 2)
                })
        
        return jsonify({"leaderboard": result})
    except Exception as e:
        logger.error(f"获取时长排行榜失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取排行榜失败"}), 500

@app.route('/api/leaderboard/streak', methods=['GET'])
@require_auth
@handle_db_error
def get_streak_leaderboard():
    """获取连续打卡排行榜"""
    try:
        from database import User
        
        # 获取所有用户的打卡统计
        all_users = User.query.all()
        user_streaks = []
        
        for user in all_users:
            stats = get_user_checkin_stats(user.user_id)
            # 使用current_streak，如果为0则使用longest_streak
            streak = stats['current_streak'] if stats['current_streak'] > 0 else stats['longest_streak']
            if streak > 0:  # 只显示有打卡记录的用户
                user_streaks.append({
                    "user_id": user.user_id,
                    "streak": streak
                })
        
        user_streaks.sort(key=lambda x: x['streak'], reverse=True)
        user_streaks = user_streaks[:20]
        
        result = []
        for rank, item in enumerate(user_streaks, 1):
            user = get_user_by_id(item['user_id'])
            if user:
                result.append({
                    "rank": rank,
                    "user_id": item['user_id'],
                    "username": user.username,
                    "nickname": user.nickname or user.username,
                    "streak": item['streak']
                })
        
        return jsonify({"leaderboard": result})
    except Exception as e:
        logger.error(f"获取打卡排行榜失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取排行榜失败"}), 500

@app.route('/api/leaderboard/accuracy', methods=['GET'])
@require_auth
@handle_db_error
def get_accuracy_leaderboard():
    """获取准确率排行榜"""
    try:
        from sqlalchemy import func
        from database import Session
        
        # 计算每个用户的平均准确率（排除平板支撑，因为平板支撑的total_count是秒数）
        user_stats = db.session.query(
            Session.user_id,
            func.sum(Session.correct_count).label('total_correct'),
            func.sum(Session.total_count).label('total_count')
        ).filter(
            Session.status == 'completed',
            Session.total_count > 0,
            Session.exercise_type != 'plank'  # 排除平板支撑
        ).group_by(Session.user_id).having(
            func.sum(Session.total_count) > 0
        ).all()
        
        avg_accuracies = {}
        for user_id, total_correct, total_count in user_stats:
            if total_count and total_count > 0:
                # 确保correct_count不超过total_count，准确率不超过100%
                total_correct = min(total_correct, total_count)
                avg_accuracies[user_id] = min(100, (total_correct / total_count) * 100)
        
        leaderboard = sorted(avg_accuracies.items(), key=lambda x: x[1], reverse=True)[:20]
        
        result = []
        for rank, (user_id, accuracy) in enumerate(leaderboard, 1):
            user = get_user_by_id(user_id)
            if user:
                result.append({
                    "rank": rank,
                    "user_id": user_id,
                    "username": user.username,
                    "nickname": user.nickname or user.username,
                    "accuracy": round(accuracy, 2)
                })
        
        return jsonify({"leaderboard": result})
    except Exception as e:
        logger.error(f"获取准确率排行榜失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取排行榜失败"}), 500

# ==================== 打卡系统API ====================

@app.route('/api/checkin', methods=['POST'])
@require_auth
@handle_db_error
def checkin():
    """用户打卡"""
    try:
        user_id = request.user_id
        
        # 添加打卡记录
        success = add_checkin(user_id)
        if not success:
            return jsonify({
                "message": "今天已打卡",
                "current_streak": get_user_checkin_stats(user_id)['current_streak']
            }), 200
        
        # 获取更新后的统计
        stats = get_user_checkin_stats(user_id)
        
        # 检查成就
        try:
            check_achievements(user_id)
        except Exception as e:
            logger.warning(f"检查成就失败: {str(e)}")
        
        return jsonify({
            "message": "打卡成功",
            "current_streak": stats['current_streak'],
            "longest_streak": stats['longest_streak'],
            "total_days": stats['total_days']
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"打卡失败: {str(e)}", exc_info=True)
        return jsonify({"error": "打卡失败"}), 500

@app.route('/api/user/checkin/streak', methods=['GET'])
@require_auth
@handle_db_error
def get_checkin_streak():
    """获取用户打卡连续天数"""
    try:
        user_id = request.user_id
        stats = get_user_checkin_stats(user_id)
        
        return jsonify({
            "current_streak": stats['current_streak'],
            "longest_streak": stats['longest_streak'],
            "total_days": stats['total_days'],
            "last_checkin_date": stats.get('last_checkin_date')
        })
    except Exception as e:
        logger.error(f"获取打卡统计失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取打卡统计失败"}), 500

@app.route('/api/user/checkin/calendar', methods=['GET'])
@require_auth
@handle_db_error
def get_checkin_calendar():
    """获取用户打卡日历数据"""
    try:
        user_id = request.user_id
        calendar_data = get_checkin_calendar(user_id, days=90)
        stats = get_user_checkin_stats(user_id)
        
        return jsonify({
            "calendar": calendar_data,
            "current_streak": stats['current_streak'],
            "longest_streak": stats['longest_streak'],
            "total_days": stats['total_days']
        })
    except Exception as e:
        logger.error(f"获取打卡日历失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取打卡日历失败"}), 500

# ==================== 训练报告生成API ====================

@app.route('/api/reports/weekly', methods=['POST'])
@require_auth
@handle_db_error
def generate_weekly_report():
    """生成周报"""
    try:
        user_id = request.user_id
        user = get_user_by_id(user_id)
        user_plan = get_user_plan(user_id)
        
        # 计算本周数据
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        
        # 从数据库查询本周会话
        from database import Session
        weekly_sessions = Session.query.filter(
            Session.user_id == user_id,
            Session.status == 'completed',
            Session.start_time >= week_start,
            Session.start_time < week_end
        ).all()
    
        total_count = sum(s.total_count for s in weekly_sessions)
        total_duration = 0
        exercise_counts = {}
        accuracy_scores = []
        
        for session in weekly_sessions:
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60
                total_duration += duration
            
            ex_type = session.exercise_type
            exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + session.total_count
            
            if session.total_count > 0:
                # 确保correct_count不超过total_count，准确率不超过100%
                correct_count = min(session.correct_count or 0, session.total_count)
                accuracy = min(100, (correct_count / session.total_count) * 100)
                accuracy_scores.append(accuracy)
        
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        # 检查目标完成情况
        daily_goals = {}
        if user_plan and user_plan.daily_goals:
            if isinstance(user_plan.daily_goals, str):
                try:
                    daily_goals = json.loads(user_plan.daily_goals)
                except:
                    daily_goals = {}
            else:
                daily_goals = user_plan.daily_goals
        
        goal_completion = {}
        for ex_type, count in exercise_counts.items():
            goal = daily_goals.get(ex_type, 0)
            if goal > 0:
                goal_completion[ex_type] = {
                    "target": goal * 7,  # 周目标
                    "actual": count,
                    "completion_rate": round((count / (goal * 7)) * 100, 2) if goal > 0 else 0
                }
        
        # 生成AI建议（简化版，实际可以调用智谱AI）
        suggestions = []
        if avg_accuracy < 80:
            suggestions.append("您的动作准确率还有提升空间，建议放慢动作速度，确保每个动作都做到位。")
        if total_duration < 150:
            suggestions.append("本周运动时长较少，建议增加运动频率，每天至少运动30分钟。")
        if len(exercise_counts) < 3:
            suggestions.append("建议尝试更多种类的运动，全面锻炼身体各个部位。")
        
        report = {
            "period": f"{week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}",
            "summary": {
                "total_sessions": len(weekly_sessions),
                "total_count": total_count,
                "total_duration": round(total_duration, 2),
                "avg_accuracy": round(avg_accuracy, 2)
            },
            "exercise_distribution": exercise_counts,
            "goal_completion": goal_completion,
            "suggestions": suggestions,
            "generated_at": datetime.now().isoformat()
        }
        
        return jsonify(report)
    except Exception as e:
        logger.error(f"生成周报失败: {str(e)}", exc_info=True)
        return jsonify({"error": "生成周报失败"}), 500

@app.route('/api/reports/monthly', methods=['POST'])
@require_auth
@handle_db_error
def generate_monthly_report():
    """生成月报"""
    try:
        user_id = request.user_id
        
        today = datetime.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1)
        
        # 从数据库查询本月会话
        from database import Session
        monthly_sessions = Session.query.filter(
            Session.user_id == user_id,
            Session.status == 'completed',
            Session.start_time >= month_start,
            Session.start_time < month_end
        ).all()
        
        total_count = sum(s.total_count for s in monthly_sessions)
        total_duration = 0
        exercise_counts = {}
        
        for session in monthly_sessions:
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60
                total_duration += duration
            
            ex_type = session.exercise_type
            exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + session.total_count
        
        # 获取成就
        user_achievements_dict = get_user_achievements(user_id)
        unlocked_achievements = len(user_achievements_dict)
        
        report = {
            "month": today.strftime('%Y-%m'),
            "summary": {
                "total_sessions": len(monthly_sessions),
                "total_count": total_count,
                "total_duration": round(total_duration, 2),
                "unlocked_achievements": unlocked_achievements
            },
            "exercise_distribution": exercise_counts,
            "achievements_unlocked": unlocked_achievements,
            "generated_at": datetime.now().isoformat()
        }
        
        return jsonify(report)
    except Exception as e:
        logger.error(f"生成月报失败: {str(e)}", exc_info=True)
        return jsonify({"error": "生成月报失败"}), 500

# ==================== 每日挑战API ====================

def generate_daily_challenge():
    """生成每日挑战"""
    challenges = [
        {
            "id": "squat_50",
            "type": "count",
            "exercise": "squat",
            "name": "深蹲挑战",
            "target": 50,
            "description": "今天完成50个深蹲",
            "reward": {"points": 100}
        },
        {
            "id": "pushup_30",
            "type": "count",
            "exercise": "pushup",
            "name": "俯卧撑挑战",
            "target": 30,
            "description": "今天完成30个俯卧撑",
            "reward": {"points": 80}
        },
        {
            "id": "plank_120",
            "type": "duration",
            "exercise": "plank",
            "name": "平板支撑挑战",
            "target": 120,
            "description": "平板支撑坚持2分钟",
            "reward": {"points": 90}
        },
        {
            "id": "combo_challenge",
            "type": "combo",
            "exercises": ["squat", "pushup", "jumping_jack"],
            "name": "组合挑战",
            "targets": {"squat": 20, "pushup": 15, "jumping_jack": 20},
            "description": "完成深蹲20次+俯卧撑15次+开合跳20次",
            "reward": {"points": 150}
        }
    ]
    
    # 根据日期选择挑战（确保每天相同）
    today = datetime.now().date()
    day_of_year = today.timetuple().tm_yday
    selected_challenge = challenges[day_of_year % len(challenges)]
    
    return {
        **selected_challenge,
        "date": today.isoformat(),
        "available": True
    }

@app.route('/api/challenges/daily', methods=['GET'])
@require_auth
def get_daily_challenge():
    """获取今日挑战"""
    challenge = generate_daily_challenge()
    return jsonify(challenge)

def validate_challenge_completion(user_id, challenge_id, challenge_data):
    """
    验证用户是否真的完成了挑战
    
    Args:
        user_id: 用户ID
        challenge_id: 挑战ID
        challenge_data: 挑战数据（包含type, exercise, target等）
    
    Returns:
        tuple: (是否完成, 实际完成值, 目标值)
    """
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # 查询今天的会话
    today_sessions = Session.query.filter(
        Session.user_id == user_id,
        Session.status == 'completed',
        Session.start_time >= today_start,
        Session.start_time <= today_end
    ).all()
    
    challenge_type = challenge_data.get('type')
    
    if challenge_type == 'count':
        # 计数类挑战：检查指定运动的累计次数
        exercise = challenge_data.get('exercise')
        target = challenge_data.get('target', 0)
        
        total_count = 0
        for session in today_sessions:
            if session.exercise_type == exercise:
                total_count += session.total_count
        
        completed = total_count >= target
        return completed, total_count, target
    
    elif challenge_type == 'duration':
        # 时长类挑战：检查指定运动的累计时长
        exercise = challenge_data.get('exercise')
        target = challenge_data.get('target', 0)  # 秒
        
        total_duration = 0
        for session in today_sessions:
            if session.exercise_type == exercise and session.end_time:
                duration = (session.end_time - session.start_time).total_seconds()
                total_duration += duration
        
        completed = total_duration >= target
        return completed, int(total_duration), target
    
    elif challenge_type == 'combo':
        # 组合挑战：检查多个运动是否都达到目标
        exercises = challenge_data.get('exercises', [])
        targets = challenge_data.get('targets', {})
        
        exercise_counts = {}
        for session in today_sessions:
            ex_type = session.exercise_type
            if ex_type in exercises:
                if ex_type == 'plank':
                    # 平板支撑：使用时长（秒）
                    if session.end_time:
                        duration_seconds = int((session.end_time - session.start_time).total_seconds())
                    else:
                        duration_seconds = 0
                    exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + duration_seconds
                else:
                    # 其他运动：使用次数
                    exercise_counts[ex_type] = exercise_counts.get(ex_type, 0) + session.total_count
        
        all_completed = True
        for exercise in exercises:
            if exercise_counts.get(exercise, 0) < targets.get(exercise, 0):
                all_completed = False
                break
        
        return all_completed, exercise_counts, targets
    
    return False, 0, 0

@app.route('/api/challenges/<challenge_id>/complete', methods=['POST', 'OPTIONS'])
@require_auth
def complete_challenge_endpoint(challenge_id):
    """
    完成挑战（带验证）
    
    Path Parameters:
        - challenge_id: 挑战ID
    
    Returns:
        JSON: 完成结果
    """
    try:
        user_id = request.user_id
        
        # 获取挑战数据
        challenge = generate_daily_challenge()
        if challenge.get('id') != challenge_id:
            # 如果挑战ID不匹配，尝试从挑战列表中找到对应的挑战
            challenges = [
                {"id": "squat_50", "type": "count", "exercise": "squat", "target": 50},
                {"id": "pushup_30", "type": "count", "exercise": "pushup", "target": 30},
                {"id": "plank_120", "type": "duration", "exercise": "plank", "target": 120},
                {"id": "combo_challenge", "type": "combo", "exercises": ["squat", "pushup", "jumping_jack"], 
                 "targets": {"squat": 20, "pushup": 15, "jumping_jack": 20}}
            ]
            challenge_data = next((c for c in challenges if c.get('id') == challenge_id), None)
            if not challenge_data:
                return jsonify({"error": "挑战不存在"}), 404
        else:
            challenge_data = challenge
        
        # 验证用户是否真的完成了挑战
        completed, actual_value, target_value = validate_challenge_completion(user_id, challenge_id, challenge_data)
        
        if not completed:
            # 构建友好的错误消息
            if challenge_data.get('type') == 'count':
                exercise_name = {'squat': '深蹲', 'pushup': '俯卧撑', 'jumping_jack': '开合跳'}.get(
                    challenge_data.get('exercise'), challenge_data.get('exercise')
                )
                return jsonify({
                    "error": "挑战未完成",
                    "message": f"您今天只完成了 {actual_value} 次{exercise_name}，还需要 {max(0, target_value - actual_value)} 次才能完成挑战",
                    "actual": actual_value,
                    "target": target_value,
                    "completed": False
                }), 400
            elif challenge_data.get('type') == 'duration':
                exercise_name = {'plank': '平板支撑'}.get(challenge_data.get('exercise'), challenge_data.get('exercise'))
                actual_minutes = actual_value // 60
                target_minutes = target_value // 60
                return jsonify({
                    "error": "挑战未完成",
                    "message": f"您今天只完成了 {actual_minutes} 分钟{exercise_name}，还需要 {max(0, target_minutes - actual_minutes)} 分钟才能完成挑战",
                    "actual": actual_value,
                    "target": target_value,
                    "completed": False
                }), 400
            else:
                return jsonify({
                    "error": "挑战未完成",
                    "message": "您还没有完成所有挑战目标",
                    "completed": False
                }), 400
        
        # 验证通过，记录完成
        success = complete_challenge(user_id, challenge_id)
        
        if success:
            logger.info(f"✅ 用户 {user_id} 完成挑战 {challenge_id}")
            
            # 检查挑战相关成就
            try:
                check_achievements(user_id)
            except Exception as e:
                logger.warning(f"检查成就失败: {str(e)}")
            
            return jsonify({
                "message": "挑战完成成功！",
                "challenge_id": challenge_id,
                "completed": True,
                "actual": actual_value,
                "target": target_value
            })
        else:
            logger.info(f"⚠️  用户 {user_id} 挑战 {challenge_id} 已完成")
            return jsonify({
                "message": "挑战已完成",
                "challenge_id": challenge_id,
                "completed": True
            })
    except ValueError as e:
        logger.error(f"❌ 完成挑战失败（验证错误）: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"❌ 完成挑战失败: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "error": "完成挑战失败",
            "message": str(e)
        }), 500

# 这个函数已经在前面更新过了，删除重复定义

# ==================== 全局错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({"error": "资源不存在"}), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"服务器内部错误: {str(error)}", exc_info=True)
    db.session.rollback()
    return jsonify({"error": "服务器内部错误"}), 500

@app.errorhandler(400)
def bad_request(error):
    """400错误处理"""
    return jsonify({"error": "请求参数错误"}), 400

@app.errorhandler(401)
def unauthorized(error):
    """401错误处理"""
    return jsonify({"error": "未授权访问"}), 401

@app.errorhandler(SQLAlchemyError)
def handle_db_exception(error):
    """数据库异常处理"""
    logger.error(f"数据库错误: {str(error)}", exc_info=True)
    db.session.rollback()
    return jsonify({"error": "数据库操作失败"}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """全局异常处理"""
    logger.error(f"未处理的异常: {str(error)}", exc_info=True)
    db.session.rollback()
    return jsonify({"error": "服务器错误"}), 500

# ==================== 健康检查 ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口（快速响应，不阻塞）"""
    try:
        # 尝试快速检查数据库连接（不阻塞）
        try:
            # 使用连接池的快速检查
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT 1'))
            db_status = "connected"
        except Exception as db_error:
            logger.warning(f"数据库连接检查失败: {str(db_error)}")
            db_status = "disconnected"
        
        return jsonify({
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        # 即使出错也返回200，避免影响负载均衡
        return jsonify({
            "status": "unhealthy",
            "database": "unknown",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 200

if __name__ == '__main__':
    # 启动时检查数据库连接（不阻塞启动）
    def check_db_on_startup():
        import time
        time.sleep(1)  # 等待应用完全初始化
        try:
            with app.app_context():
                db.session.execute(db.text('SELECT 1'))
                logger.info("✅ PostgreSQL 数据库连接正常")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL 数据库连接检查失败: {e}")
            logger.info("💡 服务器将继续启动，数据库连接将在实际使用时重试")
            logger.info("💡 检查 .env 文件中的 DATABASE_URL 配置")
    
    # 在后台线程中检查数据库，不阻塞服务器启动
    import threading
    db_check_thread = threading.Thread(target=check_db_on_startup, daemon=True)
    db_check_thread.start()
    
    print("[INFO] Starting Flask server...")
    print("[INFO] Server address: http://0.0.0.0:8000")
    print("[INFO] Local access: http://localhost:8000")
    print("[INFO] Press Ctrl+C to stop the server")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8000, use_reloader=False)
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        import traceback
        traceback.print_exc() 