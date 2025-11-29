#!/usr/bin/env python3
"""
FitnessAI 集成测试脚本
测试前后端完整功能集成
"""

import requests
import json
import time
from pose_analyzer import create_analyzer

def test_backend_api():
    """测试后端API功能"""
    base_url = "http://localhost:8000"
    
    print("🧪 开始后端API测试...")
    
    # 1. 测试API状态
    try:
        response = requests.get(f"{base_url}/api")
        print(f"✅ API状态: {response.json()['status']}")
    except Exception as e:
        print(f"❌ API状态测试失败: {e}")
        return False
    
    # 2. 测试运动类型获取
    try:
        response = requests.get(f"{base_url}/api/exercises")
        exercises = response.json()
        print(f"✅ 获取到 {len(exercises)} 种运动类型")
    except Exception as e:
        print(f"❌ 运动类型获取失败: {e}")
        return False
    
    # 3. 测试会话管理
    try:
        # 开始会话
        session_data = {
            "exercise_type": "squat",
            "user_id": "test_user"
        }
        response = requests.post(f"{base_url}/api/session/start", 
                               json=session_data)
        session_info = response.json()
        session_id = session_info['session_id']
        print(f"✅ 会话创建成功: {session_id}")
        
        # 提交运动数据
        exercise_data = {
            "pose_data": {"test": "data"},
            "is_correct": True,
            "score": 85,
            "feedback": "测试反馈"
        }
        response = requests.post(f"{base_url}/api/session/{session_id}/data",
                               json=exercise_data)
        print("✅ 运动数据提交成功")
        
        # 结束会话
        response = requests.post(f"{base_url}/api/session/{session_id}/end")
        summary = response.json()
        print(f"✅ 会话结束成功: {summary['summary']}")
        
    except Exception as e:
        print(f"❌ 会话管理测试失败: {e}")
        return False
    
    return True

def test_pose_analyzer():
    """测试姿态分析器"""
    print("\n🧪 开始姿态分析器测试...")
    
    # 模拟MediaPipe姿态数据
    mock_landmarks = []
    for i in range(33):  # MediaPipe有33个关键点
        mock_landmarks.append({
            'x': 0.5 + (i * 0.01),  # 模拟坐标
            'y': 0.5 + (i * 0.01),
            'z': 0.0,
            'visibility': 0.9
        })
    
    # 测试深蹲分析器
    try:
        squat_analyzer = create_analyzer('squat')
        result = squat_analyzer.analyze(mock_landmarks)
        print(f"✅ 深蹲分析器测试: {result['feedback']}")
    except Exception as e:
        print(f"❌ 深蹲分析器测试失败: {e}")
        return False
    
    # 测试俯卧撑分析器
    try:
        pushup_analyzer = create_analyzer('pushup')
        result = pushup_analyzer.analyze(mock_landmarks)
        print(f"✅ 俯卧撑分析器测试: {result['feedback']}")
    except Exception as e:
        print(f"❌ 俯卧撑分析器测试失败: {e}")
        return False
    
    return True

def test_pose_analysis_api():
    """测试姿态分析API"""
    print("\n🧪 开始姿态分析API测试...")
    
    base_url = "http://localhost:8000"
    
    # 模拟MediaPipe姿态数据
    mock_landmarks = []
    for i in range(33):
        mock_landmarks.append({
            'x': 0.5,
            'y': 0.5,
            'z': 0.0,
            'visibility': 0.9
        })
    
    try:
        analysis_data = {
            "pose_landmarks": mock_landmarks,
            "exercise_type": "squat"
        }
        
        response = requests.post(f"{base_url}/api/analytics/pose",
                               json=analysis_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 姿态分析API测试成功: {result['feedback']}")
            print(f"   得分: {result['score']}, 正确性: {result['is_correct']}")
            return True
        else:
            print(f"❌ 姿态分析API测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 姿态分析API测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 FitnessAI 集成测试开始")
    print("=" * 50)
    
    # 检查后端是否运行
    try:
        response = requests.get("http://localhost:8000/api", timeout=5)
        if response.status_code != 200:
            print("❌ 后端服务未运行，请先启动后端")
            return
    except Exception:
        print("❌ 无法连接到后端服务，请确保后端在运行")
        return
    
    all_tests_passed = True
    
    # 运行各项测试
    if not test_backend_api():
        all_tests_passed = False
    
    if not test_pose_analyzer():
        all_tests_passed = False
    
    if not test_pose_analysis_api():
        all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 所有测试通过！系统集成成功")
        print("\n📋 下一步:")
        print("1. 启动前端: cd frontend && npm start")
        print("2. 访问: http://localhost:3000")
        print("3. 授权摄像头权限")
        print("4. 选择运动类型并开始检测")
    else:
        print("❌ 部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main() 