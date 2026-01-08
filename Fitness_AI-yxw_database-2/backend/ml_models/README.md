# ML Models 目录

这个目录用于存放运动分析的 PyTorch 模型文件。

## 模型文件位置

请将训练好的模型文件放在以下位置：

- `squat_model.pth` - 深蹲分析模型
- `pushup_model.pth` - 俯卧撑分析模型
- `plank_model.pth` - 平板支撑分析模型
- `jumping_jack_model.pth` - 开合跳分析模型

## 模型接口要求

每个模型应该实现以下接口：

### 输入格式
- **landmarks**: List[Dict] - MediaPipe姿态关键点列表
  - 每个关键点包含: `x`, `y`, `z`, `visibility`
  - 总共33个关键点（MediaPipe Pose标准）

### 输出格式
模型应该返回一个字典，包含以下字段：

**对于计数类运动（深蹲、俯卧撑、开合跳）：**
```python
{
    "is_correct": bool,      # 动作是否正确
    "score": int,            # 得分 (0-100)
    "feedback": str,         # 反馈信息
    "count": int,            # 当前计数
    "accuracy": float,       # 准确度
    "details": dict          # 详细信息（可选）
}
```

**对于计时类运动（平板支撑）：**
```python
{
    "is_correct": bool,      # 动作是否正确
    "score": int,            # 得分 (0-100)
    "feedback": str,         # 反馈信息
    "duration": float,       # 持续时间（秒）
    "accuracy": float,       # 准确度
    "details": dict          # 详细信息（可选）
}
```

## 模型实现方式

### 方式1：使用通用接口（推荐）
如果你的模型是一个标准的 PyTorch 模型（`.pth` 文件），可以直接放在对应位置，系统会自动使用 `GenericExerciseModel` 加载。

### 方式2：自定义模型类
如果你想自定义模型加载逻辑，可以创建对应的模型文件：

- `squat_model.py` - 包含 `SquatModel` 类
- `pushup_model.py` - 包含 `PushupModel` 类
- `plank_model.py` - 包含 `PlankModel` 类
- `jumping_jack_model.py` - 包含 `Jumping_jackModel` 类

每个模型类应该继承 `ExerciseModelInterface` 并实现：
- `_load_model()`: 加载模型
- `predict(landmarks)`: 进行预测

## 注意事项

1. 模型文件路径是相对于 `backend/` 目录的
2. 如果模型文件不存在，系统会记录警告但不会崩溃
3. 模型加载失败时，分析器会返回错误信息
4. 确保模型在 CPU 和 GPU 上都能正常工作（系统会自动检测）

