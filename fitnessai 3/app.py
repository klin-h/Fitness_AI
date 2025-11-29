from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import json
from datetime import datetime
import os

# 导入姿态分析器
from backend.pose_analyzer import create_analyzer

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)  # 允许跨域请求

# 数据存储（生产环境中应使用数据库）
exercise_data = {}
user_sessions = {}
# 存储每个会话的分析器实例
session_analyzers = {}

@app.route('/')
def index():
    """提供前端页面"""
    try:
        return send_file('frontend/build/index.html')
    except:
        return """
        <html>
        <head><title>FitnessAI</title></head>
        <body>
            <h1>🏃‍♀️ FitnessAI 健身助手</h1>
            <p>欢迎使用智能健身辅助系统！</p>
            <p>前端文件未找到，但后端API正常运行</p>
            <p><a href="/demo">查看演示页面</a></p>
        </body>
        </html>
        """

@app.route('/api')
def api_status():
    """API状态接口"""
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
        },
        {
            "id": "plank",
            "name": "平板支撑",
            "description": "核心稳定性训练的金标准",
            "difficulty": "medium",
            "target_muscles": ["核心", "肩部", "背部"],
            "instructions": [
                "俯卧支撑姿势",
                "前臂贴地，肘部在肩膀下方",
                "身体保持一条直线",
                "收紧核心肌群",
                "保持静止状态"
            ]
        },
        {
            "id": "jumping_jack",
            "name": "开合跳",
            "description": "全身有氧运动，提高心率",
            "difficulty": "easy",
            "target_muscles": ["全身", "心肺"],
            "instructions": [
                "双脚并拢站立",
                "跳起时双腿分开",
                "同时双臂上举过头",
                "跳回起始位置",
                "保持节奏连续进行"
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
    print(" 开始新11的锻炼会话")
    # 创建对应的姿态分析器
    try:
        analyzer = create_analyzer(exercise_type)
        session_analyzers[session_id] = analyzer
        print(f"✅ 为会话 {session_id} 创建了 {exercise_type} 分析器")
    except Exception as e:
        print(f"❌ 创建分析器失败: {e}")
        return jsonify({"error": "Failed to create analyzer"}), 500
    
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
    
    # 清理分析器
    if session_id in session_analyzers:
        del session_analyzers[session_id]
        print(f"✅ 清理了会话 {session_id} 的分析器")
    
    # 计算会话统计
    total_count = session['total_count']
    correct_count = session['correct_count']
    accuracy = correct_count / total_count if total_count > 0 else 0
    avg_score = sum([s['score'] for s in session['scores']]) / len(session['scores']) if session['scores'] else 0
    
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

@app.route('/api/session/<session_id>/reset', methods=['POST'])
def reset_session_counters(session_id):
    """
    重置会话中的计数器
    
    Path Parameters:
        - session_id: 会话ID
    
    Returns:
        JSON: 重置结果
    """
    if session_id not in user_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    # 重置会话中的计数
    session = user_sessions[session_id]
    session['total_count'] = 0
    session['correct_count'] = 0
    session['scores'] = []
    
    # 重置分析器中的计数
    if session_id in session_analyzers:
        analyzer = session_analyzers[session_id]
        # 根据不同的分析器类型重置计数
        if hasattr(analyzer, 'squat_count'):
            analyzer.squat_count = 0
        if hasattr(analyzer, 'pushup_count'):
            analyzer.pushup_count = 0
        if hasattr(analyzer, 'jump_count'):
            analyzer.jump_count = 0
        if hasattr(analyzer, 'plank_duration'):
            analyzer.plank_duration = 0
        print(f"✅ 重置了会话 {session_id} 的计数器")
    
    return jsonify({
        "message": "Session counters reset successfully",
        "session_id": session_id
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
    分析姿态数据
    
    Request Body:
        - pose_landmarks: MediaPipe姿态关键点数据
        - exercise_type: 运动类型
        - session_id: 会话ID（可选，用于获取对应的分析器）
    
    Returns:
        JSON: 分析结果
    """
    print("进入动作分析模块")
    try:
        data = request.get_json()
        pose_landmarks = data.get('pose_landmarks')
        exercise_type = data.get('exercise_type', 'squat')
        session_id = data.get('session_id')
        
        if not pose_landmarks:
            return jsonify({
                "error": "No pose landmarks provided",
                "is_correct": False,
                "score": 0,
                "feedback": "未检测到姿态数据"
            }), 400
        
        # 尝试从会话中获取分析器，如果没有则创建新的
        analyzer = None
        if session_id and session_id in session_analyzers:
            analyzer = session_analyzers[session_id]
        else:
            analyzer = create_analyzer(exercise_type)
        
        # 转换姿态数据格式
        formatted_landmarks = []
        for landmark in pose_landmarks:
            formatted_landmarks.append({
                'x': landmark.get('x', 0),
                'y': landmark.get('y', 0),
                'z': landmark.get('z', 0),
                'visibility': landmark.get('visibility', 1.0)
            })
        
        # 进行姿态分析
        analysis_result = analyzer.analyze(formatted_landmarks)
        
        # 添加运动类型信息
        analysis_result['exercise_type'] = exercise_type
        analysis_result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(analysis_result)
        
    except Exception as e:
        print(f"❌ 姿态分析错误: {e}")
        return jsonify({
            "error": f"Analysis failed: {str(e)}",
            "is_correct": False,
            "score": 0,
            "feedback": "分析过程中出现错误",
            "count": 0
        }), 500

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

@app.route('/demo')
def demo():
    """演示页面"""
    return """
    <html>
    <head>
        <title>FitnessAI Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
            .container { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; }
            .btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            .btn:hover { background: #45a049; }
            .status { background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin: 10px 0; }
            .exercise-card { background: rgba(255,255,255,0.2); padding: 20px; margin: 10px 0; border-radius: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏃‍♀️ FitnessAI 演示</h1>
            <p>智能健身辅助系统 - 基于AI的姿态识别健身指导</p>
            
            <div class="status">
                <h3>📊 系统状态</h3>
                <p>API状态: <span id="api-status">检查中...</span></p>
                <p>支持的运动: <span id="exercises">加载中...</span></p>
            </div>
            
            <div class="exercise-card">
                <h3>🎯 开始训练</h3>
                <button class="btn" onclick="startSession('squat')">开始深蹲训练</button>
                <button class="btn" onclick="startSession('pushup')">开始俯卧撑训练</button>
                <div id="session-info"></div>
            </div>
            
            <div class="exercise-card">
                <h3>💡 功能特色</h3>
                <ul>
                    <li>🎯 实时姿态识别 - 基于MediaPipe技术</li>
                    <li>📊 动作分析 - 智能判断动作标准性</li>
                    <li>🔢 自动计数 - 准确统计运动次数</li>
                    <li>💬 实时反馈 - 提供动作纠正建议</li>
                    <li>📈 数据统计 - 记录训练历史</li>
                </ul>
            </div>
        </div>
        
        <script>
            // 检查API状态
            fetch('/api')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('api-status').textContent = '✅ ' + data.status;
                })
                .catch(e => {
                    document.getElementById('api-status').textContent = '❌ 离线';
                });
            
            // 获取运动类型
            fetch('/api/exercises')
                .then(r => r.json())
                .then(data => {
                    const names = data.map(ex => ex.name).join(', ');
                    document.getElementById('exercises').textContent = names;
                })
                .catch(e => {
                    document.getElementById('exercises').textContent = '加载失败';
                });
            
            // 开始训练会话
            function startSession(exerciseType) {
                fetch('/api/session/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({exercise_type: exerciseType, user_id: 'demo_user'})
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('session-info').innerHTML = 
                        '<p>✅ 训练会话已开始!</p><p>会话ID: ' + data.session_id + '</p>';
                })
                .catch(e => {
                    document.getElementById('session-info').innerHTML = 
                        '<p>❌ 启动失败: ' + e.message + '</p>';
                });
            }
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    import multiprocessing
    # 设置multiprocessing启动方法，避免semaphore泄漏
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass  # 已经设置过了
    
    print("🚀 启动FitnessAI应用...")
    print("📱 访问: http://localhost:8000")
    print("🎯 演示页面: http://localhost:8000/demo")
    print("🔧 API状态: http://localhost:8000/api")
    
    # 使用更安全的启动配置
    app.run(
        debug=False,  # 关闭debug模式避免额外进程
        host='0.0.0.0', 
        port=8000,
        threaded=True,  # 使用线程而不是进程
        use_reloader=False  # 关闭自动重载
    ) 