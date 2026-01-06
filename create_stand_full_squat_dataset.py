"""
创建只包含站直和完全蹲下的数据集
从完整的训练数据中筛选出标签0（站直）和标签2（完全蹲下），并重新标记为0和1
"""

import pandas as pd
import numpy as np
import argparse
import os


def create_stand_full_squat_dataset(
    input_csv: str,
    output_csv: str,
    stand_label: int = 0,
    full_squat_label: int = 2
):
    """
    从完整数据集中提取站直和完全蹲下的数据
    
    Args:
        input_csv: 输入CSV文件路径（包含3个类别的完整数据）
        output_csv: 输出CSV文件路径
        stand_label: 站直的原始标签（默认: 0）
        full_squat_label: 完全蹲下的原始标签（默认: 2）
    """
    print("=" * 60)
    print("创建站直-完全蹲下数据集")
    print("=" * 60)
    
    # 读取完整数据
    print(f"\n[1/3] 读取完整数据集: {input_csv}")
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"文件不存在: {input_csv}")
    
    df = pd.read_csv(input_csv)
    print(f"  总样本数: {len(df)}")
    print(f"  原始标签分布:")
    label_counts = df['label'].value_counts().sort_index()
    label_names = {0: '站直', 1: '半蹲', 2: '完全蹲下'}
    for label, count in label_counts.items():
        name = label_names.get(label, f'标签{label}')
        print(f"    {name} (标签{label}): {count} 个样本")
    
    # 筛选站直和完全蹲下的数据
    print(f"\n[2/3] 筛选数据（保留站直和完全蹲下）")
    df_filtered = df[df['label'].isin([stand_label, full_squat_label])].copy()
    print(f"  筛选后样本数: {len(df_filtered)}")
    
    # 重新标记：站直=0, 完全蹲下=1
    print(f"\n[3/3] 重新标记数据")
    df_filtered['label'] = df_filtered['label'].replace({
        stand_label: 0,      # 站直 -> 0
        full_squat_label: 1  # 完全蹲下 -> 1
    })
    
    # 统计新标签分布
    new_label_counts = df_filtered['label'].value_counts().sort_index()
    new_label_names = {0: '站直', 1: '完全蹲下'}
    print(f"  新标签分布:")
    for label, count in new_label_counts.items():
        name = new_label_names.get(label, f'标签{label}')
        print(f"    {name} (标签{label}): {count} 个样本 ({count/len(df_filtered)*100:.1f}%)")
    
    # 保存新数据集
    print(f"\n保存数据集到: {output_csv}")
    df_filtered.to_csv(output_csv, index=False)
    print(f"  [OK] 数据集已保存")
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("数据集统计")
    print("=" * 60)
    print(f"总样本数: {len(df_filtered)}")
    print(f"特征列数: {len(df.columns) - 2}")  # 减去filename和label列
    print(f"标签列: label (0: 站直, 1: 完全蹲下)")
    print(f"\n标签分布:")
    for label, count in new_label_counts.items():
        name = new_label_names.get(label, f'标签{label}')
        print(f"  {name} ({label}): {count} 个样本 ({count/len(df_filtered)*100:.1f}%)")
    
    print(f"\n[INFO] 数据集创建完成！")
    print(f"[INFO] 可以使用以下命令训练2分类模型：")
    print(f"  python train_squat_classifier.py --data {output_csv} --label-column label")
    
    return df_filtered


def main():
    parser = argparse.ArgumentParser(description='创建只包含站直和完全蹲下的数据集')
    parser.add_argument('--input', type=str, default='data/pose_landmarks_training.csv',
                        help='输入CSV文件路径（包含3个类别的完整数据，默认: data/pose_landmarks_training.csv）')
    parser.add_argument('--output', type=str, default='data/pose_landmarks_stand_full_squat.csv',
                        help='输出CSV文件路径（默认: data/pose_landmarks_stand_full_squat.csv）')
    parser.add_argument('--stand-label', type=int, default=0,
                        help='站直的原始标签（默认: 0）')
    parser.add_argument('--full-squat-label', type=int, default=2,
                        help='完全蹲下的原始标签（默认: 2）')
    
    args = parser.parse_args()
    
    create_stand_full_squat_dataset(
        args.input,
        args.output,
        args.stand_label,
        args.full_squat_label
    )


if __name__ == "__main__":
    # 如果直接运行，使用默认参数
    import sys
    if len(sys.argv) == 1:
        # 使用默认路径
        create_stand_full_squat_dataset(
            'data/pose_landmarks_training.csv',
            'data/pose_landmarks_stand_full_squat.csv',
            stand_label=0,
            full_squat_label=2
        )
    else:
        main()




