"""
模型加载器

负责加载和管理PyTorch模型
"""

import os
import torch
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

class ExerciseModelInterface:
    """
    运动模型接口基类
    
    所有运动模型都应该实现这个接口
    """
    
    def __init__(self, model_path: str, model_name: str):
        """
        初始化模型
        
        Args:
            model_path: 模型文件路径
            model_name: 模型名称
        """
        self.model_path = model_path
        self.model_name = model_name
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self._load_model()
    
    def _load_model(self):
        """加载模型 - 子类需要实现"""
        raise NotImplementedError("子类必须实现 _load_model 方法")
    
    def predict(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        预测接口
        
        Args:
            landmarks: MediaPipe姿态关键点列表，每个关键点包含 x, y, z, visibility
            
        Returns:
            Dict: 分析结果，包含以下字段：
                - is_correct: bool, 动作是否正确
                - score: int, 得分 (0-100)
                - feedback: str, 反馈信息
                - count: int (对于计数类运动) 或 duration: float (对于计时类运动)
                - accuracy: float, 准确度
                - details: dict, 详细信息
        """
        raise NotImplementedError("子类必须实现 predict 方法")
    
    def _landmarks_to_tensor(self, landmarks: List[Dict]) -> torch.Tensor:
        """
        将landmarks转换为模型输入tensor
        
        Args:
            landmarks: MediaPipe姿态关键点列表
            
        Returns:
            torch.Tensor: 形状为 (1, num_features) 的tensor
        """
        # 提取关键点特征：x, y, z, visibility
        features = []
        for landmark in landmarks:
            features.extend([
                landmark.get('x', 0.0),
                landmark.get('y', 0.0),
                landmark.get('z', 0.0),
                landmark.get('visibility', 0.0)
            ])
        
        # 转换为numpy数组再转为tensor
        features_array = np.array(features, dtype=np.float32)
        tensor = torch.from_numpy(features_array).unsqueeze(0)  # 添加batch维度
        return tensor.to(self.device)


def load_exercise_model(exercise_type: str) -> Optional[ExerciseModelInterface]:
    """
    根据运动类型加载对应的模型
    
    Args:
        exercise_type: 运动类型 ('squat', 'pushup', 'plank', 'jumping_jack')
        
    Returns:
        ExerciseModelInterface: 模型实例，如果加载失败返回None
    """
    # 模型文件名映射
    model_files = {
        'squat': 'squat_model.pth',
        'pushup': 'pushup_model.pth',
        'plank': 'plank_model.pth',
        'jumping_jack': 'jumping_jack_model.pth'
    }
    
    if exercise_type not in model_files:
        logger.error(f"未知的运动类型: {exercise_type}")
        return None
    
    model_filename = model_files[exercise_type]
    
    # 获取绝对路径（ml_models目录）
    ml_models_dir = Path(__file__).parent
    full_model_path = ml_models_dir / model_filename
    
    if not full_model_path.exists():
        logger.warning(f"模型文件不存在: {full_model_path}")
        logger.warning(f"请确保模型文件已放置在: {full_model_path}")
        return None
    
    try:
        # 动态导入对应的模型类
        # 这里假设模型类已经实现，文件名为 {exercise_type}_model.py
        model_module_name = f"ml_models.{exercise_type}_model"
        
        # 尝试导入模型类
        try:
            import importlib
            model_module = importlib.import_module(model_module_name)
            # 处理 jumping_jack 的特殊情况
            if exercise_type == 'jumping_jack':
                class_name = "JumpingJackModel"
            else:
                class_name = f"{exercise_type.capitalize()}Model"
            model_class = getattr(model_module, class_name, None)
            
            if model_class is None:
                # 如果找不到类，使用通用接口
                logger.info(f"使用通用模型接口加载: {exercise_type}")
                model = GenericExerciseModel(str(full_model_path), exercise_type)
            else:
                model = model_class(str(full_model_path), exercise_type)
            
            logger.info(f"成功加载模型: {exercise_type} from {full_model_path}")
            return model
            
        except ImportError:
            # 如果模型文件不存在，使用通用接口
            logger.info(f"模型文件不存在，使用通用接口: {exercise_type}")
            model = GenericExerciseModel(str(full_model_path), exercise_type)
            return model
            
    except Exception as e:
        logger.error(f"加载模型失败: {exercise_type}, 错误: {str(e)}")
        return None


class GenericExerciseModel(ExerciseModelInterface):
    """
    通用模型接口
    
    如果具体的模型类不存在，使用这个通用接口
    假设模型是一个标准的PyTorch模型，输入是landmarks特征，输出是分析结果
    """
    
    def _load_model(self):
        """加载PyTorch模型"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"模型文件不存在: {self.model_path}")
                self.model = None
                return
            
            # 加载模型
            self.model = torch.load(self.model_path, map_location=self.device)
            self.model.eval()  # 设置为评估模式
            logger.info(f"成功加载模型: {self.model_path}")
            
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            self.model = None
    
    def predict(self, landmarks: List[Dict]) -> Dict[str, Any]:
        """
        使用模型进行预测
        
        Args:
            landmarks: MediaPipe姿态关键点列表
            
        Returns:
            Dict: 分析结果
        """
        if self.model is None:
            return {
                "error": "模型未加载",
                "is_correct": False,
                "score": 0,
                "feedback": "模型加载失败，请检查模型文件",
                "count": 0,
                "accuracy": 0.0
            }
        
        try:
            # 转换为tensor
            input_tensor = self._landmarks_to_tensor(landmarks)
            
            # 模型推理
            with torch.no_grad():
                output = self.model(input_tensor)
            
            # 将输出转换为字典格式
            # 假设模型输出是一个字典或可以转换为字典的格式
            if isinstance(output, dict):
                result = output
            elif isinstance(output, torch.Tensor):
                # 如果输出是tensor，需要根据具体模型结构解析
                # 这里提供一个通用的解析方式
                result = self._parse_tensor_output(output)
            else:
                # 如果输出是其他格式，尝试转换
                result = self._parse_output(output)
            
            # 确保返回格式符合接口要求
            return self._format_output(result)
            
        except Exception as e:
            logger.error(f"模型预测失败: {str(e)}")
            return {
                "error": f"预测失败: {str(e)}",
                "is_correct": False,
                "score": 0,
                "feedback": "动作分析出错，请重试",
                "count": 0,
                "accuracy": 0.0
            }
    
    def _parse_tensor_output(self, output: torch.Tensor) -> Dict[str, Any]:
        """
        解析tensor输出
        
        这个方法需要根据具体模型输出格式调整
        """
        # 将tensor转换为numpy
        output_np = output.cpu().numpy()
        
        # 假设输出格式：[is_correct, score, count, accuracy, ...]
        # 这里需要根据实际模型输出调整
        result = {
            "is_correct": bool(output_np[0] > 0.5) if len(output_np) > 0 else True,
            "score": int(output_np[1] * 100) if len(output_np) > 1 else 80,
            "count": int(output_np[2]) if len(output_np) > 2 else 0,
            "accuracy": float(output_np[3]) if len(output_np) > 3 else 0.9,
        }
        
        return result
    
    def _parse_output(self, output: Any) -> Dict[str, Any]:
        """
        解析模型输出
        
        尝试将各种格式的输出转换为字典
        """
        if isinstance(output, dict):
            return output
        elif hasattr(output, '__dict__'):
            return output.__dict__
        else:
            # 默认返回
            return {
                "is_correct": True,
                "score": 80,
                "count": 0,
                "accuracy": 0.9
            }
    
    def _format_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化输出，确保符合接口要求
        
        Args:
            result: 模型原始输出
            
        Returns:
            Dict: 格式化后的输出
        """
        # 确保必要字段存在
        formatted = {
            "is_correct": result.get("is_correct", True),
            "score": int(result.get("score", 80)),
            "feedback": result.get("feedback", "动作正确"),
            "accuracy": float(result.get("accuracy", 0.9)),
            "details": result.get("details", {})
        }
        
        # 根据运动类型添加count或duration
        if "count" in result:
            formatted["count"] = int(result.get("count", 0))
        if "duration" in result:
            formatted["duration"] = float(result.get("duration", 0.0))
        
        # 如果有错误信息
        if "error" in result:
            formatted["error"] = result["error"]
            formatted["is_correct"] = False
        
        return formatted

