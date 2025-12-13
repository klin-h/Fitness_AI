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

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 数据存储（生产环境中应使用数据库）
exercise_data = {}

# 数据文件路径
USERS_FILE = 'users.json'
TOKENS_FILE = 'tokens.json'
SESSIONS_FILE = 'sessions.json'
PLANS_FILE = 'plans.json'

# 初始化用户数据文件
def init_users_file():
    """初始化用户数据文件"""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def init_tokens_file():
    """初始化token文件"""
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_users():
    """加载用户数据"""
    init_users_file()
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    """保存用户数据"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_tokens():
    """加载token数据"""
    init_tokens_file()
    try:
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_tokens(tokens):
    """保存token数据"""
    with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)

def init_sessions_file():
    """初始化会话数据文件"""
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_sessions():
    """加载会话数据"""
    init_sessions_file()
    try:
        with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_sessions(sessions):
    """保存会话数据"""
    with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def init_plans_file():
    """初始化健身计划数据文件"""
    if not os.path.exists(PLANS_FILE):
        with open(PLANS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_plans():
    """加载健身计划数据"""
    init_plans_file()
    try:
        with open(PLANS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_plans(plans):
    """保存健身计划数据"""
    with open(PLANS_FILE, 'w', encoding='utf-8') as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

# 从文件加载会话数据（必须在函数定义之后）
user_sessions = load_sessions()

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    """生成token"""
    return secrets.token_urlsafe(32)

def verify_token(token):
    """验证token"""
    tokens = load_tokens()
    if token in tokens:
        token_data = tokens[token]
        # 检查token是否过期（24小时）
        expire_time = datetime.fromisoformat(token_data['expire_time'])
        if datetime.now() < expire_time:
            return token_data['user_id']
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
    
    Request Body:
        - exercise_type: 运动类型
        - user_id: 用户ID（可选）
    
    Returns:
        JSON: 会话ID和初始数据
    """
    data = request.get_json()
    exercise_type = data.get('exercise_type', 'squat')
    user_id = data.get('user_id', 'anonymous')
    
    session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    user_sessions[session_id] = {
        "session_id": session_id,
        "user_id": user_id,
        "exercise_type": exercise_type,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "total_count": 0,
        "correct_count": 0,
        "scores": [],
        "status": "active"
    }
    
    # 保存到文件
    save_sessions(user_sessions)
    
    return jsonify({
        "session_id": session_id,
        "message": "Session started successfully"
    })

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
    if session_id not in user_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    data = request.get_json()
    pose_data = data.get('pose_data')
    is_correct = data.get('is_correct', False)
    score = data.get('score', 0)
    feedback = data.get('feedback', '')
    
    session = user_sessions[session_id]
    session['total_count'] += 1
    
    if is_correct:
        session['correct_count'] += 1
    
    session['scores'].append({
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "is_correct": is_correct,
        "feedback": feedback,
        "pose_data": pose_data  # 实际项目中可能需要压缩或存储到文件
    })
    
    # 保存到文件
    save_sessions(user_sessions)
    
    return jsonify({
        "message": "Data submitted successfully",
        "session_stats": {
            "total_count": session['total_count'],
            "correct_count": session['correct_count'],
            "accuracy": session['correct_count'] / session['total_count'] if session['total_count'] > 0 else 0
        }
    })

@app.route('/api/session/<session_id>/end', methods=['POST'])
def end_session(session_id):
    """
    结束锻炼会话
    
    Path Parameters:
        - session_id: 会话ID
    
    Returns:
        JSON: 会话总结数据
    """
    if session_id not in user_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session = user_sessions[session_id]
    session['end_time'] = datetime.now().isoformat()
    session['status'] = 'completed'
    
    # 计算会话统计
    total_count = session['total_count']
    correct_count = session['correct_count']
    accuracy = correct_count / total_count if total_count > 0 else 0
    avg_score = sum([s['score'] for s in session['scores']]) / len(session['scores']) if session['scores'] else 0
    
    # 保存到文件
    save_sessions(user_sessions)
    
    return jsonify({
        "session_id": session_id,
        "summary": {
            "total_count": total_count,
            "correct_count": correct_count,
            "accuracy": accuracy,
            "average_score": avg_score,
            "duration": session['end_time'],  # 实际应该是结束时间 - 开始时间
            "exercise_type": session['exercise_type']
        },
        "message": "Session ended successfully"
    })

@app.route('/api/user/<user_id>/history', methods=['GET'])
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
    limit = request.args.get('limit', 10, type=int)
    exercise_type = request.args.get('exercise_type')
    
    user_sessions_list = []
    for session_id, session in user_sessions.items():
        if session['user_id'] == user_id:
            if exercise_type is None or session['exercise_type'] == exercise_type:
                user_sessions_list.append(session)
    
    # 按开始时间排序，最新的在前
    user_sessions_list.sort(key=lambda x: x['start_time'], reverse=True)
    
    return jsonify({
        "user_id": user_id,
        "sessions": user_sessions_list[:limit],
        "total_sessions": len(user_sessions_list)
    })

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
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '')
    nickname = data.get('nickname', username)
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "密码长度至少6位"}), 400
    
    users = load_users()
    
    if username in users:
        return jsonify({"error": "用户名已存在"}), 400
    
    # 创建新用户
    user_id = username
    users[user_id] = {
        "user_id": user_id,
        "username": username,
        "password_hash": hash_password(password),
        "email": email,
        "nickname": nickname,
        "created_at": datetime.now().isoformat(),
        "avatar": "",  # 头像URL
        "profile": {
            "height": 0,
            "weight": 0,
            "age": 0,
            "gender": ""
        }
    }
    save_users(users)
    
    # 生成token
    token = generate_token()
    tokens = load_tokens()
    expire_time = datetime.now() + timedelta(days=1)  # 24小时后过期
    tokens[token] = {
        "user_id": user_id,
        "expire_time": expire_time.isoformat()
    }
    save_tokens(tokens)
    
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

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录
    
    Request Body:
        - username: 用户名
        - password: 密码
    
    Returns:
        JSON: 登录结果和token
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    users = load_users()
    
    if username not in users:
        return jsonify({"error": "用户名或密码错误"}), 401
    
    user = users[username]
    password_hash = hash_password(password)
    
    if user['password_hash'] != password_hash:
        return jsonify({"error": "用户名或密码错误"}), 401
    
    # 生成token
    token = generate_token()
    tokens = load_tokens()
    expire_time = datetime.now() + timedelta(days=1)  # 24小时后过期
    tokens[token] = {
        "user_id": username,
        "expire_time": expire_time.isoformat()
    }
    save_tokens(tokens)
    
    return jsonify({
        "message": "登录成功",
        "token": token,
        "user": {
            "user_id": user['user_id'],
            "username": user['username'],
            "nickname": user['nickname'],
            "email": user['email']
        }
    })

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """
    获取当前用户信息（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Returns:
        JSON: 用户信息
    """
    users = load_users()
    user_id = request.user_id
    
    if user_id not in users:
        return jsonify({"error": "用户不存在"}), 404
    
    user = users[user_id].copy()
    # 移除敏感信息
    user.pop('password_hash', None)
    
    return jsonify(user)

@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
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
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({"error": "旧密码和新密码不能为空"}), 400
    
    if len(new_password) < 6:
        return jsonify({"error": "新密码长度至少6位"}), 400
    
    users = load_users()
    user_id = request.user_id
    
    if user_id not in users:
        return jsonify({"error": "用户不存在"}), 404
    
    user = users[user_id]
    
    # 验证旧密码
    if user['password_hash'] != hash_password(old_password):
        return jsonify({"error": "旧密码错误"}), 401
    
    # 更新密码
    user['password_hash'] = hash_password(new_password)
    save_users(users)
    
    return jsonify({"message": "密码修改成功"})

@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """
    获取用户个人资料（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Returns:
        JSON: 用户个人资料
    """
    users = load_users()
    user_id = request.user_id
    
    if user_id not in users:
        return jsonify({"error": "用户不存在"}), 404
    
    user = users[user_id].copy()
    user.pop('password_hash', None)
    
    return jsonify(user)

@app.route('/api/user/profile', methods=['PUT'])
@require_auth
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
    users = load_users()
    user_id = request.user_id
    
    if user_id not in users:
        return jsonify({"error": "用户不存在"}), 404
    
    user = users[user_id]
    
    # 更新允许修改的字段
    if 'nickname' in data:
        user['nickname'] = data['nickname']
    if 'email' in data:
        user['email'] = data['email']
    if 'avatar' in data:
        user['avatar'] = data['avatar']
    if 'profile' in data:
        if 'profile' not in user:
            user['profile'] = {}
        user['profile'].update(data['profile'])
    
    save_users(users)
    
    # 返回更新后的用户信息（移除敏感信息）
    updated_user = user.copy()
    updated_user.pop('password_hash', None)
    
    return jsonify(updated_user)

@app.route('/api/user/plan', methods=['GET'])
@require_auth
def get_user_plan():
    """
    获取用户的健身计划（需要认证）
    
    Headers:
        - Authorization: Bearer {token}
    
    Returns:
        JSON: 用户的健身计划
    """
    plans = load_plans()
    user_id = request.user_id
    
    if user_id in plans:
        return jsonify(plans[user_id])
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
    plans = load_plans()
    user_id = request.user_id
    
    if user_id not in plans:
        plans[user_id] = {
            "daily_goals": {},
            "weekly_goals": {},
            "created_at": datetime.now().isoformat()
        }
    
    plan = plans[user_id]
    
    # 更新每日目标
    if 'daily_goals' in data:
        if 'daily_goals' not in plan:
            plan['daily_goals'] = {}
        plan['daily_goals'].update(data['daily_goals'])
    
    # 更新每周目标
    if 'weekly_goals' in data:
        if 'weekly_goals' not in plan:
            plan['weekly_goals'] = {}
        plan['weekly_goals'].update(data['weekly_goals'])
    
    plan['updated_at'] = datetime.now().isoformat()
    
    save_plans(plans)
    
    return jsonify(plan)

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
    users = load_users()
    user_id = request.user_id
    
    if user_id not in users:
        return jsonify({"error": "用户不存在"}), 404
    
    user = users[user_id]
    profile = user.get('profile', {})
    
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