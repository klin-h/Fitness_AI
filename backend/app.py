from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime, timedelta
import os
import hashlib
import secrets
from functools import wraps
import math
import requests
from dotenv import load_dotenv
from models import db, User, Plan, Session, Token
from pose_analyzer import create_analyzer

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 存储活跃的分析器实例，用于保持状态（如计数）
# Key: f"{user_id}_{exercise_type}", Value: PoseAnalyzer instance
active_analyzers = {}

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 在应用启动时自动创建表
with app.app_context():
    db.create_all()

# 数据存储（生产环境中应使用数据库）
exercise_data = {}

# 辅助函数：密码哈希
def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

# 辅助函数：生成token
def generate_token():
    """生成token"""
    return secrets.token_urlsafe(32)

# 辅助函数：验证token
def verify_token(token_str):
    """验证token"""
    token_record = Token.query.get(token_str)
    if token_record:
        if datetime.now() < token_record.expire_time:
            return token_record.user_id
        else:
            # 过期删除
            db.session.delete(token_record)
            db.session.commit()
    return None

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "未提供认证token"}), 401
        
        # 移除 "Bearer " 前缀（如果存在）
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
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
    """
    data = request.get_json()
    exercise_type = data.get('exercise_type', 'squat')
    user_id = data.get('user_id', 'anonymous')
    
    session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    new_session = Session(
        session_id=session_id,
        user_id=user_id,
        exercise_type=exercise_type,
        start_time=datetime.now(),
        status="active",
        scores=[]
    )
    db.session.add(new_session)
    db.session.commit()
    
    return jsonify({
        "session_id": session_id,
        "message": "Session started successfully"
    })

@app.route('/api/session/<session_id>/data', methods=['POST'])
def submit_exercise_data(session_id):
    """
    提交运动数据
    """
    session = Session.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    data = request.get_json()
    pose_data = data.get('pose_data')
    is_correct = data.get('is_correct', False)
    score = data.get('score', 0)
    feedback = data.get('feedback', '')
    
    session.total_count += 1
    if is_correct:
        session.correct_count += 1
    
    # 更新scores JSONB字段
    # 注意：需要创建一个新列表以触发SQLAlchemy的变更检测，或者使用flag_modified
    new_score = {
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "is_correct": is_correct,
        "feedback": feedback,
        "pose_data": pose_data
    }
    
    # 复制现有列表并添加新项
    current_scores = list(session.scores) if session.scores else []
    current_scores.append(new_score)
    session.scores = current_scores
    
    db.session.commit()
    
    return jsonify({
        "message": "Data submitted successfully",
        "session_stats": {
            "total_count": session.total_count,
            "correct_count": session.correct_count,
            "accuracy": session.correct_count / session.total_count if session.total_count > 0 else 0
        }
    })

from datetime import datetime, timedelta
from sqlalchemy import func

@app.route('/api/user/stats/weekly', methods=['GET'])
def get_weekly_stats():
    """获取用户本周运动统计数据"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Missing Authorization header"}), 401
    
    token = auth_header.split(" ")[1]
    token_obj = Token.query.get(token)
    if not token_obj or token_obj.expire_time < datetime.now():
        return jsonify({"error": "Invalid or expired token"}), 401
        
    user_id = token_obj.user_id
    
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
def get_exercise_distribution():
    """获取用户运动类型分布"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Missing Authorization header"}), 401
    
    token = auth_header.split(" ")[1]
    token_obj = Token.query.get(token)
    if not token_obj or token_obj.expire_time < datetime.now():
        return jsonify({"error": "Invalid or expired token"}), 401
        
    user_id = token_obj.user_id
    
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
    """
    session = Session.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    session.end_time = datetime.now()
    session.status = 'completed'
    
    # 计算统计数据
    total_count = session.total_count
    correct_count = session.correct_count
    accuracy = correct_count / total_count if total_count > 0 else 0
    
    scores_list = session.scores if session.scores else []
    avg_score = sum([s['score'] for s in scores_list]) / len(scores_list) if scores_list else 0
    
    db.session.commit()
    
    return jsonify({
        "session_id": session_id,
        "summary": {
            "total_count": total_count,
            "correct_count": correct_count,
            "accuracy": accuracy,
            "average_score": avg_score,
            "duration": session.end_time.isoformat(),
            "exercise_type": session.exercise_type
        },
        "message": "Session ended successfully"
    })

@app.route('/api/user/<user_id>/history', methods=['GET'])
def get_user_history(user_id):
    """
    获取用户历史记录
    """
    limit = request.args.get('limit', 10, type=int)
    exercise_type = request.args.get('exercise_type')
    
    query = Session.query.filter_by(user_id=user_id)
    if exercise_type:
        query = query.filter_by(exercise_type=exercise_type)
    
    # 按开始时间倒序
    sessions = query.order_by(Session.start_time.desc()).limit(limit).all()
    
    return jsonify({
        "user_id": user_id,
        "sessions": [s.to_dict() for s in sessions],
        "total_sessions": query.count() # 注意：这里count是总数，不是limit后的数量
    })

@app.route('/api/analytics/pose', methods=['POST'])
def analyze_pose():
    """
    分析姿态数据
    
    Request Body:
        - pose_landmarks: MediaPipe姿态关键点数据
        - exercise_type: 运动类型
    
    Returns:
        JSON: 分析结果
    """
    data = request.get_json()
    pose_landmarks = data.get('pose_landmarks')
    exercise_type = data.get('exercise_type', 'squat')
    
    if not pose_landmarks:
        return jsonify({"error": "缺少姿态关键点数据"}), 400

    # 获取用户标识（优先使用认证用户ID，否则使用IP）
    # 注意：如果未经过 require_auth 装饰器，request.user_id 可能不存在
    user_id = getattr(request, 'user_id', request.remote_addr)
    
    # 获取或创建分析器实例
    # 使用 user_id 和 exercise_type 作为键，确保每个用户的每种运动都有独立的状态
    analyzer_key = f"{user_id}_{exercise_type}"
    
    # 如果分析器不存在，创建新的
    if analyzer_key not in active_analyzers:
        # 简单的内存管理：清理该用户的其他分析器，假设用户同一时间只做一个运动
        keys_to_remove = [k for k in active_analyzers.keys() if k.startswith(f"{user_id}_")]
        for k in keys_to_remove:
            del active_analyzers[k]
            
        active_analyzers[analyzer_key] = create_analyzer(exercise_type)
    
    analyzer = active_analyzers[analyzer_key]
    
    # 执行分析
    try:
        result = analyzer.analyze(pose_landmarks)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"分析过程出错: {str(e)}"}), 500

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
def register():
    """
    用户注册
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '')
    nickname = data.get('nickname', username)
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "密码长度至少6位"}), 400
    
    # 检查用户是否存在
    if User.query.get(username):
        return jsonify({"error": "用户名已存在"}), 400
    
    # 创建新用户
    new_user = User(
        user_id=username,
        username=username,
        password_hash=hash_password(password),
        email=email,
        nickname=nickname,
        created_at=datetime.now(),
        avatar="",
        profile={
            "height": 0,
            "weight": 0,
            "age": 0,
            "gender": ""
        }
    )
    db.session.add(new_user)
    db.session.commit()
    
    # 生成token
    token_str = generate_token()
    expire_time = datetime.now() + timedelta(days=1)
    
    new_token = Token(
        token=token_str,
        user_id=username,
        expire_time=expire_time
    )
    db.session.add(new_token)
    db.session.commit()
    
    return jsonify({
        "message": "注册成功",
        "token": token_str,
        "user": {
            "user_id": username,
            "username": username,
            "nickname": nickname,
            "email": email
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    user = User.query.get(username)
    
    if not user or user.password_hash != hash_password(password):
        return jsonify({"error": "用户名或密码错误"}), 401
    
    # 生成token
    token_str = generate_token()
    expire_time = datetime.now() + timedelta(days=1)
    
    new_token = Token(
        token=token_str,
        user_id=username,
        expire_time=expire_time
    )
    db.session.add(new_token)
    db.session.commit()
    
    return jsonify({
        "message": "登录成功",
        "token": token_str,
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email
        }
    })

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """
    获取当前用户信息（需要认证）
    """
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    return jsonify(user.to_dict())

@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    修改密码（需要认证）
    """
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({"error": "旧密码和新密码不能为空"}), 400
    
    if len(new_password) < 6:
        return jsonify({"error": "新密码长度至少6位"}), 400
    
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    # 验证旧密码
    if user.password_hash != hash_password(old_password):
        return jsonify({"error": "旧密码错误"}), 401
    
    # 更新密码
    user.password_hash = hash_password(new_password)
    db.session.commit()
    
    return jsonify({"message": "密码修改成功"})

@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """
    获取用户个人资料（需要认证）
    """
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    return jsonify(user.to_dict())

@app.route('/api/user/profile', methods=['PUT'])
@require_auth
def update_user_profile():
    """
    更新用户个人资料（需要认证）
    """
    data = request.get_json()
    user = User.query.get(request.user_id)
    
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    # 更新允许修改的字段
    if 'nickname' in data:
        user.nickname = data['nickname']
    if 'email' in data:
        user.email = data['email']
    if 'avatar' in data:
        user.avatar = data['avatar']
    if 'profile' in data:
        # 更新JSONB字段
        current_profile = dict(user.profile) if user.profile else {}
        current_profile.update(data['profile'])
        user.profile = current_profile
    
    db.session.commit()
    
    return jsonify(user.to_dict())

@app.route('/api/user/plan', methods=['GET'])
@require_auth
def get_user_plan():
    """
    获取用户的健身计划（需要认证）
    """
    plan = Plan.query.filter_by(user_id=request.user_id).first()
    
    if plan:
        return jsonify(plan.to_dict())
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

@app.route('/api/user/plan', methods=['PUT'])
@require_auth
def update_user_plan():
    """
    更新用户的健身计划（需要认证）
    """
    data = request.get_json()
    plan = Plan.query.filter_by(user_id=request.user_id).first()
    
    if not plan:
        plan = Plan(
            user_id=request.user_id,
            daily_goals={},
            weekly_goals={},
            created_at=datetime.now()
        )
        db.session.add(plan)
    
    # 更新每日目标
    if 'daily_goals' in data:
        current_daily = dict(plan.daily_goals) if plan.daily_goals else {}
        current_daily.update(data['daily_goals'])
        plan.daily_goals = current_daily
    
    # 更新每周目标
    if 'weekly_goals' in data:
        current_weekly = dict(plan.weekly_goals) if plan.weekly_goals else {}
        current_weekly.update(data['weekly_goals'])
        plan.weekly_goals = current_weekly
    
    plan.updated_at = datetime.now()
    db.session.commit()
    
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
        AI生成的文本，如果失败则返回None
    """
    api_key = os.getenv('ZHIPU_API_KEY')
    
    # 如果没有配置API Key，返回None（将使用规则引擎）
    if not api_key or api_key == 'your_zhipu_api_key_here':
        print("⚠️  [AI] API Key未配置，将使用规则引擎")
        return None
    
    print(f"🤖 [AI] 正在调用智谱AI API...")
    print(f"📝 [AI] 提示词长度: {len(prompt)} 字符")
    
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "glm-4",  # 使用GLM-4模型
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
    
    # 重试机制
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"🔄 [AI] 第 {attempt + 1} 次尝试...")
            
            print(f"🌐 [AI] 发送请求到: {url}")
            # 增加超时时间：连接超时5秒，读取超时30秒
            response = requests.post(url, headers=headers, json=data, timeout=(5, 30))
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                ai_content = result['choices'][0]['message']['content']
                print(f"✅ [AI] API调用成功！")
                print(f"📄 [AI] AI返回内容长度: {len(ai_content)} 字符")
                print(f"📄 [AI] AI返回内容预览: {ai_content[:200]}...")
                return ai_content
            else:
                print(f"❌ [AI] API返回格式异常: {result}")
                return None
                
        except requests.exceptions.Timeout as e:
            print(f"⏱️  [AI] 请求超时 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                import time
                wait_time = (attempt + 1) * 2  # 递增等待时间
                print(f"⏳ [AI] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"❌ [AI] 所有重试均失败，网络可能不稳定或服务器响应慢")
                return None
                
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 [AI] 连接错误 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                import time
                wait_time = (attempt + 1) * 2
                print(f"⏳ [AI] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"❌ [AI] 无法连接到服务器，请检查网络连接")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ [AI] 网络请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                import time
                wait_time = (attempt + 1) * 2
                print(f"⏳ [AI] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                return None
                
        except Exception as e:
            print(f"❌ [AI] API调用失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    return None

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
            daily_goals["squat"] = value
            print(f"✅ [AI] 解析深蹲: {value}次")
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
            daily_goals["pushup"] = value
            print(f"✅ [AI] 解析俯卧撑: {value}次")
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
            daily_goals["plank"] = value
            print(f"✅ [AI] 解析平板支撑: {value}秒")
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
            daily_goals["jumping_jack"] = value
            print(f"✅ [AI] 解析开合跳: {value}次")
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
    
    # 提取建议（按段落分割，过滤掉标题和数字行）
    lines = [line.strip() for line in ai_text.split('\n') if line.strip()]
    for line in lines:
        # 跳过标题、数字行、空行
        if (len(line) > 20 and 
            not re.match(r'^[#*\-•\d\s]+$', line) and 
            not re.match(r'^[###\s]+', line) and
            '建议' not in line and '目标' not in line):
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
        "ai_response": ai_text
    }

def ai_generate_fitness_plan(height, weight, age, gender):
    """
    AI Agent: 根据用户生命体征生成个性化健身计划建议
    优先使用智谱AI API，如果失败则使用规则引擎
    
    参数:
        height: 身高（cm）
        weight: 体重（kg）
        age: 年龄
        gender: 性别（male/female/other）
    
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
    
    prompt = f"""请根据以下用户信息，制定一份个性化的健身计划：

用户信息：
- 身高：{height}cm
- 体重：{weight}kg
- BMI：{bmi_text}
- 年龄：{age_text}
- 性别：{gender_text}
- 健身水平：{fitness_level}

请严格按照以下格式提供：

### 每日目标
- 深蹲：XX次（直接写总次数，不要写"X组，每组X次"）
- 俯卧撑：XX次（直接写总次数）
- 平板支撑：XX秒（直接写总秒数）
- 开合跳：XX次（直接写总次数）

### 每周目标
- 总运动次数：X次
- 总运动时长：X分钟（每周总时长）

### 专业建议
1. 建议内容1
2. 建议内容2
3. 建议内容3

重要：每日目标请直接写总次数/总秒数，不要写"X组，每组X次"的格式。例如写"深蹲：30次"而不是"深蹲：3组，每组10次"。"""
    
    # 尝试调用智谱AI API
    print(f"\n{'='*60}")
    print(f"🤖 [AI] 开始生成健身计划")
    print(f"📊 [AI] 用户信息: 身高{height}cm, 体重{weight}kg, 年龄{age_text}, 性别{gender_text}, BMI{bmi_text}")
    print(f"{'='*60}\n")
    
    ai_response = call_zhipu_ai_api(prompt)
    
    if ai_response:
        print(f"✅ [AI] 使用智谱AI生成计划")
        # 解析AI返回的结果
        result = parse_ai_response(ai_response, height, weight, age, gender)
        result["bmi"] = round(bmi, 1) if bmi else None
        result["fitness_level"] = fitness_level
        result["reasoning"] = f"基于您的身体指标（BMI: {round(bmi, 1) if bmi else '未提供'}, 年龄: {age or '未提供'}, 性别: {gender_text}），智谱AI为您生成了个性化的健身计划。"
        result["ai_used"] = True
        result["ai_raw_response"] = ai_response  # 保存原始AI响应
        print(f"📋 [AI] 解析后的计划: 深蹲{result['daily_goals']['squat']}次, 俯卧撑{result['daily_goals']['pushup']}次")
        print(f"{'='*60}\n")
        return result
    else:
        print(f"⚠️  [AI] API调用失败，使用规则引擎生成计划")
    
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
    
    # 生成每周目标（基于每日目标计算）
    # 建议每周运动5-6次，每次约30-45分钟
    weekly_goals = {
        "total_sessions": 5 if fitness_level in ["beginner", "obese"] else 6,
        "total_duration": 150 if fitness_level in ["beginner", "obese"] else 180
    }
    
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
    
    gender_text = {"male": "男性", "female": "女性", "other": "其他"}.get(gender, "未知")
    print(f"📋 [规则引擎] 生成的计划: 深蹲{daily_goals['squat']}次, 俯卧撑{daily_goals['pushup']}次")
    print(f"{'='*60}\n")
    return {
        "daily_goals": daily_goals,
        "weekly_goals": weekly_goals,
        "suggestions": suggestions,
        "bmi": round(bmi, 1) if bmi else None,
        "fitness_level": fitness_level,
        "reasoning": f"基于您的身体指标（BMI: {round(bmi, 1) if bmi else '未提供'}, 年龄: {age or '未提供'}, 性别: {gender_text}），系统为您生成了个性化的健身计划。",
        "ai_used": False
    }

@app.route('/api/ai/generate-plan', methods=['POST'])
@require_auth
def generate_ai_plan():
    """
    AI Agent: 根据用户生命体征生成个性化健身计划建议（需要认证）
    """
    data = request.get_json() or {}
    user = User.query.get(request.user_id)
    
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    profile = user.profile or {}
    
    # 优先使用请求中的数据，否则从用户资料中获取
    height = data.get('height') or profile.get('height')
    weight = data.get('weight') or profile.get('weight')
    age = data.get('age') or profile.get('age')
    gender = data.get('gender') or profile.get('gender')
    
    # 检查是否有足够的信息
    if not height or not weight:
        return jsonify({
            "error": "缺少必要信息",
            "message": "请先在个人资料中填写身高和体重，以便AI生成个性化建议"
        }), 400
    
    # 调用AI agent生成建议
    ai_plan = ai_generate_fitness_plan(height, weight, age, gender)
    
    return jsonify(ai_plan)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000) 