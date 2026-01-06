"""
深蹲状态预测脚本
接收MediaPipe骨骼点坐标，提取特征并返回深蹲状态
"""

import numpy as np
import argparse
import json
import sys
from squat_classifier import SquatClassifier, extract_squat_features


def parse_landmarks_from_list(landmarks_list):
    """
    从列表解析骨骼点坐标
    
    输入格式可以是：
    1. 展平的列表: [x0, y0, z0, v0, x1, y1, z1, v1, ..., x32, y32, z32, v32]
    2. 嵌套列表: [[x0, y0, z0, v0], [x1, y1, z1, v1], ..., [x32, y32, z32, v32]]
    """
    landmarks_array = np.array(landmarks_list, dtype=np.float32)
    
    # 如果是嵌套列表，展平
    if landmarks_array.ndim == 2:
        # 已经是33x4格式，直接返回
        if landmarks_array.shape == (33, 4):
            return landmarks_array
        else:
            landmarks_array = landmarks_array.flatten()
    
    # 检查维度
    if landmarks_array.shape[0] != 132:
        raise ValueError(
            f"输入维度错误：期望132维（33个点×4个值），"
            f"得到{landmarks_array.shape[0]}维"
        )
    
    # reshape为33x4
    return landmarks_array.reshape(33, 4)


def main():
    parser = argparse.ArgumentParser(description='预测深蹲状态')
    parser.add_argument('--model', type=str, default='squat_classifier_model.h5',
                        help='模型文件路径（默认: squat_classifier_model.h5）')
    parser.add_argument('--input', type=str,
                        help='输入JSON文件路径（包含骨骼点坐标）')
    parser.add_argument('--landmarks', type=str,
                        help='直接输入骨骼点坐标（逗号分隔的132个值）')
    parser.add_argument('--output', type=str,
                        help='输出JSON文件路径（可选）')
    parser.add_argument('--show-features', action='store_true',
                        help='显示提取的特征值')
    
    args = parser.parse_args()
    
    # 加载模型
    try:
        classifier = SquatClassifier(model_path=args.model)
    except Exception as e:
        print(f"[ERROR] 加载模型失败: {e}", file=sys.stderr)
        print(f"[INFO] 如果模型不存在，请先运行 train_squat_classifier.py 训练模型", file=sys.stderr)
        sys.exit(1)
    
    # 读取输入数据
    if args.input:
        # 从JSON文件读取
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'landmarks' in data:
                landmarks = data['landmarks']
            elif 'pose_landmarks' in data:
                # 如果是MediaPipe格式
                landmarks = []
                for lm in data['pose_landmarks']:
                    landmarks.extend([lm['x'], lm['y'], lm.get('z', 0.0), lm.get('visibility', 1.0)])
            else:
                raise ValueError("JSON文件必须包含 'landmarks' 或 'pose_landmarks' 字段")
        except Exception as e:
            print(f"[ERROR] 读取输入文件失败: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.landmarks:
        # 从命令行参数读取
        try:
            landmarks = [float(x.strip()) for x in args.landmarks.split(',')]
        except Exception as e:
            print(f"[ERROR] 解析骨骼点坐标失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 从标准输入读取
        try:
            input_str = sys.stdin.read().strip()
            data = json.loads(input_str)
            if 'landmarks' in data:
                landmarks = data['landmarks']
            else:
                raise ValueError("输入必须包含 'landmarks' 字段")
        except Exception as e:
            print(f"[ERROR] 读取标准输入失败: {e}", file=sys.stderr)
            print("\n使用示例:")
            print("  python predict_squat.py --landmarks '0.5,0.5,0.1,1.0,...'")
            print("  echo '{\"landmarks\": [0.5,0.5,0.1,1.0,...]}' | python predict_squat.py")
            sys.exit(1)
    
    # 解析骨骼点
    try:
        landmarks = parse_landmarks_from_list(landmarks)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    
    # 提取特征
    try:
        features = extract_squat_features(landmarks)
    except Exception as e:
        print(f"[ERROR] 特征提取失败: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 预测
    try:
        state, confidence, probabilities = classifier.predict(landmarks)
    except Exception as e:
        print(f"[ERROR] 预测失败: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 准备输出结果
    state_names = {0: "站直", 1: "半蹲", 2: "完全蹲下"}
    feature_names = [
        "左膝盖角度", "右膝盖角度", "左髋部角度", "右髋部角度",
        "髋关节垂直高度", "肩膀垂直高度", "左膝盖水平偏移", "右膝盖水平偏移"
    ]
    
    result = {
        "state": state,
        "state_name": state_names[state],
        "confidence": float(confidence),
        "probabilities": {
            "站直": float(probabilities[0]),
            "半蹲": float(probabilities[1]),
            "完全蹲下": float(probabilities[2])
        }
    }
    
    if args.show_features:
        result["features"] = {
            name: float(value) for name, value in zip(feature_names, features)
        }
    
    # 输出结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 结果已保存到: {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


