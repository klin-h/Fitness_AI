"""
深蹲状态检测使用示例
演示如何使用特征提取后的分类器
"""

import numpy as np
from squat_classifier_api import predict_squat_state, initialize_classifier
from squat_classifier import extract_squat_features


def example_1_basic_usage():
    """示例1: 基本使用"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    
    # 初始化分类器
    try:
        initialize_classifier('squat_classifier_model.h5')
        print("[INFO] 分类器已初始化")
    except:
        print("[WARN] 模型文件不存在，将使用未训练的模型")
        initialize_classifier()
    
    # 准备33个骨骼点坐标（已归一化）
    # 格式1: 33x4的numpy数组
    landmarks = np.random.rand(33, 4).astype(np.float32)
    
    # 预测状态
    state, confidence, details = predict_squat_state(landmarks)
    
    print(f"\n预测结果:")
    print(f"  状态: {details['state_name']} (状态码: {details['state']})")
    print(f"  置信度: {confidence:.4f}")
    print(f"\n概率分布:")
    for state_name, prob in details['probabilities'].items():
        print(f"    {state_name}: {prob:.4f}")
    
    print(f"\n提取的特征:")
    feature_names = [
        "左膝盖角度", "右膝盖角度", "左髋部角度", "右髋部角度",
        "髋关节垂直高度", "肩膀垂直高度", "左膝盖水平偏移", "右膝盖水平偏移"
    ]
    for name, value in zip(feature_names, details['features'].values()):
        print(f"    {name}: {value:.4f}")


def example_2_different_input_formats():
    """示例2: 不同的输入格式"""
    print("\n" + "=" * 60)
    print("示例2: 不同的输入格式")
    print("=" * 60)
    
    initialize_classifier()
    
    # 格式1: 33x4的numpy数组
    landmarks_2d = np.random.rand(33, 4).astype(np.float32)
    state1, _, _ = predict_squat_state(landmarks_2d)
    print(f"格式1 (33x4数组): 状态={state1}")
    
    # 格式2: 展平的列表（132维）
    landmarks_flat = np.random.rand(132).tolist()
    state2, _, _ = predict_squat_state(landmarks_flat)
    print(f"格式2 (展平列表): 状态={state2}")
    
    # 格式3: 嵌套列表
    landmarks_nested = [[np.random.rand(), np.random.rand(), 
                         np.random.rand(), 1.0] for _ in range(33)]
    state3, _, _ = predict_squat_state(landmarks_nested)
    print(f"格式3 (嵌套列表): 状态={state3}")


def example_3_feature_extraction():
    """示例3: 单独提取特征"""
    print("\n" + "=" * 60)
    print("示例3: 单独提取特征")
    print("=" * 60)
    
    # 准备数据
    landmarks = np.random.rand(33, 4).astype(np.float32)
    
    # 提取特征
    features = extract_squat_features(landmarks)
    
    feature_names = [
        "左膝盖角度", "右膝盖角度", "左髋部角度", "右髋部角度",
        "髋关节垂直高度", "肩膀垂直高度", "左膝盖水平偏移", "右膝盖水平偏移"
    ]
    
    print("提取的8维特征:")
    for name, value in zip(feature_names, features):
        print(f"  {name}: {value:.4f}")
    
    print(f"\n特征向量形状: {features.shape}")
    print(f"特征向量: {features}")


def example_4_simulate_states():
    """示例4: 模拟不同深蹲状态的特征"""
    print("\n" + "=" * 60)
    print("示例4: 模拟不同深蹲状态的特征")
    print("=" * 60)
    
    # MediaPipe关键点索引
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    
    # 模拟站直状态（膝盖角度接近180度）
    print("\n1. 站直状态（膝盖角度接近180°）:")
    landmarks_standing = np.random.rand(33, 4).astype(np.float32)
    # 设置关键点使膝盖角度接近180度
    landmarks_standing[LEFT_HIP] = [0.5, 0.4, 0.0, 1.0]  # 髋部
    landmarks_standing[LEFT_KNEE] = [0.5, 0.5, 0.0, 1.0]  # 膝盖
    landmarks_standing[LEFT_ANKLE] = [0.5, 0.6, 0.0, 1.0]  # 脚踝（垂直）
    
    features_standing = extract_squat_features(landmarks_standing)
    print(f"  左膝盖角度: {features_standing[0]:.2f}°")
    print(f"  右膝盖角度: {features_standing[1]:.2f}°")
    print(f"  髋关节垂直高度: {features_standing[4]:.4f}")
    
    # 模拟完全蹲下状态（膝盖角度较小）
    print("\n2. 完全蹲下状态（膝盖角度<100°）:")
    landmarks_squat = np.random.rand(33, 4).astype(np.float32)
    # 设置关键点使膝盖角度较小
    landmarks_squat[LEFT_HIP] = [0.5, 0.5, 0.0, 1.0]  # 髋部下降
    landmarks_squat[LEFT_KNEE] = [0.5, 0.55, 0.0, 1.0]  # 膝盖弯曲
    landmarks_squat[LEFT_ANKLE] = [0.5, 0.6, 0.0, 1.0]  # 脚踝
    
    features_squat = extract_squat_features(landmarks_squat)
    print(f"  左膝盖角度: {features_squat[0]:.2f}°")
    print(f"  右膝盖角度: {features_squat[1]:.2f}°")
    print(f"  髋关节垂直高度: {features_squat[4]:.4f}")


if __name__ == "__main__":
    # 运行所有示例
    example_1_basic_usage()
    example_2_different_input_formats()
    example_3_feature_extraction()
    example_4_simulate_states()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)




