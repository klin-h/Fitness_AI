"""
ML模型模块

这个模块包含运动分析的PyTorch模型加载和调用接口
"""

from .model_loader import load_exercise_model, ExerciseModelInterface

__all__ = ['load_exercise_model', 'ExerciseModelInterface']

