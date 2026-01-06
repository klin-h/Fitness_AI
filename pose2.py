import numpy as np
import math
import cv2
import mediapipe as mp
import os
import logging
from typing import Dict, List, Tuple, Any, Optional
from collections import deque
import time
import torch
import torch.nn as nn
import torch.nn.functional as F

# 设置环境变量
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionalEncoding(nn.Module):
    """Transformer位置编码"""
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        
        self.register_buffer('pe', pe)
        
    def forward(self, x):
        return x + self.pe[:x.size(1), :].transpose(0, 1)

class TemporalBlock(nn.Module):
    """时序块"""
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(TemporalBlock, self).__init__()
        self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size,
                              stride=stride, padding=padding, dilation=dilation)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)
        
        self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size,
                              stride=stride, padding=padding, dilation=dilation)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)
        
        self.net = nn.Sequential(self.conv1, self.relu1, self.dropout1,
                                self.conv2, self.relu2, self.dropout2)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()
        
    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TemporalConvNet(nn.Module):
    """时序卷积网络用于动作分析"""
    
    def __init__(self, input_size, num_channels, kernel_size=5, dropout=0.2):
        super(TemporalConvNet, self).__init__()
        layers = []
        num_levels = len(num_channels)
        
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = input_size if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            
            layers += [TemporalBlock(in_channels, out_channels, kernel_size, 
                                   stride=1, dilation=dilation_size,
                                   padding=(kernel_size-1) * dilation_size // 2,
                                   dropout=dropout)]
            
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.network(x)

class AdvancedPoseTransformer(nn.Module):
    """基于Transformer的先进姿态序列分析模型"""
    
    def __init__(self, input_dim=132, hidden_dim=128, num_heads=4, num_layers=3, num_classes=9):
        super(AdvancedPoseTransformer, self).__init__()
        
        self.tcn = TemporalConvNet(
            input_size=input_dim,
            num_channels=[64, 128, hidden_dim],
            kernel_size=3,
            dropout=0.1
        )
        
        self.positional_encoding = PositionalEncoding(hidden_dim)
        
        # Transformer编码器
        encoder_layers = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim*2,
            dropout=0.1,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        
        # 多任务输出头
        self.action_classifier = nn.Linear(hidden_dim, num_classes)  # 动作分类（保留但可结合规则）
        self.quality_regressor = nn.Linear(hidden_dim, 1)  # 质量评分
        self.phase_detector = nn.Linear(hidden_dim, 3)  # 动作阶段检测
        self.anomaly_detector = nn.Linear(hidden_dim, 1)  # 异常检测
        
    def forward(self, x):
        # x: (batch_size, seq_len, input_dim)
        x = x.transpose(1, 2)  # (batch_size, input_dim, seq_len)
        x = self.tcn(x)  # (batch_size, hidden_dim, seq_len)
        x = x.transpose(1, 2)  # (batch_size, seq_len, hidden_dim)
        
        x = self.positional_encoding(x)
        
        # Transformer处理
        encoded = self.transformer_encoder(x)
        
        # 使用序列的最后一个时间步进行分类
        last_hidden = encoded[:, -1, :]
        
        # 多任务输出
        action_logits = self.action_classifier(last_hidden)
        quality_score = torch.sigmoid(self.quality_regressor(last_hidden)) * 100
        phase_probs = F.softmax(self.phase_detector(last_hidden), dim=-1)
        anomaly_score = torch.sigmoid(self.anomaly_detector(last_hidden))
        
        return {
            'action': action_logits,
            'quality': quality_score,
            'phase': phase_probs,
            'anomaly': anomaly_score
        }

class PoseAutoencoder(nn.Module):
    """姿态自编码器用于异常检测"""
    def __init__(self, input_dim=99, hidden_dim=32):
        super(PoseAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, hidden_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim)
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

class DeepPoseAnalyzer:
    """基于深度学习的姿态分析器"""
    
    def __init__(self):
        # MediaPipe配置
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,  # 使用最高复杂度模型
            smooth_landmarks=True,
            enable_segmentation=False,
            smooth_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 深度学习模型参数
        self.sequence_length = 20
        self.pose_sequence = deque(maxlen=self.sequence_length)
        
        # 初始化深度学习模型
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        self.transformer_model = AdvancedPoseTransformer(
            input_dim=132,  # 基础坐标(99) + 高级特征(33)
            hidden_dim=128,
            num_heads=4,
            num_layers=3,
            num_classes=9  # neutral, squat_down, squat_up, pushup_down, pushup_up, plank_hold, jumpingjack_open, jumpingjack_close, abnormal
        ).to(self.device)
        
        self.autoencoder = PoseAutoencoder(input_dim=99, hidden_dim=32).to(self.device)
        
        # 将模型设置为评估模式
        self.transformer_model.eval()
        self.autoencoder.eval()
        
        # 动作状态
        self.action_counts = {"squat": 0, "pushup": 0, "plank": 0, "jumpingjack": 0}
        self.last_action = "neutral"
        self.action_confidences = deque(maxlen=10)
        self.current_exercise = None  # 当前检测到的主要动作类型
        
        # 新增：动作状态标志，用于控制计数逻辑
        self.squat_ready_for_next = True  # 深蹲：是否准备好进行下一次计数
        self.pushup_ready_for_next = True  # 俯卧撑：是否准备好进行下一次计数
        self.plank_start_time = None  # 平板支撑：开始时间
        self.plank_total_time = 0  # 平板支撑：累计时间（秒）
        
        # 角度序列用于规则判断
        self.angle_sequences = {
            'knee': deque(maxlen=self.sequence_length),
            'elbow': deque(maxlen=self.sequence_length),
            'hip': deque(maxlen=self.sequence_length),
            'arm': deque(maxlen=self.sequence_length),
            'back': deque(maxlen=self.sequence_length),
            'shoulder_hip_knee': deque(maxlen=self.sequence_length),  # 新增：肩-髋-膝角度
            'ankle_hip_shoulder': deque(maxlen=self.sequence_length),  # 新增：踝-髋-肩角度
            'leg_spread': deque(maxlen=self.sequence_length),  # 新增：腿部展开角度
        }
        
        # 动作特征统计
        self.action_features = {
            'squat_features': deque(maxlen=self.sequence_length),
            'pushup_features': deque(maxlen=self.sequence_length),
            'plank_features': deque(maxlen=self.sequence_length),
            'jumpingjack_features': deque(maxlen=self.sequence_length)
        }
        
        # 开合跳状态跟踪 - 新增角度极值记录
        self.jumpingjack_state = "unknown"  # unknown, open, close
        self.jumpingjack_cycle_count = 0
        self.jumpingjack_last_state = "unknown"  # 上一次的状态
        
        # 新增：开合跳角度极值记录
        self.jumpingjack_angle_extremes = {
            'arm_min': float('inf'),
            'arm_max': float('-inf'),
            'leg_spread_min': float('inf'),
            'leg_spread_max': float('-inf')
        }
        
        # 新增：开合跳状态机
        self.jumpingjack_phase = "rest"  # rest, opening, open, closing, close
        self.jumpingjack_last_phase_change = time.time()
        
        logger.info("Deep learning pose analyzer initialized")
    
    def extract_advanced_features(self, landmarks):
        """提取高级姿态特征"""
        features = []
        
        # 基础坐标特征 (33个关键点 * 3个坐标 = 99维)
        for landmark in landmarks:
            features.extend([landmark['x'], landmark['y'], landmark['z']])
        
        # 动力学特征 (速度 = 33维)
        kinematic_features = self._calculate_kinematic_features()
        features.extend(kinematic_features)
        
        return np.array(features, dtype=np.float32)
    
    def _calculate_kinematic_features(self):
        """计算运动学特征"""
        if len(self.pose_sequence) < 2:
            return [0.0] * 33  # 返回零向量
        
        current_pose = self.pose_sequence[-1][:99]  # 只取坐标部分
        previous_pose = self.pose_sequence[-2][:99] if len(self.pose_sequence) >= 2 else current_pose
        
        velocities = []
        
        # 计算关键点速度 (33个点)
        for i in range(33):
            if i * 3 + 1 < len(current_pose) and i * 3 + 1 < len(previous_pose):
                curr_x, curr_y = current_pose[i*3], current_pose[i*3+1]
                prev_x, prev_y = previous_pose[i*3], previous_pose[i*3+1]
                velocity = math.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
                velocities.append(velocity)
            else:
                velocities.append(0.0)
        
        return velocities
    
    def calculate_angle(self, point1, point2, point3):
        """计算三点之间的角度"""
        try:
            v1 = np.array([point1['x'] - point2['x'], point1['y'] - point2['y']])
            v2 = np.array([point3['x'] - point2['x'], point3['y'] - point2['y']])
            
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle = np.arccos(cos_angle)
            
            return np.degrees(angle)
        except:
            return 0.0
    
    def calculate_joint_angles(self, landmarks):
        """计算多个关节角度"""
        angles = {}
        
        # 膝盖角度 (平均左右)
        left_knee = self.calculate_angle(landmarks[23], landmarks[25], landmarks[27])  # 左髋-膝-踝
        right_knee = self.calculate_angle(landmarks[24], landmarks[26], landmarks[28])  # 右髋-膝-踝
        angles['knee'] = (left_knee + right_knee) / 2
        
        # 肘部角度 (平均左右)
        left_elbow = self.calculate_angle(landmarks[11], landmarks[13], landmarks[15])  # 左肩-肘-腕
        right_elbow = self.calculate_angle(landmarks[12], landmarks[14], landmarks[16])  # 右肩-肘-腕
        angles['elbow'] = (left_elbow + right_elbow) / 2
        
        # 髋部角度 (平均左右)
        left_hip = self.calculate_angle(landmarks[11], landmarks[23], landmarks[25])  # 左肩-髋-膝
        right_hip = self.calculate_angle(landmarks[12], landmarks[24], landmarks[26])  # 右肩-髋-膝
        angles['hip'] = (left_hip + right_hip) / 2
        
        # 手臂角度 (对于开合跳)
        left_arm = self.calculate_angle(landmarks[23], landmarks[11], landmarks[13])  # 左髋-肩-肘
        right_arm = self.calculate_angle(landmarks[24], landmarks[12], landmarks[14])  # 右髋-肩-肘
        angles['arm'] = (left_arm + right_arm) / 2
        
        # 背部角度 (使用肩-髋-膝)
        back_angle = (left_hip + right_hip) / 2  # 简化
        angles['back'] = back_angle
        
        # 新增角度：肩-髋-膝角度（用于区分深蹲和俯卧撑）
        left_shoulder_hip_knee = self.calculate_angle(landmarks[11], landmarks[23], landmarks[25])
        right_shoulder_hip_knee = self.calculate_angle(landmarks[12], landmarks[24], landmarks[26])
        angles['shoulder_hip_knee'] = (left_shoulder_hip_knee + right_shoulder_hip_knee) / 2
        
        # 新增角度：踝-髋-肩角度（身体倾斜度）
        left_ankle_hip_shoulder = self.calculate_angle(landmarks[27], landmarks[23], landmarks[11])
        right_ankle_hip_shoulder = self.calculate_angle(landmarks[28], landmarks[24], landmarks[12])
        angles['ankle_hip_shoulder'] = (left_ankle_hip_shoulder + right_ankle_hip_shoulder) / 2
        
        # 新增：腿部展开角度（用于开合跳检测）
        # 计算两腿之间的角度（左髋-右髋-右膝）
        leg_spread_left = self.calculate_angle(landmarks[23], landmarks[24], landmarks[26])
        leg_spread_right = self.calculate_angle(landmarks[24], landmarks[23], landmarks[25])
        angles['leg_spread'] = (leg_spread_left + leg_spread_right) / 2
        
        return angles
    
    def is_pose_visible(self, landmarks):
        """检查姿态可见性"""
        try:
            key_joints = [11, 12, 13, 14, 23, 24, 25, 26]
            visible_count = 0
            
            for joint_idx in key_joints:
                if joint_idx < len(landmarks):
                    landmark = landmarks[joint_idx]
                    if (0 <= landmark['x'] <= 1 and 
                        0 <= landmark['y'] <= 1 and 
                        landmark.get('visibility', 1) > 0.5):
                        visible_count += 1
            
            return visible_count >= len(key_joints) * 0.6
        except:
            return False
    
    def calculate_action_features(self, angles):
        """计算动作特异性特征"""
        features = {}
        
        # 深蹲特征：膝盖和髋部弯曲，身体垂直移动
        features['squat'] = (
            angles['knee'] < 120 and  # 膝盖弯曲
            angles['hip'] < 120 and   # 髋部弯曲
            angles['ankle_hip_shoulder'] > 150 and  # 身体相对垂直
            angles['elbow'] > 60      # 手臂相对稳定
        )
        
        # 俯卧撑特征：肘部弯曲，身体水平，髋部稳定
        features['pushup'] = (
            angles['elbow'] < 120 and  # 肘部弯曲
            angles['back'] > 160 and   # 背部直
            angles['hip'] > 160 and    # 髋部直
            angles['shoulder_hip_knee'] > 150  # 身体水平
        )
        
        # 平板支撑特征：肘部固定角度，身体水平
        features['plank'] = (
            80 < angles['elbow'] < 100 and  # 肘部固定角度
            angles['back'] > 160 and        # 背部非常直
            angles['hip'] > 160 and         # 髋部非常直
            angles['knee'] > 120            # 膝盖相对直
        )
        
        # 开合跳特征：手臂和腿部大幅度运动
        features['jumpingjack'] = (
            (angles['arm'] > 120 or angles['arm'] < 60) or  # 手臂大幅度
            (angles['leg_spread'] > 45 or angles['leg_spread'] < 20)  # 腿部开合
        )
        
        return features
    
    def detect_jumpingjack_state(self, angles):
        """专门检测开合跳状态 - 改进版本"""
        # 更新角度极值记录
        self._update_jumpingjack_angle_extremes(angles)
        
        # 手臂展开条件
        arms_open = angles['arm'] > 110
        # 腿部展开条件
        legs_open = angles['leg_spread'] > 105
        
        # 手臂闭合条件
        arms_closed = angles['arm'] < 70
        # 腿部闭合条件
        legs_closed = angles['leg_spread'] < 95
        
        # 判断开合跳状态 - 更宽松的条件
        if arms_open and legs_open:
            return "jumpingjack_open", 0.9
        elif arms_closed and legs_closed:
            return "jumpingjack_close", 0.9
        elif arms_open and legs_closed:
            return "jumpingjack_open", 0.7  # 手臂打开但腿部未完全打开
        elif arms_closed and legs_open:
            return "jumpingjack_close", 0.7  # 手臂闭合但腿部未完全闭合
        elif arms_open:
            return "jumpingjack_open", 0.6
        elif arms_closed:
            return "jumpingjack_close", 0.6
        else:
            return "jumpingjack_transition", 0.5
    
    def _update_jumpingjack_angle_extremes(self, angles):
        """更新开合跳角度极值记录"""
        # 更新手臂角度极值
        if angles['arm'] < self.jumpingjack_angle_extremes['arm_min']:
            self.jumpingjack_angle_extremes['arm_min'] = angles['arm']
        if angles['arm'] > self.jumpingjack_angle_extremes['arm_max']:
            self.jumpingjack_angle_extremes['arm_max'] = angles['arm']
        
        # 更新腿部展开角度极值
        if angles['leg_spread'] < self.jumpingjack_angle_extremes['leg_spread_min']:
            self.jumpingjack_angle_extremes['leg_spread_min'] = angles['leg_spread']
        if angles['leg_spread'] > self.jumpingjack_angle_extremes['leg_spread_max']:
            self.jumpingjack_angle_extremes['leg_spread_max'] = angles['leg_spread']
    
    def _check_jumpingjack_cycle_completion(self):
        """检查开合跳周期是否完成 - 检测两次完整动作才计数一次"""
        # 计算手臂和腿部的角度差值
        arm_range = self.jumpingjack_angle_extremes['arm_max'] - self.jumpingjack_angle_extremes['arm_min']
        leg_spread_range = self.jumpingjack_angle_extremes['leg_spread_max'] - self.jumpingjack_angle_extremes['leg_spread_min']
        
        # 检查是否满足差值条件
        arm_condition = arm_range > 60  # 手臂角度变化大于60度
        leg_condition = leg_spread_range > 8   # 腿部展开角度变化大于8度
        
        # 如果满足条件，增加周期计数
        if arm_condition and leg_condition:
            self.jumpingjack_cycle_count += 1
            print(f"Cycle detected: {self.jumpingjack_cycle_count}")
            
            # 重置极值记录，开始检测下一个半周期
            self.jumpingjack_angle_extremes = {
                'arm_min': float('inf'),
                'arm_max': float('-inf'),
                'leg_spread_min': float('inf'),
                'leg_spread_max': float('-inf')
            }
            
            # 每2个周期计数一次（一次完整的开合跳）
            if self.jumpingjack_cycle_count >= 2:
                self.action_counts["jumpingjack"] += 1
                self.jumpingjack_cycle_count = 0  # 重置周期计数
                print(f"Jumping jack count: {self.action_counts['jumpingjack']}")
                return True
        
        return False
    
    def rule_based_detect_action(self, angles):
        """基于关节角度的规则判断动作类型和状态"""
        if len(self.angle_sequences['knee']) < self.sequence_length:
            return "neutral", 0.0
        
        # 计算角度的标准差和平均值，用于判断动作类型
        std_knee = np.std(list(self.angle_sequences['knee']))
        std_elbow = np.std(list(self.angle_sequences['elbow']))
        std_hip = np.std(list(self.angle_sequences['hip']))
        std_arm = np.std(list(self.angle_sequences['arm']))
        std_back = np.std(list(self.angle_sequences['back']))
        std_shoulder_hip_knee = np.std(list(self.angle_sequences['shoulder_hip_knee']))
        std_leg_spread = np.std(list(self.angle_sequences['leg_spread']))  # 新增：腿部展开标准差
        
        avg_knee = np.mean(list(self.angle_sequences['knee']))
        avg_elbow = np.mean(list(self.angle_sequences['elbow']))
        avg_hip = np.mean(list(self.angle_sequences['hip']))
        avg_arm = np.mean(list(self.angle_sequences['arm']))
        avg_back = np.mean(list(self.angle_sequences['back']))
        avg_shoulder_hip_knee = np.mean(list(self.angle_sequences['shoulder_hip_knee']))
        avg_ankle_hip_shoulder = np.mean(list(self.angle_sequences['ankle_hip_shoulder']))
        avg_leg_spread = np.mean(list(self.angle_sequences['leg_spread']))  # 新增：平均腿部展开角度
        
        # 计算动作特异性特征
        action_features = self.calculate_action_features({
            'knee': avg_knee,
            'elbow': avg_elbow,
            'hip': avg_hip,
            'arm': avg_arm,
            'back': avg_back,
            'shoulder_hip_knee': avg_shoulder_hip_knee,
            'ankle_hip_shoulder': avg_ankle_hip_shoulder,
            'leg_spread': avg_leg_spread
        })
        
        # 改进的动作类型判断逻辑
        squat_score = (
            (1 if std_knee > 15 else 0) + (1 if std_hip > 12 else 0) + 
            (1 if std_elbow < 10 else 0) + (1 if std_back < 8 else 0) +
            (1 if action_features['squat'] else 0) +
            (1 if avg_ankle_hip_shoulder > 140 else 0)  # 身体相对垂直
        )
        
        pushup_score = (
            (1 if std_elbow > 20 else 0) +                    # 提高肘部变化阈值
            (1 if std_back < 5 else 0) + 
            (1 if std_hip < 5 else 0) + 
            (1 if std_knee < 8 else 0) +
            (1 if action_features['pushup'] else 0) +   
            (1 if avg_shoulder_hip_knee > 150 else 0) +  # 提高身体水平要求
            (1 if self._has_vertical_movement() else 0)  # 新增：检测垂直移动
        )
        
        # 改进的开合跳评分 - 更注重手臂和腿部展开的变化
        jumpingjack_score = (
            (1 if std_arm > 20 else 0) + (1 if std_leg_spread > 4 else 0) +  # 手臂和腿部展开变化大
            (1 if std_back < 10 else 0) + (1 if std_hip < 5 else 0) +
            (1 if action_features['jumpingjack'] else 0) +
            (1 if avg_leg_spread > 85 or avg_leg_spread < 115 else 0)  # 腿部有开合变化
        )
        
        plank_score = (
            (1 if std_back < 5 else 0) + 
            (1 if std_hip < 5 else 0) + 
            (1 if std_elbow < 8 else 0) +                     # 更严格的肘部稳定性
            (1 if std_knee < 8 else 0) +                      # 更严格的膝盖稳定性
            (1 if action_features['plank'] else 0) +
            (1 if 80 < avg_elbow < 100 else 0) +   # 更精确的肘部角度范围
            (1 if self._is_static_pose() else 0)  # 新增：检测静态姿势
        )
        
        scores = {
            "squat": squat_score,
            "pushup": pushup_score, 
            "jumpingjack": jumpingjack_score,
            "plank": plank_score
        }
        # 确定得分最高的动作
        max_score = max(scores.values())
        if max_score >= 4:  # 设置阈值
            self.current_exercise = max(scores, key=scores.get)
        else:
            self.current_exercise = None
            return "neutral", 1.0
        
        # 根据动作类型判断具体状态
        if self.current_exercise == "squat":
            if avg_knee < 110 and avg_hip < 130:  # 放宽阈值以适应不同下蹲深度
                state = "squat_down"
            elif avg_knee > 150 and avg_hip > 150:
                state = "squat_up"
            else:
                state = "squat_transition"
        elif self.current_exercise == "pushup":
            if avg_elbow < 90 and avg_back > 160 and avg_hip > 160:
                state = "pushup_down"
            elif avg_elbow > 140 and avg_back > 160 and avg_hip > 160:
                state = "pushup_up"
            else:
                state = "pushup_transition"
        elif self.current_exercise == "plank":
            if avg_back > 170 and avg_hip > 170 and 80 < avg_elbow < 100:
                state = "plank_hold"
            else:
                state = "plank_transition"
        elif self.current_exercise == "jumpingjack":
            # 使用专门的开合跳状态检测
            state, confidence = self.detect_jumpingjack_state({
                'arm': angles['arm'],  # 使用当前帧的手臂角度
                'leg_spread': angles['leg_spread']  # 使用当前帧的腿部展开角度
            })
            
            # 检查开合跳周期是否完成
            self._check_jumpingjack_cycle_completion()
        else:
            state = "neutral"
        
        # 置信度基于得分和稳定性
        confidence = min(max_score / 6.0, 1.0)  # 最大得分6分
        
        return state, confidence
    
    def _has_vertical_movement(self):
        """检测是否有明显的垂直移动（俯卧撑特征）"""
        if len(self.pose_sequence) < 5:
            return False
        
        # 计算肩膀点的垂直位置变化
        shoulder_y_positions = []
        for pose in list(self.pose_sequence)[-5:]:
            if len(pose) >= 33*3:  # 确保有足够的数据
                # 左肩和右肩的y坐标平均
                left_shoulder_y = pose[11*3+1]  # 索引11的y坐标
                right_shoulder_y = pose[12*3+1] # 索引12的y坐标  
                avg_y = (left_shoulder_y + right_shoulder_y) / 2
                shoulder_y_positions.append(avg_y)
        
        if len(shoulder_y_positions) < 3:
            return False
        
        # 计算垂直位置的标准差
        vertical_std = np.std(shoulder_y_positions)
        return vertical_std > 0.02  # 阈值可根据实际情况调整

    def _is_static_pose(self):
        """检测是否是静态姿势（平板支撑特征）"""
        if len(self.pose_sequence) < 5:
            return False
        
        # 计算整体运动幅度
        total_movement = 0
        for i in range(1, min(5, len(self.pose_sequence))):
            current = self.pose_sequence[-i]
            previous = self.pose_sequence[-i-1] 
            movement = np.linalg.norm(current[:99] - previous[:99])  # 坐标部分的欧氏距离
            total_movement += movement
        
        avg_movement = total_movement / 4
        return avg_movement < 0.01  # 静态姿势的运动幅度很小

    def deep_analyze_sequence(self):
        """使用深度学习模型分析姿态序列（保留质量、阶段、异常检测）"""
        if len(self.pose_sequence) < self.sequence_length:
            return None
        
        try:
            # 准备输入数据
            sequence_array = np.array(list(self.pose_sequence))
            
            # 转换为PyTorch张量
            input_tensor = torch.FloatTensor(sequence_array).unsqueeze(0).to(self.device)  # (1, seq_len, feature_dim)
            
            # Transformer分析
            with torch.no_grad():
                transformer_output = self.transformer_model(input_tensor)
                
                quality_score = transformer_output['quality'].item()
                phase_pred = transformer_output['phase']
                model_anomaly_score = transformer_output['anomaly'].item()
            
            # 自编码器异常检测
            poses = input_tensor[0, :, :99]  # (seq_len, 99)
            reconstructed = self.autoencoder(poses)
            recon_error = F.mse_loss(reconstructed, poses, reduction='mean').item()
            
            # 结合异常分数（示例：取最大值）
            anomaly_score = max(model_anomaly_score, recon_error / 0.01)  # 假设阈值0.01
            
            return {
                'quality_score': quality_score,
                'phase_distribution': phase_pred.squeeze().cpu().numpy(),
                'anomaly_score': anomaly_score,
                'is_abnormal': anomaly_score > 0.7,
                'reconstruction_error': recon_error
            }
            
        except Exception as e:
            logger.error(f"Deep learning analysis failed: {e}")
            return None
    
    def _update_action_state(self, current_action, confidence):
        """更新动作状态和计数 - 改进计数逻辑"""
        self.action_confidences.append(confidence)
        avg_confidence = np.mean(self.action_confidences) if self.action_confidences else 0
        
        # 只有在置信度足够高时才更新状态
        if avg_confidence > 0.6:
            # 深蹲计数逻辑 - 添加角度限制
            if self.current_exercise == "squat":
                if ((current_action == "squat_down" and self.last_action != "squat_down" and self.last_action != "squat_transition" and self.last_action != "squat_up") or (current_action == "squat_transition" and self.last_action != "squat_transition"and self.last_action != "squat_down")) and self.squat_ready_for_next:
                    self.action_counts["squat"] += 1
                    self.squat_ready_for_next = False  # 标记为已计数，等待恢复
                    print(f"Squat count: {self.action_counts['squat']}")  # 调试输出
                
                # 当膝盖角度大于150度时，准备下一次计数
                if len(self.angle_sequences['knee']) > 0:
                    current_knee_angle = list(self.angle_sequences['knee'])[-1]
                    if current_knee_angle > 150:
                        self.squat_ready_for_next = True
            
            # 俯卧撑计数逻辑 - 添加角度限制
            elif self.current_exercise == "pushup":
                if ((current_action == "pushup_down" and self.last_action != "pushup_down" and self.last_action != "pushup_transition" and self.last_action != "pushup_up") or (current_action == "pushup_transition" and self.last_action != "pushup_down" and self.last_action != "pushup_transition" and self.last_action != "pushup_up")) and self.pushup_ready_for_next:
                    self.action_counts["pushup"] += 1
                    self.pushup_ready_for_next = False  # 标记为已计数，等待恢复
                    print(f"Pushup count: {self.action_counts['pushup']}")  # 调试输出
                
                # 当肘部角度大于140度时，准备下一次计数
                if len(self.angle_sequences['elbow']) > 0:
                    current_elbow_angle = list(self.angle_sequences['elbow'])[-1]
                    if current_elbow_angle > 140:
                        self.pushup_ready_for_next = True
            
            # 平板支撑时间记录 - 不计数，记录时间
            elif self.current_exercise == "plank":
                if current_action == "plank_hold":
                    if self.plank_start_time is None:
                        self.plank_start_time = time.time()
                        print("Plank timing started")
                    else:
                        # 累计有效时间（秒）
                        current_time = time.time()
                        self.plank_total_time = int(current_time - self.plank_start_time)
                        self.action_counts["plank"] = self.plank_total_time
                else:
                    # 姿势不标准或不是plank_hold状态，暂停计时
                    if self.plank_start_time is not None:
                        # 记录已经计时的时间，但暂停新的计时
                        current_time = time.time()
                        self.plank_total_time = int(current_time - self.plank_start_time)
                        self.action_counts["plank"] = self.plank_total_time
                        print(f"Plank timing paused at {self.plank_total_time} seconds")
                
            
            # 开合跳计数逻辑 - 使用周期检测
            elif self.current_exercise == "jumpingjack":
                # 开合跳计数已经在_check_jumpingjack_cycle_completion中处理
                pass
            
            self.last_action = current_action
    
    def process_frame(self, frame):
        """处理单帧图像"""
        try:
            # 转换颜色空间
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            
            # 姿态检测
            results = self.pose.process(image_rgb)
            
            if results.pose_landmarks:
                landmarks = self._convert_landmarks(results.pose_landmarks)
                
                if not self.is_pose_visible(landmarks):
                    return {"error": "Pose not visible", "counts": self.action_counts}
                
                # 计算关节角度
                angles = self.calculate_joint_angles(landmarks)
                
                # 添加角度到序列
                for key in angles:
                    self.angle_sequences[key].append(angles[key])
                
                # 提取特征并添加到姿态序列
                features = self.extract_advanced_features(landmarks)
                self.pose_sequence.append(features)
                
                # 规则基动作判断
                predicted_action, action_confidence = self.rule_based_detect_action(angles)
                self._update_action_state(predicted_action, action_confidence)
                
                # 深度学习分析（质量、阶段、异常）
                if len(self.pose_sequence) >= self.sequence_length:
                    deep_analysis = self.deep_analyze_sequence()
                    if deep_analysis:
                        return self.interpret_deep_analysis(deep_analysis, angles, predicted_action, action_confidence)
                    else:
                        return {"error": "Deep learning analysis failed", "counts": self.action_counts}
                else:
                    return {
                        "status": "collecting", 
                        "frames_collected": len(self.pose_sequence),
                        "counts": self.action_counts,
                        "angles": angles  # 添加角度信息到返回结果
                    }
            
            return {"error": "No human pose detected", "counts": self.action_counts}
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {"error": f"Processing failed: {str(e)}", "counts": self.action_counts}
    
    def interpret_deep_analysis(self, deep_analysis, angles, predicted_action, action_confidence):
        """解释深度学习分析结果"""
        if not deep_analysis:
            return {"error": "Analysis failed", "counts": self.action_counts}
        
        # 基于规则动作和角度生成反馈
        feedback = self._generate_ai_feedback(predicted_action, angles)
        
        return {
            "is_correct": deep_analysis['quality_score'] > 70 and not deep_analysis['is_abnormal'],
            "score": int(deep_analysis['quality_score']),
            "feedback": feedback['main'],
            "detailed_feedback": feedback['details'],
            "predicted_action": predicted_action,
            "action_confidence": action_confidence,
            "anomaly_detected": deep_analysis['is_abnormal'],
            "anomaly_score": deep_analysis['anomaly_score'],
            "ai_suggestions": feedback['suggestions'],
            "counts": self.action_counts,
            "knee_angle": angles['knee'],
            "elbow_angle": angles['elbow'],
            "hip_angle": angles['hip'],
            "shoulder_hip_knee_angle": angles['shoulder_hip_knee'],  # 新增角度显示
            "ankle_hip_shoulder_angle": angles['ankle_hip_shoulder'],  # 新增角度显示
            "leg_spread_angle": angles['leg_spread'],  # 新增腿部展开角度显示
            "count_changed": False,  # 在_update_action_state中处理
            "in_action_position": predicted_action != "neutral"
        }
    
    def _generate_ai_feedback(self, action, angles):
        """基于动作和角度生成AI反馈"""
        feedback = {
            "main": "Keep up the good work!",
            "details": [],
            "suggestions": []
        }
        
        if action == "squat_down":
            if angles['knee'] < 60:
                feedback["main"] = "Squat too deep"
                feedback["details"].append("Your knees are bending too much")
                feedback["suggestions"].append("Keep knees above 60 degrees")
            elif angles['knee'] > 120:
                feedback["main"] = "Squat not deep enough"
                feedback["details"].append("You should bend your knees more")
                feedback["suggestions"].append("Aim for 90-110 degrees knee bend")
            else:
                feedback["main"] = "Good squat depth"
                feedback["details"].append("Maintain this depth")
        
        elif action == "pushup_down":
            if angles['elbow'] < 60:
                feedback["main"] = "Going too low"
                feedback["details"].append("Your chest is too close to ground")
                feedback["suggestions"].append("Stop when elbows are at 90 degrees")
            elif angles['back'] < 170:
                feedback["main"] = "Keep your back straight"
                feedback["details"].append("Your back is sagging")
                feedback["suggestions"].append("Engage your core muscles")
            else:
                feedback["main"] = "Good pushup form"
                feedback["details"].append("Maintain straight back")
        
        elif action == "plank_hold":
            if angles['back'] < 170:
                feedback["main"] = "Hips too high"
                feedback["details"].append("Raise your hips slightly")
                feedback["suggestions"].append("Form a straight line from head to heels")
            elif angles['hip'] < 170:
                feedback["main"] = "Hips sagging"
                feedback["details"].append("Engage your core")
                feedback["suggestions"].append("Tighten your abdominal muscles")
            else:
                feedback["main"] = "Perfect plank position"
                feedback["details"].append("Great core engagement")
        
        elif action == "jumpingjack_open":
            if angles['arm'] < 100:
                feedback["main"] = "Raise arms higher"
                feedback["details"].append("Your arms should be overhead")
                feedback["suggestions"].append("Extend arms fully overhead")
            if angles['leg_spread'] < 40:
                feedback["main"] = "Spread legs wider"
                feedback["details"].append("Jump wider for full range")
                feedback["suggestions"].append("Land with feet shoulder-width apart")
        
        elif action == "jumpingjack_close":
            if angles['arm'] > 60:
                feedback["main"] = "Bring arms closer"
                feedback["details"].append("Arms should return to sides")
                feedback["suggestions"].append("Let arms touch your thighs")
            if angles['leg_spread'] > 25:
                feedback["main"] = "Feet too far apart"
                feedback["details"].append("Bring feet together")
                feedback["suggestions"].append("Land with feet together")
        
        return feedback
    
    def _convert_landmarks(self, pose_landmarks):
        """转换MediaPipe landmarks为字典格式"""
        landmarks = []
        for idx, landmark in enumerate(pose_landmarks.landmark):
            landmarks.append({
                'x': landmark.x,
                'y': landmark.y, 
                'z': landmark.z,
                'visibility': landmark.visibility
            })
        return landmarks
    
    def get_action_counts(self):
        """获取动作计数"""
        return self.action_counts
    
    def reset_counts(self):
        """重置所有计数器"""
        self.action_counts = {"squat": 0, "pushup": 0, "plank": 0, "jumpingjack": 0}
        self.last_action = "neutral"
        self.action_confidences.clear()
        self.current_exercise = None
        self.jumpingjack_state = "unknown"
        self.jumpingjack_cycle_count = 0
        self.jumpingjack_last_state = "unknown"
        self.jumpingjack_phase = "rest"
        self.jumpingjack_last_phase_change = time.time()
        self.jumpingjack_angle_extremes = {
            'arm_min': float('inf'),
            'arm_max': float('-inf'),
            'leg_spread_min': float('inf'),
            'leg_spread_max': float('-inf')
        }
        # 重置新增的状态标志
        self.squat_ready_for_next = True
        self.pushup_ready_for_next = True
        self.plank_start_time = None
        self.plank_total_time = 0
        logger.info("All action counts and states have been reset")

def main(camera_index=0, model_path=None, video_path=None):
    """主函数：演示姿态分析器的使用"""
    
    # 初始化分析器
    analyzer = DeepPoseAnalyzer()
    
    # 加载预训练模型（如果有）
    if model_path and os.path.exists(model_path):
        try:
            checkpoint = torch.load(model_path, map_location=analyzer.device)
            analyzer.transformer_model.load_state_dict(checkpoint['model_state_dict'])
            logger.info(f"Loaded pre-trained model from {model_path}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
    
    # 初始化视频源
    if video_path:
        cap = cv2.VideoCapture(video_path)
    else:
        cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        logger.error("Cannot open video source")
        return
    
    logger.info("Starting pose analysis. Press 'q' to quit, 'r' to reset counts.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to capture frame")
            break
        
        # 处理帧
        result = analyzer.process_frame(frame)
        
        # 显示结果
        display_frame = frame.copy()
        
        # 显示计数
        counts = result.get('counts', {})
        count_text = f"Squat: {counts.get('squat', 0)} | Pushup: {counts.get('pushup', 0)} | Plank: {counts.get('plank', 0)}s | Jumping Jack: {counts.get('jumpingjack', 0)}"
        cv2.putText(display_frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示当前动作和角度信息
        if 'predicted_action' in result:
            action_text = f"Action: {result['predicted_action']} (Conf: {result.get('action_confidence', 0):.2f})"
            cv2.putText(display_frame, action_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # 显示关键角度
            angle_text = f"Knee: {result.get('knee_angle', 0):.1f}° | Elbow: {result.get('elbow_angle', 0):.1f}° | Leg Spread: {result.get('leg_spread_angle', 0):.1f}°"
            cv2.putText(display_frame, angle_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 显示反馈
        if 'feedback' in result:
            feedback_text = f"Feedback: {result['feedback']}"
            cv2.putText(display_frame, feedback_text, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        
        # 显示质量分数
        if 'score' in result:
            score_text = f"Quality Score: {result['score']}"
            color = (0, 255, 0) if result['score'] > 70 else (0, 0, 255)
            cv2.putText(display_frame, score_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 显示异常检测
        if result.get('anomaly_detected'):
            cv2.putText(display_frame, "ANOMALY DETECTED!", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
        
        cv2.imshow('Advanced Pose Analysis', display_frame)
        
        # 按键处理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            analyzer.reset_counts()
            logger.info("Counts reset")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 使用示例：
    # 从摄像头读取：main(camera_index=0)
    # 从视频文件读取：main(video_path="path/to/video.mp4")
    main(video_path="C:\\Users\\16042\\Desktop\\fitnessai\\fitnessai\\俯卧撑.mp4")