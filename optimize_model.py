"""
模型优化方案集合
包含多种优化策略，可以逐步尝试
"""

import numpy as np
from typing import List, Tuple, Optional
from squat_classifier import extract_squat_features, calculate_angle, MediaPipeIndices


def extract_enhanced_features(landmarks, include_raw_coords: bool = True) -> np.ndarray:
    """
    增强特征提取 - 添加更多区分性特征
    
    新增特征：
    1. 膝盖弯曲速度（如果有时序数据）
    2. 身体重心位置
    3. 大腿与小腿的角度比
    4. 髋部与膝盖的相对高度差
    5. 左右腿对称性指标
    6. 身体倾斜角度
    """
    # 先提取基础特征
    base_features = extract_squat_features(landmarks, include_raw_coords=False)
    
    # 转换为numpy数组格式
    if hasattr(landmarks[0], 'x'):
        points = np.array([[lm.x, lm.y, lm.z, getattr(lm, 'visibility', 1.0)] 
                          for lm in landmarks])
    elif isinstance(landmarks, np.ndarray):
        if landmarks.ndim == 1:
            points = landmarks.reshape(33, 4)
        else:
            points = landmarks
    else:
        landmarks_array = np.array(landmarks, dtype=np.float32)
        if landmarks_array.ndim == 1:
            points = landmarks_array.reshape(33, 4)
        else:
            points = landmarks_array
    
    idx = MediaPipeIndices
    
    def get_point(index: int) -> np.ndarray:
        point = points[index]
        if len(point) >= 2:
            return np.array([point[0], point[1], point[2] if len(point) > 2 else 0.0])
        return np.array([point[0], point[1], 0.0])
    
    left_shoulder = get_point(idx.LEFT_SHOULDER)
    right_shoulder = get_point(idx.RIGHT_SHOULDER)
    left_hip = get_point(idx.LEFT_HIP)
    right_hip = get_point(idx.RIGHT_HIP)
    left_knee = get_point(idx.LEFT_KNEE)
    right_knee = get_point(idx.RIGHT_KNEE)
    left_ankle = get_point(idx.LEFT_ANKLE)
    right_ankle = get_point(idx.RIGHT_ANKLE)
    
    enhanced_features = []
    
    # 1. 身体重心位置（基于髋部和肩膀）
    center_hip_x = (left_hip[0] + right_hip[0]) / 2.0
    center_hip_y = (left_hip[1] + right_hip[1]) / 2.0
    center_ankle_x = (left_ankle[0] + right_ankle[0]) / 2.0
    center_ankle_y = (left_ankle[1] + right_ankle[1]) / 2.0
    
    # 重心相对于脚踝的水平偏移
    center_of_mass_x = center_hip_x - center_ankle_x
    enhanced_features.append(center_of_mass_x)
    
    # 2. 左右腿对称性（膝盖角度差异）
    left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
    right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
    knee_angle_asymmetry = abs(left_knee_angle - right_knee_angle)
    enhanced_features.append(knee_angle_asymmetry)
    
    # 3. 大腿与小腿的长度比（归一化）
    left_thigh_length = np.linalg.norm(left_hip[:2] - left_knee[:2])
    left_shank_length = np.linalg.norm(left_knee[:2] - left_ankle[:2])
    right_thigh_length = np.linalg.norm(right_hip[:2] - right_knee[:2])
    right_shank_length = np.linalg.norm(right_knee[:2] - right_ankle[:2])
    
    if left_shank_length > 0 and right_shank_length > 0:
        left_ratio = left_thigh_length / left_shank_length
        right_ratio = right_thigh_length / right_shank_length
        enhanced_features.append(left_ratio)
        enhanced_features.append(right_ratio)
    else:
        enhanced_features.extend([1.0, 1.0])  # 默认值
    
    # 4. 髋部与膝盖的相对高度差
    left_hip_knee_height_diff = left_hip[1] - left_knee[1]
    right_hip_knee_height_diff = right_hip[1] - right_knee[1]
    enhanced_features.append(left_hip_knee_height_diff)
    enhanced_features.append(right_hip_knee_height_diff)
    
    # 5. 身体倾斜角度（肩膀连线与水平线的角度）
    shoulder_angle = np.arctan2(
        right_shoulder[1] - left_shoulder[1],
        right_shoulder[0] - left_shoulder[0]
    )
    enhanced_features.append(np.degrees(shoulder_angle))
    
    # 6. 膝盖相对于髋部的水平偏移
    left_knee_hip_offset = left_knee[0] - left_hip[0]
    right_knee_hip_offset = right_knee[0] - right_hip[0]
    enhanced_features.append(left_knee_hip_offset)
    enhanced_features.append(right_knee_hip_offset)
    
    # 组合所有特征
    enhanced_features = np.array(enhanced_features, dtype=np.float32)
    
    if include_raw_coords:
        # 添加原始坐标特征
        raw_coords = [
            left_shoulder[0], left_shoulder[1],
            right_shoulder[0], right_shoulder[1],
            left_hip[0], left_hip[1],
            right_hip[0], right_hip[1],
            left_knee[0], left_knee[1],
            right_knee[0], right_knee[1],
            left_ankle[0], left_ankle[1],
            right_ankle[0], right_ankle[1]
        ]
        all_features = np.concatenate([base_features, enhanced_features, raw_coords])
    else:
        all_features = np.concatenate([base_features, enhanced_features])
    
    return all_features


def create_ensemble_models():
    """
    创建集成学习方案
    可以训练多个不同架构的模型，然后投票或平均
    """
    model_configs = [
        {
            'name': 'deep_model',
            'hidden_units': [256, 128, 64, 32],
            'dropout_rates': [0.5, 0.4, 0.3, 0.2],
            'learning_rate': 0.001
        },
        {
            'name': 'wide_model',
            'hidden_units': [128, 128, 64],
            'dropout_rates': [0.4, 0.3, 0.2],
            'learning_rate': 0.0005
        },
        {
            'name': 'regularized_model',
            'hidden_units': [96, 64, 32],
            'dropout_rates': [0.5, 0.4, 0.3],
            'learning_rate': 0.001
        }
    ]
    return model_configs


def data_augmentation(X, y, noise_level: float = 0.01):
    """
    数据增强：添加轻微噪声
    """
    X_augmented = X.copy()
    noise = np.random.normal(0, noise_level, X.shape)
    X_augmented = X_augmented + noise
    return np.vstack([X, X_augmented]), np.hstack([y, y])


def smote_oversampling(X, y, target_samples: int = None):
    """
    使用SMOTE进行过采样（处理类别不平衡）
    需要安装: pip install imbalanced-learn
    """
    try:
        from imblearn.over_sampling import SMOTE
        
        if target_samples is None:
            # 自动确定目标样本数（使用最多类别的样本数）
            unique, counts = np.unique(y, return_counts=True)
            target_samples = counts.max()
        
        smote = SMOTE(random_state=42, k_neighbors=3)
        X_resampled, y_resampled = smote.fit_resample(X, y)
        return X_resampled, y_resampled
    except ImportError:
        print("警告: 未安装 imbalanced-learn，跳过SMOTE")
        return X, y


# 优化建议文档
OPTIMIZATION_GUIDE = """
# 模型优化指南

## 当前状态
- 准确率: 77.89%
- 主要问题: 半蹲和完全蹲下仍有混淆

## 优化方案（按优先级）

### 1. 特征工程（推荐优先尝试）
- 使用 extract_enhanced_features() 添加更多特征
- 新增特征包括：身体重心、对称性、长度比等
- 预期提升: +2-5%

### 2. 数据增强
- 添加轻微噪声增加训练样本
- 使用SMOTE处理类别不平衡
- 预期提升: +1-3%

### 3. 模型架构优化
- 尝试更深的网络（4-5层）
- 调整隐藏层大小和Dropout率
- 预期提升: +1-3%

### 4. 集成学习
- 训练多个不同架构的模型
- 使用投票或平均预测
- 预期提升: +2-4%

### 5. 超参数调优
- 使用GridSearch或RandomSearch
- 优化学习率、batch_size、正则化参数
- 预期提升: +1-2%

### 6. 数据质量改进
- 清理异常数据
- 增加边界样本（半蹲和完全蹲下的过渡状态）
- 预期提升: +2-5%

## 实施步骤

1. 先尝试特征工程（最简单，效果明显）
2. 然后尝试数据增强
3. 最后考虑集成学习

每个优化后都要重新评估，确保改进有效。
"""

if __name__ == "__main__":
    print(OPTIMIZATION_GUIDE)




