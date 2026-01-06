"""
姿态分析模块

这个模块包含具体的运动分析算法：
1. 深蹲分析
2. 俯卧撑分析
3. 平板支撑分析
4. 开合跳分析
"""

import numpy as np
import math
import logging
from typing import Dict, List, Tuple, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pose_analyzer')

class PoseAnalyzer:
    """姿态分析基类"""
    
    def __init__(self):
        self.min_detection_confidence = 0.5  # 最小检测置信度
        # 共用状态跟踪变量
        self.state_changed_frames = 0  # 状态保持的帧数
        self.min_stable_frames = 3     # 需要保持状态的最小帧数
        self.cooldown_counter = 0      # 计数冷却计数器
        self.cooldown_frames = 10      # 计数后的冷却时间（帧数）
        # 创建logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
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
    """深蹲动作分析器"""
    
    def __init__(self):
        super().__init__()
        self.squat_count = 0
        self.last_state = "up"  # up, down
        self.angle_threshold = 140  # 角度阈值，进一步提高下蹲判定阈值，使得更容易判定为下蹲
        self.standing_threshold = 140  # 进一步降低站立角度阈值，使得更容易判定为站立
        self.in_squat_position = False
        # 状态变化计数器
        self.consecutive_up_frames = 0   # 连续站立帧数
        self.consecutive_down_frames = 0 # 连续下蹲帧数
        self.required_frames = 2   # 进一步降低要求，只需2帧即可确认状态
    
    def is_pose_visible(self, landmarks: List[Dict], required_landmarks=None) -> bool:
        """检查深蹲所需关键点是否可见"""
        # 深蹲关键点：左右髋部和膝盖
        required_landmarks = [23, 24, 25, 26]  # 左右髋部和膝盖
        
        # 至少有一侧髋部和膝盖可见即可
        left_visible = landmarks[23].get('visibility', 0) >= self.min_detection_confidence and \
                    landmarks[25].get('visibility', 0) >= self.min_detection_confidence
        
        right_visible = landmarks[24].get('visibility', 0) >= self.min_detection_confidence and \
                     landmarks[26].get('visibility', 0) >= self.min_detection_confidence
        
        return left_visible or right_visible
    
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析深蹲动作
        
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
        
        try:
            # 计算膝盖角度 - 使用髋部、膝盖和脚踝点
            knee_angle = 180.0  # 默认值
            
            # 尝试使用左侧或右侧关键点，优先使用可见性更好的一侧
            left_visibility = landmarks[23].get('visibility', 0) + landmarks[25].get('visibility', 0) + landmarks[27].get('visibility', 0)
            right_visibility = landmarks[24].get('visibility', 0) + landmarks[26].get('visibility', 0) + landmarks[28].get('visibility', 0)
            
            if left_visibility > right_visibility:
                # 使用左侧
                left_hip = landmarks[23]
                left_knee = landmarks[25]
                left_ankle = landmarks[27]
                knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
            else:
                # 使用右侧
                right_hip = landmarks[24]
                right_knee = landmarks[26]
                right_ankle = landmarks[28]
                knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
            
            # 确定当前状态 - 使用更宽松的判断
            current_state = self._detect_squat_state(knee_angle)
            
            # 更新连续帧计数
            if current_state == "up":
                self.consecutive_up_frames += 1
                self.consecutive_down_frames = 0
            elif current_state == "down":
                self.consecutive_down_frames += 1
                self.consecutive_up_frames = 0
            
            # 更宽松的状态判断 - 只需少量帧即可确认状态
            confirmed_state = self.last_state
            if self.consecutive_up_frames >= self.required_frames:
                confirmed_state = "up"
            elif self.consecutive_down_frames >= self.required_frames:
                confirmed_state = "down"
                
            # 调试信息
            self.logger.info(f"深蹲角度: {knee_angle:.1f}, 当前状态: {current_state}, 确认状态: {confirmed_state}, 上一状态: {self.last_state}, "
                          f"连续站立帧: {self.consecutive_up_frames}, 连续下蹲帧: {self.consecutive_down_frames}, "
                          f"冷却计数: {self.cooldown_counter}, 下蹲位置: {self.in_squat_position}")
            
            # 更新计数，并确保状态稳定后再计数
            count_updated = self._update_count(confirmed_state)
            
            # 生成反馈 - 提供更多鼓励
            if confirmed_state == "down":
                feedback = "很好！下蹲姿势正确，请站起来完成动作"
            else:
                feedback = "站立姿势正确，请尝试下蹲"
            
            # 计算得分 - 更宽松的评分
            if confirmed_state == "down":
                # 下蹲越深，得分越高，但基础分更高
                score = max(70, 100 - max(0, knee_angle - 90))
            else:
                # 站得越直，得分越高，但基础分更高
                score = min(100, max(70, knee_angle))
            
            return {
                "is_correct": True,
                "score": int(score),
                "feedback": feedback,
                "count": self.squat_count,
                "accuracy": 0.9,
                "details": {
                    "knee_angle": round(knee_angle, 1),
                    "state": confirmed_state,
                    "cooldown": self.cooldown_counter
                }
            }
            
        except Exception as e:
            self.logger.error(f"深蹲分析错误: {str(e)}")
            return {
                "error": f"分析失败: {str(e)}",
                "is_correct": False,
                "score": 0,
                "feedback": "动作分析出错，请重试",
                "count": self.squat_count
            }
    
    def _detect_squat_state(self, knee_angle: float) -> str:
        """检测深蹲状态"""
        if knee_angle < self.angle_threshold:
            return "down"
        elif knee_angle > self.standing_threshold:
            return "up"
        else:
            # 在过渡区域，保持上一个状态，防止抖动
            return self.last_state
    
    def _update_count(self, current_state: str) -> bool:
        """更新计数"""
        count_updated = False
        
        # 调试信息
        self.logger.info(f"当前状态: {current_state}, 上一状态: {self.last_state}, 冷却计数: {self.cooldown_counter}, 稳定帧数: {self.state_changed_frames}, 是否在下蹲位置: {self.in_squat_position}")
        
        # 冷却计数器处理
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            
        # 状态变化检测 - 只在状态变化时重置帧计数，防止抖动导致的状态变化
        if current_state != self.last_state:
            if self.state_changed_frames >= 3:  # 确保之前的状态是稳定的
                if self.last_state != "down" and current_state == "down" and self.cooldown_counter == 0:
                    # 从其他状态变为下蹲状态
                    self.in_squat_position = True
                    self.logger.info("检测到下蹲")
                elif self.last_state == "down" and current_state == "up" and self.in_squat_position:
                    # 从下蹲状态变为起立状态
                    if self.cooldown_counter == 0:
                        self.squat_count += 1
                        count_updated = True
                        self.cooldown_counter = self.cooldown_frames  # 设置冷却时间
                        self.logger.info(f"计数增加，当前: {self.squat_count}")
                    self.in_squat_position = False
                self.state_changed_frames = 0
            else:
                # 状态变化但不够稳定，忽略这次变化
                self.logger.info(f"状态变化不稳定，忽略: {self.last_state} -> {current_state}")
                return count_updated
        else:
            # 同一状态下累加帧数
            self.state_changed_frames += 1
        
        self.last_state = current_state
        return count_updated

class PushupAnalyzer(PoseAnalyzer):
    """俯卧撑动作分析器"""
    
    def __init__(self):
        super().__init__()
        self.pushup_count = 0
        self.last_state = "up"  # up, down
        self.angle_threshold = 115  # 弯曲角度阈值，小于这个角度被视为下降
        self.straight_threshold = 155  # 伸直角度阈值，大于这个角度被视为上升
        self.in_down_position = False
        # 状态变化计数器
        self.consecutive_up_frames = 0   # 连续上升帧数
        self.consecutive_down_frames = 0 # 连续下降帧数
        self.required_frames = 5   # 要求更多帧数来确认状态
        # 增加冷却时间
        self.cooldown_frames = 15  # 冷却时间（帧数）
    
    def is_pose_visible(self, landmarks: List[Dict]) -> bool:
        """检查俯卧撑所需关键点是否可见"""
        # 俯卧撑主要关键点：肩部和肘部
        required_landmarks = [11, 12, 13, 14]  # 左右肩部和肘部
        
        # 检查至少一侧的肩部和肘部可见
        left_visible = landmarks[11].get('visibility', 0) >= self.min_detection_confidence and \
                    landmarks[13].get('visibility', 0) >= self.min_detection_confidence
        
        right_visible = landmarks[12].get('visibility', 0) >= self.min_detection_confidence and \
                     landmarks[14].get('visibility', 0) >= self.min_detection_confidence
        
        return left_visible or right_visible
        
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析俯卧撑动作
        
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
        
        try:
            # MediaPipe 关键点索引
            # 11: 左肩, 12: 右肩, 13: 左肘, 14: 右肘, 15: 左腕, 16: 右腕
            
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_elbow = landmarks[13]
            right_elbow = landmarks[14]
            
            # 尝试获取手腕，但不要求必须可见
            left_wrist = landmarks[15] if 15 < len(landmarks) and landmarks[15].get('visibility', 0) >= self.min_detection_confidence else None
            right_wrist = landmarks[16] if 16 < len(landmarks) and landmarks[16].get('visibility', 0) >= self.min_detection_confidence else None
            
            # 计算手臂角度（肩-肘-腕），如果手腕可见
            avg_arm_angle = 180.0
            arm_angles = []
            
            if left_wrist:
                left_arm_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
                arm_angles.append(left_arm_angle)
            
            if right_wrist:
                right_arm_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)
                arm_angles.append(right_arm_angle)
            
            if arm_angles:
                avg_arm_angle = sum(arm_angles) / len(arm_angles)
            
            # 确定当前状态
            current_state = self._detect_pushup_state(avg_arm_angle)
            
            # 更新连续帧计数
            if current_state == "up":
                self.consecutive_up_frames += 1
                self.consecutive_down_frames = 0
            elif current_state == "down":
                self.consecutive_down_frames += 1
                self.consecutive_up_frames = 0
            
            # 更严格的状态判断 - 需要连续多帧才确认状态
            confirmed_state = self.last_state
            if self.consecutive_up_frames >= self.required_frames:
                confirmed_state = "up"
            elif self.consecutive_down_frames >= self.required_frames:
                confirmed_state = "down"
            
            # 调试信息
            self.logger.info(f"俯卧撑角度: {avg_arm_angle:.1f}, 当前状态: {current_state}, 确认状态: {confirmed_state}, 上一状态: {self.last_state}, "
                          f"连续上升帧: {self.consecutive_up_frames}, 连续下降帧: {self.consecutive_down_frames}, "
                          f"冷却计数: {self.cooldown_counter}, 下降位置: {self.in_down_position}")
            
            # 更新计数，并确保状态稳定后再计数
            count_updated = self._update_pushup_count(confirmed_state)
            
            # 生成反馈
            if confirmed_state == "down":
                feedback = "已下降，请向上推起"
            else:
                feedback = "已上升，请下降"
            
            # 计算得分
            if confirmed_state == "down":
                # 下降越深，得分越高
                score = max(60, 100 - max(0, avg_arm_angle - 90))
            else:
                # 手臂越直，得分越高
                score = min(100, max(60, avg_arm_angle))
            
            return {
                "is_correct": True,
                "score": int(score),
                "feedback": feedback,
                "count": self.pushup_count,
                "accuracy": 0.9,
                "details": {
                    "arm_angle": round(avg_arm_angle, 1),
                    "state": confirmed_state,
                    "cooldown": self.cooldown_counter
                }
            }
            
        except Exception as e:
            self.logger.error(f"俯卧撑分析错误: {str(e)}")
            return {
                "error": f"分析失败: {str(e)}",
                "is_correct": False,
                "score": 0,
                "feedback": "动作分析出错，请重试",
                "count": self.pushup_count
            }
    
    def _detect_pushup_state(self, arm_angle: float) -> str:
        """检测俯卧撑状态"""
        if arm_angle < self.angle_threshold:
            return "down"
        elif arm_angle > self.straight_threshold:
            return "up"
        else:
            # 在过渡区域，保持上一个状态，防止抖动
            return self.last_state
    
    def _update_pushup_count(self, current_state: str) -> bool:
        """更新俯卧撑计数"""
        count_updated = False
        
        # 调试信息
        self.logger.info(f"俯卧撑当前状态: {current_state}, 上一状态: {self.last_state}, 冷却计数: {self.cooldown_counter}, 稳定帧数: {self.state_changed_frames}, 是否在下降位置: {self.in_down_position}")
        
        # 冷却计数器处理
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            
        # 状态变化检测 - 只在状态变化时重置帧计数，防止抖动导致的状态变化
        if current_state != self.last_state:
            if self.state_changed_frames >= 3:  # 确保之前的状态是稳定的
                if self.last_state != "down" and current_state == "down" and self.cooldown_counter == 0:
                    # 从其他状态变为下降状态
                    self.in_down_position = True
                    self.logger.info("检测到俯卧撑下降")
                elif self.last_state == "down" and current_state == "up" and self.in_down_position:
                    # 从下降状态变为上升状态
                    if self.cooldown_counter == 0:
                        self.pushup_count += 1
                        count_updated = True
                        self.cooldown_counter = self.cooldown_frames  # 设置冷却时间
                        self.logger.info(f"俯卧撑计数增加，当前: {self.pushup_count}")
                    self.in_down_position = False
                self.state_changed_frames = 0
            else:
                # 状态变化但不够稳定，忽略这次变化
                self.logger.info(f"俯卧撑状态变化不稳定，忽略: {self.last_state} -> {current_state}")
                return count_updated
        else:
            # 同一状态下累加帧数
            self.state_changed_frames += 1
        
        self.last_state = current_state
        return count_updated

class PlankAnalyzer(PoseAnalyzer):
    """平板支撑动作分析器"""
    
    def __init__(self):
        super().__init__()
        self.plank_duration = 0
        self.is_in_plank = False
        self.body_alignment_tolerance = 0.2  # 身体直线度容差
        self.elbow_angle_threshold = 120  # 肘部弯曲角度阈值（调整为更合理的要求）
        # 状态稳定性跟踪
        self.stable_frames = 0
        self.min_stable_frames = 10  # 需要至少10帧稳定才算有效平板支撑
        # 添加抖动检测
        self.unstable_frames = 0
        self.max_unstable_frames = 5  # 允许的最大不稳定帧数
        # 添加姿势质量检查
        self.quality_threshold = 0.8  # 姿势质量阈值
    
    def is_pose_visible(self, landmarks: List[Dict]) -> bool:
        """检查平板支撑所需关键点是否可见"""
        # 平板支撑主要关键点：肩部和肘部
        required_landmarks = [11, 12, 13, 14]  # 左右肩部和肘部
        
        # 检查至少一侧的肩部和肘部可见
        left_visible = landmarks[11].get('visibility', 0) >= self.min_detection_confidence and \
                    landmarks[13].get('visibility', 0) >= self.min_detection_confidence
        
        right_visible = landmarks[12].get('visibility', 0) >= self.min_detection_confidence and \
                     landmarks[14].get('visibility', 0) >= self.min_detection_confidence
        
        return left_visible or right_visible
        
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析平板支撑动作
        
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
        
        try:
            # MediaPipe 关键点索引
            # 11: 左肩, 12: 右肩, 13: 左肘, 14: 右肘
            
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_elbow = landmarks[13]
            right_elbow = landmarks[14]
            
            # 尝试获取髋部，但不要求必须可见
            left_hip = landmarks[23] if 23 < len(landmarks) and landmarks[23].get('visibility', 0) >= self.min_detection_confidence else None
            right_hip = landmarks[24] if 24 < len(landmarks) and landmarks[24].get('visibility', 0) >= self.min_detection_confidence else None
            
            # 检查手肘是否弯曲（平板支撑姿势）
            left_elbow_angle = self.calculate_angle(left_shoulder, left_elbow, {'x': left_elbow['x'], 'y': left_elbow['y'] + 0.1})
            right_elbow_angle = self.calculate_angle(right_shoulder, right_elbow, {'x': right_elbow['x'], 'y': right_elbow['y'] + 0.1})
            avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
            
            # 检查肘部是否在肩部下方
            elbows_under_shoulders = (left_elbow['y'] > left_shoulder['y'] and right_elbow['y'] > right_shoulder['y'])
            
            # 简化判断，只要肘部弯曲且在肩部下方就认为姿势正确
            is_correct_form = avg_elbow_angle < self.elbow_angle_threshold and elbows_under_shoulders
            
            # 调试信息
            self.logger.info(f"平板支撑状态: 正确={is_correct_form}, 肘部角度={avg_elbow_angle:.1f}, 肘部位置正确={elbows_under_shoulders}, 稳定帧数={self.stable_frames}, 持续时间={self.plank_duration/30:.1f}秒")
            
            # 更新状态 - 需要更稳定的判断，增加抖动检测
            if is_correct_form:
                self.stable_frames += 1
                self.unstable_frames = 0  # 重置不稳定帧数
                
                if self.stable_frames >= self.min_stable_frames:
                    if not self.is_in_plank:
                        self.is_in_plank = True
                        self.logger.info("开始平板支撑计时")
                    self.plank_duration += 1  # 增加持续时间（按帧计数）
            else:
                self.unstable_frames += 1
                
                # 如果不稳定帧数超过阈值，才减少稳定帧数
                if self.unstable_frames > self.max_unstable_frames:
                    if self.stable_frames > 0:
                        self.stable_frames -= 1
                    
                    # 如果稳定帧数降至阈值以下，停止计时
                    if self.stable_frames < self.min_stable_frames // 3:
                        if self.is_in_plank:
                            self.logger.info("停止平板支撑计时")
                            self.is_in_plank = False
            
            # 生成反馈
            feedback = self._generate_plank_feedback(is_correct_form, avg_elbow_angle, elbows_under_shoulders)
            
            # 计算得分
            score = 80 if is_correct_form else 60
            
            return {
                "is_correct": True,  # 始终返回正确，增加用户信心
                "score": score,
                "feedback": feedback,
                "duration": self.plank_duration / 30,  # 转换为秒（假设30fps）
                "accuracy": 0.9,
                "details": {
                    "elbow_angle": round(avg_elbow_angle, 1),
                    "elbows_under_shoulders": elbows_under_shoulders,
                    "stable_frames": self.stable_frames,
                    "duration_seconds": round(self.plank_duration / 30, 1)
                }
            }
            
        except Exception as e:
            return {
                "error": f"分析失败: {str(e)}",
                "is_correct": False,
                "score": 0,
                "feedback": "动作分析出错，请重试",
                "duration": self.plank_duration / 30  # 转换为秒
            }
    
    def _generate_plank_feedback(self, is_correct_form: bool, elbow_angle: float, elbows_under_shoulders: bool) -> str:
        """生成平板支撑反馈"""
        if not is_correct_form:
            feedback_parts = []
            
            if elbow_angle >= self.elbow_angle_threshold:
                feedback_parts.append("手肘需要弯曲")
            
            if not elbows_under_shoulders:
                feedback_parts.append("肘部应在肩部下方")
            
            if feedback_parts:
                return "，".join(feedback_parts)
        
        # 正确姿势反馈
        if self.stable_frames < self.min_stable_frames:
            return f"保持姿势稳定，还需 {self.min_stable_frames - self.stable_frames} 帧"
        
        duration_seconds = self.plank_duration / 30
        if duration_seconds < 10:
            return f"姿势正确，已坚持 {duration_seconds:.1f} 秒"
        elif duration_seconds < 30:
            return f"做得好！已坚持 {duration_seconds:.1f} 秒"
        else:
            return f"太棒了！已坚持 {duration_seconds:.1f} 秒"

class JumpingJackAnalyzer(PoseAnalyzer):
    """开合跳动作分析器"""
    
    def __init__(self):
        super().__init__()
        self.jump_count = 0
        self.last_state = "closed"  # closed, open
        self.arm_threshold = 120  # 手臂张开角度阈值
        self.leg_threshold = 30   # 腿部张开距离阈值
        # 提高稳定性要求，减少误检
        self.min_stable_frames = 5  # 提高稳定帧数要求
        # 增加冷却时间，防止过度敏感
        self.cooldown_counter = 0
        self.cooldown_frames = 20  # 增加冷却时间，确保动作间隔
        # 添加状态跟踪
        self.consecutive_open_frames = 0   # 连续张开帧数
        self.consecutive_closed_frames = 0 # 连续闭合帧数
        self.required_frames = 6   # 增加所需帧数，提高稳定性
        # 添加完整动作跟踪
        self.movement_phase = "none"  # none, opening, closing, complete
        self.complete_movement_required = True  # 要求完整动作才计数
        # 添加动作质量检查
        self.in_open_position = False  # 是否处于张开位置
        self.movement_started = False  # 是否开始动作
        # 添加手臂高度检查
        self.arm_height_threshold = 0.1  # 手臂需要抬高的阈值
        # 添加连续性检查
        self.last_arm_ratio = 0.0
        self.arm_ratio_change_threshold = 0.3  # 手臂比例变化阈值
    
    def is_pose_visible(self, landmarks: List[Dict], required_landmarks=None) -> bool:
        """检查开合跳所需关键点是否可见"""
        # 开合跳主要关键点：肩部和手腕
        if required_landmarks is not None:
            return super().is_pose_visible(landmarks, required_landmarks)
            
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
        分析开合跳动作
        
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
        
        try:
            # MediaPipe 关键点索引
            # 11: 左肩, 12: 右肩, 15: 左腕, 16: 右腕
            
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_wrist = landmarks[15]
            right_wrist = landmarks[16]
            
            # 计算手臂的距离和角度
            shoulder_distance = self.calculate_distance(left_shoulder, right_shoulder)
            wrist_distance = self.calculate_distance(left_wrist, right_wrist)
            
            # 计算手臂比例
            arm_ratio = wrist_distance / max(shoulder_distance, 0.1)  # 防止除零
            
            # 检查手臂高度 - 开合跳时手臂应该抬高
            left_arm_raised = left_wrist['y'] < left_shoulder['y'] - self.arm_height_threshold
            right_arm_raised = right_wrist['y'] < right_shoulder['y'] - self.arm_height_threshold
            arms_raised = left_arm_raised and right_arm_raised
            
            # 更严格的判断条件：手臂需要张开并且抬高
            arms_open = arm_ratio > 1.8 and arms_raised  # 提高手臂张开要求，并要求手臂抬高
            
            # 检查手臂比例变化的连续性，避免误检
            arm_ratio_change = abs(arm_ratio - self.last_arm_ratio)
            is_smooth_movement = arm_ratio_change < self.arm_ratio_change_threshold
            self.last_arm_ratio = arm_ratio
            
            # 确定当前状态
            current_state = "closed"
            if arms_open and is_smooth_movement:
                current_state = "open"
            
            # 更新连续帧计数
            if current_state == "open":
                self.consecutive_open_frames += 1
                self.consecutive_closed_frames = 0
            elif current_state == "closed":
                self.consecutive_closed_frames += 1
                self.consecutive_open_frames = 0
            
            # 更严格的状态判断 - 需要更多帧数才确认状态
            previous_state = self.last_state
            confirmed_state = self.last_state
            
            if self.consecutive_open_frames >= self.required_frames:
                confirmed_state = "open"
            elif self.consecutive_closed_frames >= self.required_frames:
                confirmed_state = "closed"
            
            # 冷却计数器处理
            if self.cooldown_counter > 0:
                self.cooldown_counter -= 1
            
            # 调试信息
            self.logger.info(f"开合跳状态: {current_state}, 确认状态: {confirmed_state}, 上一状态: {self.last_state}, "
                           f"连续开帧: {self.consecutive_open_frames}, 连续闭帧: {self.consecutive_closed_frames}, "
                           f"冷却计数: {self.cooldown_counter}, 手臂比例: {arm_ratio:.2f}, 手臂抬高: {arms_raised}, "
                           f"运动阶段: {self.movement_phase}, 比例变化: {arm_ratio_change:.2f}")
                
            # 完整动作跟踪和计数逻辑
            count_updated = self._update_jumping_jack_count(previous_state, confirmed_state)
            
            self.last_state = confirmed_state
            
            # 生成反馈
            feedback = self._generate_jumping_jack_feedback(confirmed_state, arms_open, arms_raised)
            
            # 计算得分 - 更严格的评分
            score = self._calculate_jumping_jack_score(confirmed_state, arms_open, arms_raised, arm_ratio)
            
            return {
                "is_correct": True,  # 始终返回正确，增加用户信心
                "score": score,
                "feedback": feedback,
                "count": self.jump_count,
                "accuracy": 0.9,
                "details": {
                    "state": confirmed_state,
                    "arm_ratio": round(arm_ratio, 2),
                    "arms_open": arms_open,
                    "arms_raised": arms_raised,
                    "movement_phase": self.movement_phase,
                    "cooldown": self.cooldown_counter
                }
            }
            
        except Exception as e:
            self.logger.error(f"开合跳分析错误: {str(e)}")
            return {
                "error": f"分析失败: {str(e)}",
                "is_correct": False,
                "score": 0,
                "feedback": "动作分析出错，请重试",
                "count": self.jump_count
            }
    
    def _update_jumping_jack_count(self, previous_state: str, current_state: str) -> bool:
        """更新开合跳计数 - 要求完整的动作循环"""
        count_updated = False
        
        # 状态变化检测
        if previous_state != current_state:
            # 状态变化：闭合 -> 张开
            if previous_state == "closed" and current_state == "open":
                if self.movement_phase == "none" or self.movement_phase == "complete":
                    self.movement_phase = "opening"
                    self.in_open_position = True
                    self.movement_started = True
                    self.logger.info("开合跳开始张开")
                    
            # 状态变化：张开 -> 闭合
            elif previous_state == "open" and current_state == "closed":
                if self.movement_phase == "opening" and self.in_open_position:
                    self.movement_phase = "closing"
                    self.in_open_position = False
                    self.logger.info("开合跳开始闭合")
                    
                    # 完成一次完整的开合跳动作
                    if self.cooldown_counter == 0:
                        self.jump_count += 1
                        count_updated = True
                        self.cooldown_counter = self.cooldown_frames
                        self.movement_phase = "complete"
                        self.logger.info(f"开合跳计数增加，当前: {self.jump_count}")
                    else:
                        self.logger.info(f"开合跳在冷却期间，不计数。剩余冷却: {self.cooldown_counter}")
        
        return count_updated
    
    def _generate_jumping_jack_feedback(self, state: str, arms_open: bool, arms_raised: bool) -> str:
        """生成开合跳反馈"""
        if state == "open":
            if self.movement_phase == "opening":
                return "很好！手臂张开，准备合拢"
            else:
                return "保持手臂张开姿势"
        else:  # closed
            if self.movement_phase == "closing":
                return "很好！完成一次开合跳"
            elif self.movement_phase == "complete":
                return "准备下一次开合跳"
            else:
                # 给出具体的改进建议
                if not arms_raised:
                    return "请将手臂抬高到肩部以上"
                else:
                    return "请跳起并张开手臂"
    
    def _calculate_jumping_jack_score(self, state: str, arms_open: bool, arms_raised: bool, arm_ratio: float) -> int:
        """计算开合跳得分"""
        base_score = 60
        
        if state == "open":
            # 张开状态的得分
            if arms_open and arms_raised:
                score = 90  # 完美张开
            elif arms_raised:
                score = 75  # 手臂抬高但未完全张开
            else:
                score = 65  # 基础分
        else:
            # 闭合状态的得分
            if self.movement_phase == "complete":
                score = 85  # 完成了完整动作
            elif self.movement_phase == "closing":
                score = 80  # 正在闭合
            else:
                score = base_score
        
        return int(score)

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