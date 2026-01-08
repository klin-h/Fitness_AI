"""
姿态分析模块

这个模块包含具体的运动分析算法，使用PyTorch模型进行预测：
1. 深蹲分析
2. 俯卧撑分析
3. 平板支撑分析
4. 开合跳分析
"""

import numpy as np
import math
import logging
from typing import Dict, List, Tuple, Any, Optional

# 导入模型加载器
from ml_models.model_loader import load_exercise_model, ExerciseModelInterface

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pose_analyzer')

class PoseAnalyzer:
    """姿态分析基类"""
    
    def __init__(self, exercise_type: str = None):
        """
        初始化分析器
        
        Args:
            exercise_type: 运动类型，用于加载对应的模型
        """
        self.min_detection_confidence = 0.5  # 最小检测置信度
        self.exercise_type = exercise_type
        self.model: Optional[ExerciseModelInterface] = None
        
        # 创建logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # 如果指定了运动类型，加载模型
        if exercise_type:
            self._load_model()
    
    def _load_model(self):
        """加载ML模型"""
        if self.exercise_type:
            self.model = load_exercise_model(self.exercise_type)
            if self.model:
                self.logger.info(f"成功加载模型: {self.exercise_type}")
            else:
                self.logger.warning(f"模型加载失败: {self.exercise_type}，将使用备用逻辑")
    
    def is_pose_visible(self, landmarks: List[Dict], required_landmarks=None) -> bool:
        """检查姿态是否可见 - 子类可覆盖此方法来定制可见性检测
        
        Args:
            landmarks: 姿态关键点
            required_landmarks: 可选，指定需要检查的关键点索引
            
        Returns:
            bool: 是否可见
        """
        # 如果未指定关键点，默认检查上半身
        if required_landmarks is None:
            required_landmarks = [11, 12, 13, 14]  # 左肩, 右肩, 左肘, 右肘
        
        for idx in required_landmarks:
            if idx >= len(landmarks) or landmarks[idx].get('visibility', 0) < self.min_detection_confidence:
                return False
        
        return True
    
    def calculate_angle(self, a: Dict, b: Dict, c: Dict) -> float:
        """
        计算三个点形成的角度
        
        Args:
            a, b, c: 三个点的坐标，b是角度的顶点
            
        Returns:
            float: 角度（度）
        """
        # 计算向量
        ba = [a['x'] - b['x'], a['y'] - b['y']]
        bc = [c['x'] - b['x'], c['y'] - b['y']]
        
        # 计算点积
        dot_product = ba[0] * bc[0] + ba[1] * bc[1]
        
        # 计算向量长度
        ba_length = math.sqrt(ba[0]**2 + ba[1]**2)
        bc_length = math.sqrt(bc[0]**2 + bc[1]**2)
        
        # 计算夹角（弧度）
        try:
            cos_angle = dot_product / (ba_length * bc_length)
            # 防止浮点数计算导致的越界
            cos_angle = max(min(cos_angle, 1.0), -1.0)
            angle_rad = math.acos(cos_angle)
            
            # 转换为角度
            angle_deg = math.degrees(angle_rad)
            return angle_deg
        except (ZeroDivisionError, ValueError):
            return 180.0  # 如果计算出错，返回180度
    
    def calculate_distance(self, a: Dict, b: Dict) -> float:
        """
        计算两点之间的距离
        
        Args:
            a, b: 两个点的坐标
            
        Returns:
            float: 距离
        """
        return math.sqrt((a['x'] - b['x'])**2 + (a['y'] - b['y'])**2)

class SquatAnalyzer(PoseAnalyzer):
    """深蹲动作分析器 - 使用ML模型"""
    
    def __init__(self):
        super().__init__(exercise_type='squat')
        # 保留计数状态（模型可能返回增量，需要累加）
        self.squat_count = 0
        self.last_count = 0
    
    def is_pose_visible(self, landmarks: List[Dict], required_landmarks=None) -> bool:
        """检查深蹲所需关键点是否可见"""
        # 深蹲关键点：左右髋部和膝盖
        required_landmarks = [23, 24, 25, 26]  # 左右髋部和膝盖
        
        # 至少有一侧髋部和膝盖可见即可
        if len(landmarks) < 27:
            return False
            
        left_visible = landmarks[23].get('visibility', 0) >= self.min_detection_confidence and \
                    landmarks[25].get('visibility', 0) >= self.min_detection_confidence
        
        right_visible = landmarks[24].get('visibility', 0) >= self.min_detection_confidence and \
                     landmarks[26].get('visibility', 0) >= self.min_detection_confidence
        
        return left_visible or right_visible
    
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析深蹲动作 - 使用ML模型
        
        Args:
            landmarks: MediaPipe姿态关键点
            
        Returns:
            Dict: 分析结果
        """
        if not self.is_pose_visible(landmarks):
            return {
                "error": "姿态不可见",
                "is_correct": False,
                "score": 0,
                "feedback": "请确保下半身在摄像头范围内",
                "count": self.squat_count
            }
        
        # 如果模型已加载，使用模型进行预测
        if self.model:
            try:
                result = self.model.predict(landmarks)
                
                # 更新计数（如果模型返回的是增量，需要累加；如果是总数，直接使用）
                if "count" in result:
                    model_count = result.get("count", 0)
                    # 如果模型返回的计数大于当前计数，说明有新计数
                    if model_count > self.last_count:
                        self.squat_count = model_count
                        self.last_count = model_count
                    else:
                        # 使用当前计数
                        result["count"] = self.squat_count
                
                return result
                
            except Exception as e:
                self.logger.error(f"模型预测失败: {str(e)}")
                # 模型失败时返回错误信息
                return {
                    "error": f"模型预测失败: {str(e)}",
                    "is_correct": False,
                    "score": 0,
                    "feedback": "动作分析出错，请重试",
                    "count": self.squat_count
                }
        else:
            # 模型未加载，返回错误
            return {
                "error": "模型未加载",
                "is_correct": False,
                "score": 0,
                "feedback": "模型加载失败，请检查模型文件",
                "count": self.squat_count
            }

class PushupAnalyzer(PoseAnalyzer):
    """俯卧撑动作分析器 - 使用ML模型"""
    
    def __init__(self):
        super().__init__(exercise_type='pushup')
        # 保留计数状态
        self.pushup_count = 0
        self.last_count = 0
    
    def is_pose_visible(self, landmarks: List[Dict]) -> bool:
        """检查俯卧撑所需关键点是否可见"""
        # 俯卧撑主要关键点：肩部和肘部
        if len(landmarks) < 15:
            return False
            
        required_landmarks = [11, 12, 13, 14]  # 左右肩部和肘部
        
        # 检查至少一侧的肩部和肘部可见
        left_visible = landmarks[11].get('visibility', 0) >= self.min_detection_confidence and \
                    landmarks[13].get('visibility', 0) >= self.min_detection_confidence
        
        right_visible = landmarks[12].get('visibility', 0) >= self.min_detection_confidence and \
                     landmarks[14].get('visibility', 0) >= self.min_detection_confidence
        
        return left_visible or right_visible
        
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析俯卧撑动作 - 使用ML模型
        
        Args:
            landmarks: MediaPipe姿态关键点
            
        Returns:
            Dict: 分析结果
        """
        if not self.is_pose_visible(landmarks):
            return {
                "error": "姿态不可见",
                "is_correct": False,
                "score": 0,
                "feedback": "请确保上半身在摄像头范围内",
                "count": self.pushup_count
            }
        
        # 如果模型已加载，使用模型进行预测
        if self.model:
            try:
                result = self.model.predict(landmarks)
                
                # 更新计数
                if "count" in result:
                    model_count = result.get("count", 0)
                    if model_count > self.last_count:
                        self.pushup_count = model_count
                        self.last_count = model_count
                    else:
                        result["count"] = self.pushup_count
                
                return result
                
            except Exception as e:
                self.logger.error(f"模型预测失败: {str(e)}")
                return {
                    "error": f"模型预测失败: {str(e)}",
                    "is_correct": False,
                    "score": 0,
                    "feedback": "动作分析出错，请重试",
                    "count": self.pushup_count
                }
        else:
            return {
                "error": "模型未加载",
                "is_correct": False,
                "score": 0,
                "feedback": "模型加载失败，请检查模型文件",
                "count": self.pushup_count
            }

class PlankAnalyzer(PoseAnalyzer):
    """平板支撑动作分析器 - 使用ML模型"""
    
    def __init__(self):
        super().__init__(exercise_type='plank')
        # 保留持续时间状态
        self.plank_duration = 0
        self.last_duration = 0.0
    
    def is_pose_visible(self, landmarks: List[Dict]) -> bool:
        """检查平板支撑所需关键点是否可见"""
        # 平板支撑主要关键点：肩部和肘部
        if len(landmarks) < 15:
            return False
            
        required_landmarks = [11, 12, 13, 14]  # 左右肩部和肘部
        
        # 检查至少一侧的肩部和肘部可见
        left_visible = landmarks[11].get('visibility', 0) >= self.min_detection_confidence and \
                    landmarks[13].get('visibility', 0) >= self.min_detection_confidence
        
        right_visible = landmarks[12].get('visibility', 0) >= self.min_detection_confidence and \
                     landmarks[14].get('visibility', 0) >= self.min_detection_confidence
        
        return left_visible or right_visible
        
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析平板支撑动作 - 使用ML模型
        
        Args:
            landmarks: MediaPipe姿态关键点
            
        Returns:
            Dict: 分析结果
        """
        if not self.is_pose_visible(landmarks):
            return {
                "error": "姿态不可见",
                "is_correct": False,
                "score": 0,
                "feedback": "请确保上半身在摄像头范围内",
                "duration": self.plank_duration / 30  # 转换为秒（假设30fps）
            }
        
        # 如果模型已加载，使用模型进行预测
        if self.model:
            try:
                result = self.model.predict(landmarks)
                
                # 更新持续时间（如果模型返回的是秒数，需要转换）
                if "duration" in result:
                    model_duration = result.get("duration", 0.0)
                    # 如果模型返回的持续时间大于上次记录，更新
                    if model_duration > self.last_duration:
                        self.plank_duration = int(model_duration * 30)  # 转换为帧数
                        self.last_duration = model_duration
                    else:
                        # 使用当前持续时间
                        result["duration"] = self.plank_duration / 30
                
                return result
                
            except Exception as e:
                self.logger.error(f"模型预测失败: {str(e)}")
                return {
                    "error": f"模型预测失败: {str(e)}",
                    "is_correct": False,
                    "score": 0,
                    "feedback": "动作分析出错，请重试",
                    "duration": self.plank_duration / 30
                }
        else:
            return {
                "error": "模型未加载",
                "is_correct": False,
                "score": 0,
                "feedback": "模型加载失败，请检查模型文件",
                "duration": self.plank_duration / 30
            }

class JumpingJackAnalyzer(PoseAnalyzer):
    """开合跳动作分析器 - 使用ML模型"""
    
    def __init__(self):
        super().__init__(exercise_type='jumping_jack')
        # 保留计数状态
        self.jump_count = 0
        self.last_count = 0
    
    def is_pose_visible(self, landmarks: List[Dict], required_landmarks=None) -> bool:
        """检查开合跳所需关键点是否可见"""
        # 开合跳主要关键点：肩部和手腕
        if required_landmarks is not None:
            return super().is_pose_visible(landmarks, required_landmarks)
        
        if len(landmarks) < 17:
            return False
            
        required_landmarks = [11, 12, 15, 16]  # 左右肩部和手腕
        
        # 检查肩部必须可见
        shoulders_visible = landmarks[11].get('visibility', 0) >= self.min_detection_confidence and \
                          landmarks[12].get('visibility', 0) >= self.min_detection_confidence
        
        # 至少一只手腕可见
        wrists_visible = landmarks[15].get('visibility', 0) >= self.min_detection_confidence or \
                       landmarks[16].get('visibility', 0) >= self.min_detection_confidence
        
        return shoulders_visible and wrists_visible
    
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析开合跳动作 - 使用ML模型
        
        Args:
            landmarks: MediaPipe姿态关键点
            
        Returns:
            Dict: 分析结果
        """
        if not self.is_pose_visible(landmarks):
            return {
                "error": "姿态不可见",
                "is_correct": False,
                "score": 0,
                "feedback": "请确保上半身在摄像头范围内",
                "count": self.jump_count
            }
        
        # 如果模型已加载，使用模型进行预测
        if self.model:
            try:
                result = self.model.predict(landmarks)
                
                # 更新计数
                if "count" in result:
                    model_count = result.get("count", 0)
                    if model_count > self.last_count:
                        self.jump_count = model_count
                        self.last_count = model_count
                    else:
                        result["count"] = self.jump_count
                
                return result
                
            except Exception as e:
                self.logger.error(f"模型预测失败: {str(e)}")
                return {
                    "error": f"模型预测失败: {str(e)}",
                    "is_correct": False,
                    "score": 0,
                    "feedback": "动作分析出错，请重试",
                    "count": self.jump_count
                }
        else:
            return {
                "error": "模型未加载",
                "is_correct": False,
                "score": 0,
                "feedback": "模型加载失败，请检查模型文件",
                "count": self.jump_count
            }

def create_analyzer(exercise_type: str) -> PoseAnalyzer:
    """
    根据运动类型创建对应的分析器
    
    Args:
        exercise_type: 运动类型 ('squat', 'pushup', 'plank', 'jumping_jack')
        
    Returns:
        PoseAnalyzer: 对应的分析器实例
    """
    analyzers = {
        'squat': SquatAnalyzer,
        'pushup': PushupAnalyzer,
        'plank': PlankAnalyzer,
        'jumping_jack': JumpingJackAnalyzer
    }
    
    analyzer_class = analyzers.get(exercise_type, SquatAnalyzer)
    return analyzer_class()

# 使用示例
if __name__ == "__main__":
    # 创建深蹲分析器
    analyzer = create_analyzer('squat')
    
    # 模拟姿态数据
    sample_landmarks = [{"x": 0.5, "y": 0.5, "z": 0.1} for _ in range(33)]
    
    # 进行分析
    result = analyzer.analyze(sample_landmarks)
    print("分析结果:", result) 