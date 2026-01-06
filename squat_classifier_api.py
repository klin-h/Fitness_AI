"""
深蹲分类器便捷API接口
提供简化的函数接口，方便快速使用
"""

import numpy as np
from typing import Tuple, Dict, Union, List, Optional
from squat_classifier import SquatClassifier, extract_squat_features

# 全局分类器实例
_classifier: Optional[SquatClassifier] = None


def initialize_classifier(model_path: Optional[str] = None):
    """
    初始化分类器（全局单例）
    
    Args:
        model_path: 模型文件路径（可选，如果为None则创建新模型）
    """
    global _classifier
    
    if model_path:
        try:
            _classifier = SquatClassifier(model_path=model_path)
            print(f"[INFO] 已加载模型: {model_path}")
        except Exception as e:
            print(f"[WARN] 加载模型失败: {e}")
            print("[INFO] 使用未训练的模型")
            _classifier = SquatClassifier()
    else:
        _classifier = SquatClassifier()
        print("[INFO] 使用未训练的模型（需要先训练）")


def predict_squat_state(landmarks: Union[List, np.ndarray]) -> Tuple[int, float, Dict]:
    """
    预测深蹲状态（便捷接口）
    
    Args:
        landmarks: MediaPipe骨骼点数据，支持多种格式：
            - 33x4的numpy数组
            - 展平的列表（132维）
            - 嵌套列表（33×4）
            - MediaPipe landmark对象列表
    
    Returns:
        Tuple[int, float, Dict]:
            - 预测的状态 (0: 站直, 1: 半蹲, 2: 完全蹲下)
            - 置信度 (0-1)
            - 详细信息字典
    """
    global _classifier
    
    if _classifier is None:
        initialize_classifier()
    
    # 预测
    state, confidence, probabilities = _classifier.predict(landmarks)
    
    # 提取特征（用于返回）
    features = extract_squat_features(landmarks, include_raw_coords=False)
    
    # 构建详细信息
    state_names = {0: "站直", 1: "半蹲", 2: "完全蹲下"}
    feature_names = [
        "左膝盖角度", "右膝盖角度", "左髋部角度", "右髋部角度",
        "髋关节垂直高度", "肩膀垂直高度", "左膝盖水平偏移", "右膝盖水平偏移"
    ]
    
    details = {
        'state': state,
        'state_name': state_names.get(state, f'状态{state}'),
        'confidence': confidence,
        'probabilities': {
            '站直': float(probabilities[0]),
            '半蹲': float(probabilities[1]) if len(probabilities) > 1 else 0.0,
            '完全蹲下': float(probabilities[2]) if len(probabilities) > 2 else 0.0
        },
        'features': {
            name: float(value) for name, value in zip(feature_names, features)
        }
    }
    
    return state, confidence, details


def predict_squat_state_from_mediapipe_results(results) -> Tuple[int, float, Dict]:
    """
    从MediaPipe结果对象直接预测深蹲状态
    
    Args:
        results: MediaPipe Pose处理结果对象（results.pose_landmarks）
    
    Returns:
        Tuple[int, float, Dict]: 同 predict_squat_state
    """
    if results.pose_landmarks is None:
        raise ValueError("MediaPipe结果中未检测到人体姿态")
    
    # 转换为列表格式
    landmarks = results.pose_landmarks.landmark
    
    return predict_squat_state(landmarks)


def get_classifier() -> Optional[SquatClassifier]:
    """
    获取全局分类器实例
    
    Returns:
        SquatClassifier实例，如果未初始化则返回None
    """
    return _classifier


def reset_classifier():
    """重置全局分类器实例"""
    global _classifier
    _classifier = None

