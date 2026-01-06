"""
准备训练数据脚本
将两个CSV文件（站直和半蹲）合并，并添加标签列
"""

import pandas as pd
import numpy as np
import argparse
import os


def prepare_training_data(
    stand_csv: str,
    half_squat_csv: str,
    output_csv: str,
    stand_label: int = 0,
    half_squat_label: int = 1
):
    """
    准备训练数据
    
    Args:
        stand_csv: 站直状态的CSV文件路径
        half_squat_csv: 半蹲状态的CSV文件路径
        output_csv: 输出CSV文件路径
        stand_label: 站直状态的标签（默认: 0）
        half_squat_label: 半蹲状态的标签（默认: 1）
    """
    print("=" * 60)
    print("准备训练数据")
    print("=" * 60)
    
    # 读取站直数据
    print(f"\n[1/4] 读取站直数据: {stand_csv}")
    if not os.path.exists(stand_csv):
        raise FileNotFoundError(f"文件不存在: {stand_csv}")
    
    df_stand = pd.read_csv(stand_csv)
    print(f"  行数: {len(df_stand)}")
    print(f"  列数: {len(df_stand.columns)}")
    
    # 添加标签列
    df_stand['label'] = stand_label
    print(f"  添加标签: {stand_label} (站直)")
    
    # 读取半蹲数据
    print(f"\n[2/4] 读取半蹲数据: {half_squat_csv}")
    if not os.path.exists(half_squat_csv):
        raise FileNotFoundError(f"文件不存在: {half_squat_csv}")
    
    df_half_squat = pd.read_csv(half_squat_csv)
    print(f"  行数: {len(df_half_squat)}")
    print(f"  列数: {len(df_half_squat.columns)}")
    
    # 添加标签列
    df_half_squat['label'] = half_squat_label
    print(f"  添加标签: {half_squat_label} (半蹲)")
    
    # 检查列是否一致
    if list(df_stand.columns[:-1]) != list(df_half_squat.columns[:-1]):
        print("\n[WARN] 两个文件的列不完全一致，尝试对齐...")
        # 获取共同的列（除了label）
        common_cols = [col for col in df_stand.columns if col != 'label']
        df_stand = df_stand[common_cols + ['label']]
        df_half_squat = df_half_squat[common_cols + ['label']]
    
    # 合并数据
    print(f"\n[3/4] 合并数据")
    df_combined = pd.concat([df_stand, df_half_squat], ignore_index=True)
    print(f"  总行数: {len(df_combined)}")
    print(f"  标签分布:")
    print(f"    站直 ({stand_label}): {len(df_stand)} 个样本")
    print(f"    半蹲 ({half_squat_label}): {len(df_half_squat)} 个样本")
    
    # 检查数据完整性
    print(f"\n[4/4] 检查数据完整性")
    
    # 检查是否有缺失值
    missing_count = df_combined.isnull().sum().sum()
    if missing_count > 0:
        print(f"  [WARN] 发现 {missing_count} 个缺失值")
        # 可以选择删除包含缺失值的行
        # df_combined = df_combined.dropna()
    else:
        print("  [OK] 没有缺失值")
    
    # 检查骨骼点列
    feature_cols = []
    for i in range(33):
        for suffix in ['_x', '_y', '_z', '_visibility']:
            col = f"{i}{suffix}"
            if col in df_combined.columns:
                feature_cols.append(col)
    
    print(f"  骨骼点列数: {len(feature_cols)} (期望: 132 = 33 * 4)")
    
    if len(feature_cols) != 132:
        print(f"  [WARN] 骨骼点列数不完整，可能影响特征提取")
    
    # 保存合并后的数据
    print(f"\n保存合并数据到: {output_csv}")
    df_combined.to_csv(output_csv, index=False)
    print(f"  [OK] 数据已保存")
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("数据统计")
    print("=" * 60)
    print(f"总样本数: {len(df_combined)}")
    print(f"特征列数: {len(feature_cols)}")
    print(f"标签列: label")
    print(f"\n标签分布:")
    label_counts = df_combined['label'].value_counts().sort_index()
    for label, count in label_counts.items():
        label_name = "站直" if label == stand_label else "半蹲" if label == half_squat_label else f"状态{label}"
        print(f"  {label_name} ({label}): {count} 个样本 ({count/len(df_combined)*100:.1f}%)")
    
    print(f"\n[INFO] 数据准备完成！")
    print(f"[INFO] 可以使用以下命令训练模型：")
    print(f"  python train_squat_classifier.py --data {output_csv} --label-column label")
    
    return df_combined


def main():
    parser = argparse.ArgumentParser(description='准备训练数据')
    parser.add_argument('--stand', type=str, default='data/pose_landmarks_stand.csv',
                        help='站直状态的CSV文件路径（默认: data/pose_landmarks_stand.csv）')
    parser.add_argument('--half-squat', type=str, default='data/pose_landmarks_Half-squat.csv',
                        help='半蹲状态的CSV文件路径（默认: data/pose_landmarks_Half-squat.csv）')
    parser.add_argument('--output', type=str, default='data/pose_landmarks_training.csv',
                        help='输出CSV文件路径（默认: data/pose_landmarks_training.csv）')
    parser.add_argument('--stand-label', type=int, default=0,
                        help='站直状态的标签（默认: 0）')
    parser.add_argument('--half-squat-label', type=int, default=1,
                        help='半蹲状态的标签（默认: 1）')
    
    args = parser.parse_args()
    
    prepare_training_data(
        args.stand,
        getattr(args, 'half_squat'),  # 处理--half-squat参数名
        args.output,
        args.stand_label,
        args.half_squat_label
    )


if __name__ == "__main__":
    # 如果直接运行，使用默认参数
    import sys
    if len(sys.argv) == 1:
        # 使用默认路径
        prepare_training_data(
            'data/pose_landmarks_stand.csv',
            'data/pose_landmarks_Half-squat.csv',
            'data/pose_landmarks_training.csv',
            stand_label=0,
            half_squat_label=1
        )
    else:
        main()




