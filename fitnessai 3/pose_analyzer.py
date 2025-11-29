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
    """姿态分析器基类"""
    
    def __init__(self):
        self.min_detection_confidence = 0.5
        self.min_tracking_confidence = 0.5
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def calculate_angle(self, point1: Dict, point2: Dict, point3: Dict) -> float:
        """
        计算三个点之间的角度
        
        Args:
            point1, point2, point3: 包含x, y坐标的字典
            
        Returns:
            float: 角度值（度）
        """
        try:
            # 提取坐标
            a = np.array([point1['x'], point1['y']])
            b = np.array([point2['x'], point2['y']])
            c = np.array([point3['x'], point3['y']])
            
            # 计算向量
            ba = a - b
            bc = c - b
            
            # 计算夹角
            cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
            # 防止数值误差导致的域错误
            cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
            angle = np.degrees(np.arccos(cosine_angle))
            
            self.logger.debug(f"计算角度: {angle:.2f}度 (点1: {point1}, 点2: {point2}, 点3: {point3})")
            return angle
        except Exception as e:
            self.logger.error(f"角度计算错误: {e}")
            return 180.0  # 返回默认值
    
    def calculate_distance(self, point1: Dict, point2: Dict) -> float:
        """
        计算两点之间的距离
        
        Args:
            point1, point2: 包含x, y坐标的字典
            
        Returns:
            float: 距离值
        """
        try:
            return math.sqrt((point1['x'] - point2['x'])**2 + (point1['y'] - point2['y'])**2)
        except Exception:
            return 0.0
    
    def is_pose_visible(self, landmarks: List[Dict]) -> bool:
        """
        检查姿态关键点是否可见
        
        Args:
            landmarks: MediaPipe姿态关键点列表
            
        Returns:
            bool: 姿态是否可见
        """
        if not landmarks or len(landmarks) < 33:
            self.logger.warning(f"关键点数量不足: {len(landmarks) if landmarks else 0}")
            return False
        
        # 检查关键关节点的可见性
        key_points = [11, 12, 23, 24, 25, 26, 27, 28]  # 肩膀、髋部、膝盖、脚踝
        invisible_points = []
        for idx in key_points:
            if idx >= len(landmarks):
                self.logger.warning(f"关键点索引超出范围: {idx}")
                return False
            if landmarks[idx].get('visibility', 0) < self.min_detection_confidence:
                invisible_points.append(idx)
        
        if invisible_points:
            self.logger.warning(f"以下关键点可见度不足: {invisible_points}")
            return False
        
        return True

class SquatAnalyzer(PoseAnalyzer):
    """深蹲动作分析器"""
    
    def __init__(self):
        super().__init__()
        self.squat_count = 0
        self.in_squat_position = False
        self.squat_threshold_angle = 90  # 深蹲角度阈值
        self.up_threshold_angle = 160   # 起立角度阈值
        self.last_state = "up"  # up, down
        self.consecutive_correct_frames = 0
        self.required_frames = 2  # 需要连续2帧才算一次完整动作（降低要求）
        
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        分析深蹲动作
        
        Args:
            landmarks: MediaPipe姿态关键点
            
        Returns:
            Dict: 分析结果
        """
        self.logger.info("开始分析深蹲动作...")
        
        if not self.is_pose_visible(landmarks):
            self.logger.warning("姿态不可见")
            return {
                "error": "姿态不可见",
                "is_correct": False,
                "score": 0,
                "feedback": "请确保全身在摄像头范围内",
                "count": self.squat_count
            }
            
        try:
            # MediaPipe 关键点索引
            # 23: 左髋, 24: 右髋, 25: 左膝, 26: 右膝, 27: 左踝, 28: 右踝
            # 11: 左肩, 12: 右肩
            
            left_hip = landmarks[23]
            right_hip = landmarks[24]
            left_knee = landmarks[25]
            right_knee = landmarks[26]
            left_ankle = landmarks[27]
            right_ankle = landmarks[28]
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            
            # 计算膝盖角度（髋-膝-踝）
            left_knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
            right_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
            avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
            
            # 计算髋部角度（肩-髋-膝）
            left_hip_angle = self.calculate_angle(left_shoulder, left_hip, left_knee)
            right_hip_angle = self.calculate_angle(right_shoulder, right_hip, right_knee)
            avg_hip_angle = (left_hip_angle + right_hip_angle) / 2
            
            self.logger.info(f"平均膝盖角度: {avg_knee_angle:.2f}°, 平均髋部角度: {avg_hip_angle:.2f}°")
            
            # 检查背部是否挺直
            back_straight = self._check_back_posture(left_shoulder, right_shoulder, left_hip, right_hip)
            self.logger.info(f"背部姿态: {'正确' if back_straight else '不正确'}")
            
            # 动作状态检测
            current_state = self._detect_squat_state(avg_knee_angle)
            self.logger.info(f"当前状态: {current_state} (上一状态: {self.last_state})")
            is_correct, feedback = self._evaluate_squat_form(avg_knee_angle, avg_hip_angle, back_straight)
            
            # 计数逻辑
            count_updated = self._update_count(current_state, is_correct)
            if count_updated:
                self.logger.info(f"计数更新: {self.squat_count}")
            
            # 计算得分
            score = self._calculate_squat_score(avg_knee_angle, avg_hip_angle, back_straight)
            
            # 生成反馈
            detailed_feedback = self._generate_feedback(avg_knee_angle, avg_hip_angle, back_straight, current_state)
            
            result = {
                "is_correct": is_correct,
                "score": score,
                "feedback": detailed_feedback,
                "count": self.squat_count,
                "accuracy": self.squat_count / max(1, self.consecutive_correct_frames // self.required_frames + self.squat_count),
                "details": {
                    "knee_angle": round(avg_knee_angle, 1),
                    "hip_angle": round(avg_hip_angle, 1),
                    "back_straight": back_straight,
                    "state": current_state
                }
            }
            
            self.logger.info(f"分析结果: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"分析过程出错: {e}", exc_info=True)
            return {
                "error": f"分析失败: {str(e)}",
                "is_correct": False,
                "score": 0,
                "feedback": "动作分析出错，请重试",
                "count": self.squat_count
            }
    
    def _detect_squat_state(self, knee_angle: float) -> str:
        """检测深蹲状态"""
        if knee_angle < self.squat_threshold_angle:
            return "down"
        elif knee_angle > self.up_threshold_angle:
            return "up"
        else:
            return "transition"
    
    def _check_back_posture(self, left_shoulder: Dict, right_shoulder: Dict, 
                           left_hip: Dict, right_hip: Dict) -> bool:
        """检查背部姿态是否正确"""
        try:
            # 计算肩膀中点和髋部中点
            shoulder_mid = {
                'x': (left_shoulder['x'] + right_shoulder['x']) / 2,
                'y': (left_shoulder['y'] + right_shoulder['y']) / 2
            }
            hip_mid = {
                'x': (left_hip['x'] + right_hip['x']) / 2,
                'y': (left_hip['y'] + right_hip['y']) / 2
            }
            
            # 计算背部倾斜角度
            back_angle = math.atan2(abs(shoulder_mid['x'] - hip_mid['x']), 
                                  abs(shoulder_mid['y'] - hip_mid['y']))
            back_angle_degrees = math.degrees(back_angle)
            
            # 背部角度应该在合理范围内（不能过度前倾）
            return back_angle_degrees < 30  # 允许30度以内的前倾
        except Exception:
            return True  # 如果计算失败，默认认为正确
    
    def _evaluate_squat_form(self, knee_angle: float, hip_angle: float, back_straight: bool) -> Tuple[bool, str]:
        """评估深蹲动作正确性"""
        issues = []
        
        if knee_angle > self.squat_threshold_angle and self.last_state == "down":
            issues.append("蹲得不够深")
        
        if not back_straight:
            issues.append("背部过度前倾")
        
        if hip_angle < 70:  # 髋部弯曲过度
            issues.append("髋部弯曲过度")
        
        is_correct = len(issues) == 0
        feedback = "动作标准！" if is_correct else ", ".join(issues)
        
        return is_correct, feedback
    
    def _update_count(self, current_state: str, is_correct: bool) -> bool:
        """更新计数"""
        count_updated = False
        
        # 状态转换逻辑：从up到down再到up算一次完整动作
        if self.last_state == "up" and current_state == "down":
            self.in_squat_position = True
            self.consecutive_correct_frames = 0  # 重置计数
        elif self.last_state == "down" and current_state == "up" and self.in_squat_position:
            # 不再要求动作必须完全正确，只要完成了下蹲和起立动作就计数
            self.squat_count += 1
            count_updated = True
            self.in_squat_position = False
            self.consecutive_correct_frames = 0
        elif current_state == "down" and is_correct:
            # 在下蹲状态时累计正确帧数
            self.consecutive_correct_frames += 1
        
        self.last_state = current_state
        return count_updated
    
    def _calculate_squat_score(self, knee_angle: float, hip_angle: float, back_straight: bool) -> int:
        """计算深蹲得分"""
        base_score = 100
        
        # 膝盖角度评分
        if knee_angle > self.squat_threshold_angle:
            base_score -= min(30, (knee_angle - self.squat_threshold_angle) * 0.5)
        
        # 髋部角度评分
        if hip_angle < 70:
            base_score -= min(20, (70 - hip_angle) * 0.3)
        
        # 背部姿态评分
        if not back_straight:
            base_score -= 25
            
        return max(0, min(100, int(base_score)))
    
    def _generate_feedback(self, knee_angle: float, hip_angle: float, 
                          back_straight: bool, state: str) -> str:
        """生成详细反馈"""
        if state == "up":
            return "准备下蹲"
        elif state == "transition":
            return "继续下蹲"
        elif state == "down":
            feedback_parts = []
            if knee_angle > self.squat_threshold_angle:
                feedback_parts.append("蹲得更低")
            if not back_straight:
                feedback_parts.append("保持背部挺直")
            if not feedback_parts:
                feedback_parts.append("动作到位，准备起立")
            return "，".join(feedback_parts)
        
        return "保持动作"

class PushupAnalyzer(PoseAnalyzer):
    """俯卧撑动作分析器"""
    
    def __init__(self):
        super().__init__()
        self.pushup_count = 0
        self.in_down_position = False
        self.arm_bend_threshold = 90  # 手臂弯曲角度阈值
        self.arm_straight_threshold = 160  # 手臂伸直角度阈值
        self.last_state = "up"
        
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
                "feedback": "请确保全身在摄像头范围内",
                "count": self.pushup_count
            }
        
        try:
            # MediaPipe 关键点索引
            # 11: 左肩, 12: 右肩, 13: 左肘, 14: 右肘, 15: 左腕, 16: 右腕
            # 23: 左髋, 24: 右髋, 27: 左踝, 28: 右踝
            
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_elbow = landmarks[13]
            right_elbow = landmarks[14]
            left_wrist = landmarks[15]
            right_wrist = landmarks[16]
            left_hip = landmarks[23]
            right_hip = landmarks[24]
            left_ankle = landmarks[27]
            right_ankle = landmarks[28]
            
            # 计算手臂角度（肩-肘-腕）
            left_arm_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
            right_arm_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)
            avg_arm_angle = (left_arm_angle + right_arm_angle) / 2
            
            # 检查身体直线度
            body_straight = self._check_body_alignment(left_shoulder, right_shoulder, 
                                                     left_hip, right_hip, 
                                                     left_ankle, right_ankle)
            
            # 动作状态检测
            current_state = self._detect_pushup_state(avg_arm_angle)
            
            # 计数逻辑
            count_updated = self._update_pushup_count(current_state, body_straight)
            
            # 评估动作正确性
            is_correct = body_straight and (current_state in ["up", "down"])
            
            # 计算得分
            score = self._calculate_pushup_score(avg_arm_angle, body_straight)
            
            # 生成反馈
            feedback = self._generate_pushup_feedback(avg_arm_angle, body_straight, current_state)
            
            return {
                "is_correct": is_correct,
                "score": score,
                "feedback": feedback,
                "count": self.pushup_count,
                "accuracy": 0.85,  # 简化的准确率计算
                "details": {
                    "arm_angle": round(avg_arm_angle, 1),
                    "body_straight": body_straight,
                    "state": current_state
                }
            }
            
        except Exception as e:
            return {
                "error": f"分析失败: {str(e)}",
                "is_correct": False,
                "score": 0,
                "feedback": "动作分析出错，请重试",
                "count": self.pushup_count
            }
    
    def _check_body_alignment(self, left_shoulder: Dict, right_shoulder: Dict,
                            left_hip: Dict, right_hip: Dict,
                            left_ankle: Dict, right_ankle: Dict) -> bool:
        """检查身体是否保持直线"""
        try:
            # 计算各部位中点
            shoulder_mid_y = (left_shoulder['y'] + right_shoulder['y']) / 2
            hip_mid_y = (left_hip['y'] + right_hip['y']) / 2
            ankle_mid_y = (left_ankle['y'] + right_ankle['y']) / 2
            
            # 检查肩膀、髋部、脚踝是否大致在一条直线上
            shoulder_hip_diff = abs(shoulder_mid_y - hip_mid_y)
            hip_ankle_diff = abs(hip_mid_y - ankle_mid_y)
            
            # 允许一定的偏差
            max_deviation = 0.1  # 根据实际测试调整
            return shoulder_hip_diff < max_deviation and hip_ankle_diff < max_deviation
        except Exception:
            return True
    
    def _detect_pushup_state(self, arm_angle: float) -> str:
        """检测俯卧撑状态"""
        if arm_angle < self.arm_bend_threshold:
            return "down"
        elif arm_angle > self.arm_straight_threshold:
            return "up"
        else:
            return "transition"
    
    def _update_pushup_count(self, current_state: str, body_straight: bool) -> bool:
        """更新俯卧撑计数"""
        count_updated = False
        
        if (self.last_state == "up" and current_state == "down" and 
            body_straight):
            self.in_down_position = True
        elif (self.last_state == "down" and current_state == "up" and 
              self.in_down_position and body_straight):
            self.pushup_count += 1
            count_updated = True
            self.in_down_position = False
        
        self.last_state = current_state
        return count_updated
    
    def _calculate_pushup_score(self, arm_angle: float, body_straight: bool) -> int:
        """计算俯卧撑得分"""
        base_score = 100
        
        # 手臂角度评分
        if arm_angle > self.arm_bend_threshold and self.last_state == "down":
            base_score -= min(30, (arm_angle - self.arm_bend_threshold) * 0.3)
        
        # 身体直线度评分
        if not body_straight:
            base_score -= 40
        
        return max(0, min(100, int(base_score)))
    
    def _generate_pushup_feedback(self, arm_angle: float, body_straight: bool, 
                                state: str) -> str:
        """生成俯卧撑反馈"""
        feedback_parts = []
        
        if not body_straight:
            feedback_parts.append("保持身体挺直")
        
        if state == "up":
            feedback_parts.append("准备下降")
        elif state == "down":
            if arm_angle > self.arm_bend_threshold:
                feedback_parts.append("下降得更低")
            else:
                feedback_parts.append("准备推起")
        elif state == "transition":
            feedback_parts.append("继续动作")
        
        if not feedback_parts:
            feedback_parts.append("动作标准")
        
        return "，".join(feedback_parts)

class PlankAnalyzer(PoseAnalyzer):
    """平板支撑分析器"""
    
    def __init__(self):
        super().__init__()
        self.hold_time = 0
        self.start_time = None
        self.is_in_position = False
        
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """分析平板支撑动作"""
        if not self.is_pose_visible(landmarks):
            return {
                "error": "姿态不可见",
                "is_correct": False,
                "score": 0,
                "feedback": "请确保全身在摄像头范围内",
                "count": 0
            }
        
        # 简化实现
        return {
            "is_correct": True,
            "score": 90,
            "feedback": "保持平板支撑",
            "count": 0,
            "accuracy": 0.9
        }

class JumpingJackAnalyzer(PoseAnalyzer):
    """开合跳分析器"""
    
    def __init__(self):
        super().__init__()
        self.jump_count = 0
        self.last_arms_state = "down"
        self.last_legs_state = "together"
        
    def analyze(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """分析开合跳动作"""
        if not self.is_pose_visible(landmarks):
            return {
                "error": "姿态不可见",
                "is_correct": False,
                "score": 0,
                "feedback": "请确保全身在摄像头范围内",
                "count": self.jump_count
            }
        
        # 简化实现
        return {
            "is_correct": True,
            "score": 85,
            "feedback": "继续开合跳",
            "count": self.jump_count,
            "accuracy": 0.85
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