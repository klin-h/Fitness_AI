"""
深蹲状态分类器 - 使用深度学习模型
基于MediaPipe的33个骨骼点坐标，提取特征后分类深蹲状态：
- 0: 站直
- 1: 半蹲
- 2: 完全蹲下

特征提取：
- 4个角度：左/右膝盖角度、左/右髋部角度
- 4个归一化坐标：髋关节垂直高度、肩膀垂直高度、左/右膝盖水平偏移
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from typing import List, Tuple, Optional, Union
import os
import math


# MediaPipe Pose 关键点索引
class MediaPipeIndices:
    """MediaPipe Pose 33个关键点的索引"""
    # 面部 (0-10) - 丢弃
    # 肩膀
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    # 手臂 (13-16) - 丢弃
    # 手指 (17-22) - 丢弃
    # 髋部
    LEFT_HIP = 23
    RIGHT_HIP = 24
    # 膝盖
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    # 脚踝
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    # 脚部 (29-32) - 可选


def calculate_angle(point1: np.ndarray, point2: np.ndarray, point3: np.ndarray) -> float:
    """
    计算三个点之间的角度（以point2为顶点）
    
    Args:
        point1, point2, point3: 包含x, y坐标的数组
    
    Returns:
        float: 角度值（度），范围0-180
    """
    # 向量1: point2 -> point1
    vec1 = point1[:2] - point2[:2]
    # 向量2: point2 -> point3
    vec2 = point3[:2] - point2[:2]
    
    # 计算角度
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 180.0  # 如果向量长度为0，返回180度（默认值）
    
    cos_angle = np.clip(dot_product / (norm1 * norm2), -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg


def extract_squat_features(landmarks: Union[List, np.ndarray], include_raw_coords: bool = True) -> np.ndarray:
    """
    从33个MediaPipe骨骼点中提取深蹲相关特征
    
    提取的特征：
    基础特征（8个）：
    1. 左膝盖角度 (Left Knee Angle): 左髋 - 左膝 - 左踝
    2. 右膝盖角度 (Right Knee Angle): 右髋 - 右膝 - 右踝
    3. 左髋部角度 (Left Hip Angle): 左肩 - 左髋 - 左膝
    4. 右髋部角度 (Right Hip Angle): 右肩 - 右髋 - 右膝
    5. 髋关节垂直高度: (左髋Y + 右髋Y) / 2 - (左踝Y + 右踝Y) / 2
    6. 肩膀垂直高度: (左肩Y + 右肩Y) / 2 - (左踝Y + 右踝Y) / 2
    7. 左膝盖水平偏移: 左膝X - 左踝X
    8. 右膝盖水平偏移: 右膝X - 右踝X
    
    原始坐标特征（16个，如果include_raw_coords=True）：
    9-10. 左肩坐标 (x, y)
    11-12. 右肩坐标 (x, y)
    13-14. 左髋坐标 (x, y)
    15-16. 右髋坐标 (x, y)
    17-18. 左膝坐标 (x, y)
    19-20. 右膝坐标 (x, y)
    21-22. 左踝坐标 (x, y)
    23-24. 右踝坐标 (x, y)
    
    Args:
        landmarks: MediaPipe骨骼点列表或数组
                  格式1: MediaPipe landmark对象列表
                  格式2: 展平的列表 [x0, y0, z0, v0, x1, y1, z1, v1, ..., x32, y32, z32, v32]
                  格式3: 嵌套列表 [[x0, y0, z0, v0], [x1, y1, z1, v1], ..., [x32, y32, z32, v32]]
        include_raw_coords: 是否包含关键点原始坐标特征（默认True）
    
    Returns:
        np.ndarray: 特征向量（8维或24维，取决于include_raw_coords）
    """
    # 转换为numpy数组格式
    if hasattr(landmarks[0], 'x'):
        # MediaPipe landmark对象列表
        points = np.array([[lm.x, lm.y, lm.z, getattr(lm, 'visibility', 1.0)] 
                          for lm in landmarks])
    elif isinstance(landmarks, np.ndarray):
        if landmarks.ndim == 1:
            # 展平的数组，需要reshape
            points = landmarks.reshape(33, 4)
        else:
            points = landmarks
    else:
        # Python列表
        landmarks_array = np.array(landmarks, dtype=np.float32)
        if landmarks_array.ndim == 1:
            # 展平的列表
            points = landmarks_array.reshape(33, 4)
        else:
            # 嵌套列表
            points = landmarks_array
    
    # 确保有33个点，每个点4个值
    if points.shape[0] != 33 or points.shape[1] < 2:
        raise ValueError(
            f"输入格式错误：期望33个点，每个点至少2个值(x, y)，"
            f"得到形状: {points.shape}"
        )
    
    # 提取关键点坐标（只使用x, y）
    idx = MediaPipeIndices
    
    # 获取关键点（如果z或visibility不存在，使用默认值）
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
    
    # 1. 计算角度特征（4个）
    left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
    right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
    left_hip_angle = calculate_angle(left_shoulder, left_hip, left_knee)
    right_hip_angle = calculate_angle(right_shoulder, right_hip, right_knee)
    
    # 2. 计算归一化坐标特征（4个）
    # 髋关节垂直高度（相对于脚踝）
    avg_hip_y = (left_hip[1] + right_hip[1]) / 2.0
    avg_ankle_y = (left_ankle[1] + right_ankle[1]) / 2.0
    hip_vertical_height = avg_hip_y - avg_ankle_y
    
    # 肩膀垂直高度（相对于脚踝）
    avg_shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2.0
    shoulder_vertical_height = avg_shoulder_y - avg_ankle_y
    
    # 膝盖水平偏移（相对于脚踝）
    left_knee_horizontal_offset = left_knee[0] - left_ankle[0]
    right_knee_horizontal_offset = right_knee[0] - right_ankle[0]
    
    # 组合基础特征向量
    base_features = [
        left_knee_angle,              # 特征0: 左膝盖角度
        right_knee_angle,              # 特征1: 右膝盖角度
        left_hip_angle,                # 特征2: 左髋部角度
        right_hip_angle,               # 特征3: 右髋部角度
        hip_vertical_height,           # 特征4: 髋关节垂直高度
        shoulder_vertical_height,      # 特征5: 肩膀垂直高度
        left_knee_horizontal_offset,  # 特征6: 左膝盖水平偏移
        right_knee_horizontal_offset  # 特征7: 右膝盖水平偏移
    ]
    
    # 如果包含原始坐标，添加关键点的x, y坐标
    if include_raw_coords:
        raw_coords = [
            left_shoulder[0],   # 特征8: 左肩X
            left_shoulder[1],   # 特征9: 左肩Y
            right_shoulder[0],  # 特征10: 右肩X
            right_shoulder[1],  # 特征11: 右肩Y
            left_hip[0],        # 特征12: 左髋X
            left_hip[1],        # 特征13: 左髋Y
            right_hip[0],       # 特征14: 右髋X
            right_hip[1],       # 特征15: 右髋Y
            left_knee[0],       # 特征16: 左膝X
            left_knee[1],       # 特征17: 左膝Y
            right_knee[0],      # 特征18: 右膝X
            right_knee[1],      # 特征19: 右膝Y
            left_ankle[0],      # 特征20: 左踝X
            left_ankle[1],      # 特征21: 左踝Y
            right_ankle[0],     # 特征22: 右踝X
            right_ankle[1]      # 特征23: 右踝Y
        ]
        features = np.array(base_features + raw_coords, dtype=np.float32)
    else:
        features = np.array(base_features, dtype=np.float32)
    
    return features


class SquatClassifier:
    """深蹲状态分类器"""
    
    def __init__(self, model_path: Optional[str] = None, num_classes: int = None, input_dim: int = None):
        """
        初始化分类器
        
        Args:
            model_path: 预训练模型路径（可选）
            num_classes: 类别数量（2或3，如果为None则从模型推断或默认为3）
            input_dim: 输入特征维度（如果为None，则从模型推断或默认为24）
        """
        self.model = None
        # 如果提供了模型路径，加载模型后会更新这些值
        self.input_dim = input_dim if input_dim is not None else 24  # 默认24维（8基础+16坐标）
        self.num_classes = num_classes if num_classes is not None else 3  # 默认3分类
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        elif input_dim is not None:
            # 如果提供了input_dim，直接构建模型
            self.build_model()
        else:
            # 如果没有提供任何参数，默认构建24维模型
            self.build_model()
    
    def build_model(self, hidden_units: list = None, dropout_rates: list = None, learning_rate: float = 0.001):
        """
        构建深度学习模型（优化版本）
        
        Args:
            hidden_units: 隐藏层单元数列表，默认[128, 64, 32]
            dropout_rates: Dropout比率列表，默认[0.4, 0.3, 0.2]
            learning_rate: 学习率，默认0.001
        """
        if hidden_units is None:
            hidden_units = [128, 64, 32]  # 增加模型容量
        if dropout_rates is None:
            dropout_rates = [0.4, 0.3, 0.2]  # 更强的正则化
        
        layers_list = [layers.Input(shape=(self.input_dim,))]
        
        # 构建隐藏层
        for i, (units, dropout_rate) in enumerate(zip(hidden_units, dropout_rates)):
            layers_list.append(layers.Dense(units, activation='relu'))
            layers_list.append(layers.BatchNormalization())
            layers_list.append(layers.Dropout(dropout_rate))
        
        # 输出层
        layers_list.append(layers.Dense(self.num_classes, activation='softmax'))
        
        model = keras.Sequential(layers_list)
        
        # 编译模型（使用学习率调度）
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        self.model = model
        return model
    
    def preprocess_landmarks(self, landmarks: Union[List, np.ndarray]) -> np.ndarray:
        """
        预处理骨骼点数据，提取特征
        
        Args:
            landmarks: MediaPipe骨骼点列表或数组
        
        Returns:
            np.ndarray: 预处理后的特征向量，添加了batch维度
        """
        # 根据模型的input_dim决定是否包含原始坐标
        include_raw_coords = (self.input_dim >= 24)
        features = extract_squat_features(landmarks, include_raw_coords=include_raw_coords)
        return features.reshape(1, -1)  # 添加batch维度
    
    def predict(self, landmarks: Union[List, np.ndarray]) -> Tuple[int, float, np.ndarray]:
        """
        预测深蹲状态
        
        Args:
            landmarks: MediaPipe骨骼点列表或数组
        
        Returns:
            Tuple[int, float, np.ndarray]: 
                - 预测的状态 (0: 站直, 1: 半蹲, 2: 完全蹲下)
                - 置信度 (0-1)
                - 所有类别的概率分布
        """
        if self.model is None:
            raise ValueError("模型未初始化，请先加载或训练模型")
        
        # 预处理输入（提取特征）
        features = self.preprocess_landmarks(landmarks)
        
        # 预测
        predictions = self.model.predict(features, verbose=0)
        probabilities = predictions[0]
        
        # 获取预测类别和置信度
        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])
        
        return predicted_class, confidence, probabilities
    
    def predict_batch(self, landmarks_list: List[Union[List, np.ndarray]]) -> List[Tuple[int, float]]:
        """
        批量预测
        
        Args:
            landmarks_list: 多个骨骼点列表的列表
        
        Returns:
            List[Tuple[int, float]]: 每个输入的预测结果 (状态, 置信度)
        """
        if self.model is None:
            raise ValueError("模型未初始化，请先加载或训练模型")
        
        # 预处理所有输入
        features_list = []
        for landmarks in landmarks_list:
            features = extract_squat_features(landmarks)
            features_list.append(features)
        
        features_array = np.array(features_list)
        
        # 批量预测
        predictions = self.model.predict(features_array, verbose=0)
        
        # 处理结果
        results = []
        for prob in predictions:
            predicted_class = int(np.argmax(prob))
            confidence = float(prob[predicted_class])
            results.append((predicted_class, confidence))
        
        return results
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray = None, y_val: np.ndarray = None,
              epochs: int = 100, batch_size: int = 32,
              validation_split: float = 0.2,
              class_weight: dict = None,
              use_early_stopping: bool = True,
              patience: int = 15):
        """
        训练模型（优化版本，支持早停和类别权重）
        
        Args:
            X_train: 训练特征 - 已经提取好的特征
            y_train: 训练标签 - 值为0, 1, 或2（2分类时只有0和1）
            X_val: 验证特征（可选）
            y_val: 验证标签（可选）
            epochs: 训练轮数
            batch_size: 批次大小
            validation_split: 如果没有提供验证集，使用训练集的比例作为验证集
            class_weight: 类别权重字典，例如 {0: 2.0, 1: 0.5} 或 {0: 2.0, 1: 0.5, 2: 1.0}
            use_early_stopping: 是否使用早停（默认True）
            patience: 早停的耐心值（默认15）
        """
        # 自动检测类别数量
        num_classes_detected = len(np.unique(y_train))
        
        # 如果模型未构建，或类别数量不匹配，重新构建模型
        if self.model is None or self.num_classes != num_classes_detected:
            print(f"[INFO] 检测到 {num_classes_detected} 个类别，{'重新' if self.model is not None else ''}构建模型...")
            self.num_classes = num_classes_detected
            self.build_model()
        
        # 验证输入维度
        if X_train.shape[1] != self.input_dim:
            raise ValueError(
                f"训练数据维度错误：期望 {self.input_dim} 维特征，"
                f"得到 {X_train.shape[1]} 维。请使用 extract_squat_features() 提取特征。"
            )
        
        # 准备验证数据
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
            validation_split = None
        else:
            validation_split = validation_split
        
        # 设置回调函数
        callbacks = []
        
        # 早停回调
        if use_early_stopping and validation_data is not None:
            early_stopping = keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=patience,
                restore_best_weights=True,
                verbose=1
            )
            callbacks.append(early_stopping)
        
        # 学习率调度
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        )
        callbacks.append(reduce_lr)
        
        # 训练模型
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            validation_split=validation_split,
            class_weight=class_weight,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def save_model(self, model_path: str):
        """保存模型"""
        if self.model is None:
            raise ValueError("模型未初始化")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(model_path) if os.path.dirname(model_path) else '.', exist_ok=True)
        
        # 保存Keras模型
        self.model.save(model_path)
        print(f"[INFO] 模型已保存到: {model_path}")
    
    def load_model(self, model_path: str):
        """加载模型"""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        self.model = keras.models.load_model(model_path)
        # 从模型形状获取输入维度和类别数量
        if self.model is not None:
            if hasattr(self.model, 'input_shape') and self.model.input_shape:
                # input_shape格式: (None, input_dim)
                self.input_dim = self.model.input_shape[-1]
            if hasattr(self.model, 'output_shape') and self.model.output_shape:
                self.num_classes = self.model.output_shape[-1]
        print(f"[INFO] 模型已从 {model_path} 加载（{self.num_classes}分类，输入维度: {self.input_dim}）")
    
    def get_model_summary(self):
        """获取模型摘要"""
        if self.model is None:
            return "模型未初始化"
        self.model.summary()


def load_data_from_csv(csv_path: str, label_column: str = 'label', include_raw_coords: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """
    从CSV文件加载训练数据并提取特征
    
    CSV格式应该包含：
    - 33个骨骼点的坐标（每点4个值：x, y, z, visibility）
    - 标签列（label_column），值为0, 1, 或2
    
    Args:
        csv_path: CSV文件路径
        label_column: 标签列名
        include_raw_coords: 是否包含关键点原始坐标特征（默认True）
    
    Returns:
        Tuple[np.ndarray, np.ndarray]: (特征, 标签) - 特征维度取决于include_raw_coords
    """
    import pandas as pd
    
    df = pd.read_csv(csv_path)
    
    # 提取特征列（所有包含_x, _y, _z, _visibility的列）
    feature_cols = []
    for i in range(33):
        feature_cols.extend([f"{i}_x", f"{i}_y", f"{i}_z", f"{i}_visibility"])
    
    # 检查列是否存在
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV文件缺少必要的列: {missing_cols[:5]}...")
    
    # 提取原始坐标数据
    raw_data = df[feature_cols].values.astype(np.float32)
    
    # 提取特征
    features_list = []
    for row in raw_data:
        # 将每行reshape为33x4的数组
        landmarks = row.reshape(33, 4)
        features = extract_squat_features(landmarks, include_raw_coords=include_raw_coords)
        features_list.append(features)
    
    X = np.array(features_list)
    
    # 提取标签
    if label_column not in df.columns:
        raise ValueError(f"CSV文件缺少标签列: {label_column}")
    
    y = df[label_column].values.astype(np.int32)
    
    # 验证标签值
    unique_labels = np.unique(y)
    if not all(label in [0, 1, 2] for label in unique_labels):
        raise ValueError(f"标签值必须是0, 1, 或2，但发现: {unique_labels}")
    
    print(f"[INFO] 加载了 {len(X)} 个样本，特征维度: {X.shape[1]}")
    print(f"[INFO] 标签分布: {np.bincount(y)}")
    
    return X, y


# 使用示例
if __name__ == "__main__":
    # 示例1: 创建新模型并预测
    print("=" * 50)
    print("示例1: 使用模型进行预测")
    print("=" * 50)
    
    classifier = SquatClassifier()
    
    # 模拟33个骨骼点数据（实际使用时从MediaPipe获取）
    # 格式: 33x4的数组，每行是 [x, y, z, visibility]
    sample_landmarks = np.random.rand(33, 4).astype(np.float32)
    
    state, confidence, probabilities = classifier.predict(sample_landmarks)
    state_names = {0: "站直", 1: "半蹲", 2: "完全蹲下"}
    print(f"预测状态: {state} ({state_names[state]})")
    print(f"置信度: {confidence:.4f}")
    print(f"概率分布: 站直={probabilities[0]:.4f}, 半蹲={probabilities[1]:.4f}, 完全蹲下={probabilities[2]:.4f}")
    
    # 显示提取的特征
    features = extract_squat_features(sample_landmarks)
    feature_names = [
        "左膝盖角度", "右膝盖角度", "左髋部角度", "右髋部角度",
        "髋关节垂直高度", "肩膀垂直高度", "左膝盖水平偏移", "右膝盖水平偏移"
    ]
    print("\n提取的特征:")
    for name, value in zip(feature_names, features):
        print(f"  {name}: {value:.4f}")
    
    # 示例2: 如果有训练数据，可以训练模型
    print("\n" + "=" * 50)
    print("示例2: 训练模型（需要CSV数据）")
    print("=" * 50)
    print("如果有标注好的CSV数据，可以使用以下代码训练：")
    print("""
    # 加载数据（会自动提取特征）
    X, y = load_data_from_csv('pose_landmarks_with_labels.csv', label_column='label')
    
    # 划分训练集和验证集
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 训练模型
    classifier = SquatClassifier()
    history = classifier.train(X_train, y_train, X_val, y_val, epochs=50)
    
    # 保存模型
    classifier.save_model('squat_classifier_model.h5')
    """)


