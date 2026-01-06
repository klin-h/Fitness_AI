"""
合并训练数据脚本
将站直、半蹲和完全蹲下的数据集合并，并添加标签列
"""

import pandas as pd
import numpy as np
import argparse
import os


def merge_training_data(
    stand_csv: str,
    half_squat_csv: str,
    full_squat_csv: str,
    output_csv: str,
    stand_label: int = 0,
    half_squat_label: int = 1,
    full_squat_label: int = 2
):
    """
    合并三个数据集并添加标签
    
    Args:
        stand_csv: 站直状态的CSV文件路径
        half_squat_csv: 半蹲状态的CSV文件路径
        full_squat_csv: 完全蹲下状态的CSV文件路径
        output_csv: 输出CSV文件路径
        stand_label: 站直状态的标签（默认: 0）
        half_squat_label: 半蹲状态的标签（默认: 1）
        full_squat_label: 完全蹲下状态的标签（默认: 2）
    """
    print("=" * 60)
    print("合并训练数据")
    print("=" * 60)
    
    datasets = []
    
    # 读取站直数据
    print(f"\n[1/4] 读取站直数据: {stand_csv}")
    if not os.path.exists(stand_csv):
        raise FileNotFoundError(f"文件不存在: {stand_csv}")
    
    df_stand = pd.read_csv(stand_csv)
    print(f"  行数: {len(df_stand)}")
    
    # 如果已有label列，先删除
    if 'label' in df_stand.columns:
        df_stand = df_stand.drop(columns=['label'])
    
    # 添加标签列
    df_stand['label'] = stand_label
    print(f"  添加标签: {stand_label} (站直)")
    datasets.append(('站直', df_stand))
    
    # 读取半蹲数据
    print(f"\n[2/4] 读取半蹲数据: {half_squat_csv}")
    if not os.path.exists(half_squat_csv):
        raise FileNotFoundError(f"文件不存在: {half_squat_csv}")
    
    df_half_squat = pd.read_csv(half_squat_csv)
    print(f"  行数: {len(df_half_squat)}")
    
    # 如果已有label列，先删除
    if 'label' in df_half_squat.columns:
        df_half_squat = df_half_squat.drop(columns=['label'])
    
    # 添加标签列
    df_half_squat['label'] = half_squat_label
    print(f"  添加标签: {half_squat_label} (半蹲)")
    datasets.append(('半蹲', df_half_squat))
    
    # 读取完全蹲下数据
    print(f"\n[3/4] 读取完全蹲下数据: {full_squat_csv}")
    if not os.path.exists(full_squat_csv):
        raise FileNotFoundError(f"文件不存在: {full_squat_csv}")
    
    df_full_squat = pd.read_csv(full_squat_csv)
    print(f"  行数: {len(df_full_squat)}")
    
    # 如果已有label列，先删除
    if 'label' in df_full_squat.columns:
        df_full_squat = df_full_squat.drop(columns=['label'])
    
    # 添加标签列
    df_full_squat['label'] = full_squat_label
    print(f"  添加标签: {full_squat_label} (完全蹲下)")
    datasets.append(('完全蹲下', df_full_squat))
    
    # 检查列是否一致
    print(f"\n[4/4] 检查并合并数据")
    
    # 获取所有数据集的列（除了label）
    all_cols = set()
    for name, df in datasets:
        cols = [col for col in df.columns if col != 'label']
        all_cols.update(cols)
    
    # 确保所有数据集有相同的列
    common_cols = sorted([col for col in all_cols if col != 'label'])
    print(f"  共同列数: {len(common_cols)} (期望: 133 = filename + 132个关键点)")
    
    # 对齐所有数据集的列
    dfs_aligned = []
    for name, df in datasets:
        # 确保有所有需要的列，缺失的用NaN填充
        for col in common_cols:
            if col not in df.columns:
                df[col] = np.nan
                print(f"  [WARN] {name} 缺少列: {col}")
        
        # 只保留共同列和label列
        df_aligned = df[common_cols + ['label']].copy()
        dfs_aligned.append(df_aligned)
    
    # 合并数据
    print(f"\n合并所有数据集...")
    df_combined = pd.concat(dfs_aligned, ignore_index=True)
    print(f"  总行数: {len(df_combined)}")
    
    # 检查数据完整性
    print(f"\n检查数据完整性...")
    
    # 检查是否有缺失值
    missing_count = df_combined.isnull().sum().sum()
    if missing_count > 0:
        print(f"  [WARN] 发现 {missing_count} 个缺失值")
        # 删除包含缺失值的行
        rows_before = len(df_combined)
        df_combined = df_combined.dropna()
        rows_after = len(df_combined)
        print(f"  [INFO] 删除了 {rows_before - rows_after} 行包含缺失值的数据")
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
    
    # 确保label列在最后
    cols_order = [col for col in df_combined.columns if col != 'label'] + ['label']
    df_combined = df_combined[cols_order]
    
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
    label_names = {
        stand_label: "站直",
        half_squat_label: "半蹲",
        full_squat_label: "完全蹲下"
    }
    for label, count in label_counts.items():
        label_name = label_names.get(label, f"状态{label}")
        print(f"  {label_name} ({label}): {count} 个样本 ({count/len(df_combined)*100:.1f}%)")
    
    print(f"\n[INFO] 数据合并完成！")
    print(f"[INFO] 可以使用以下命令训练模型：")
    print(f"  python train_squat_classifier.py --data {output_csv} --label-column label")
    
    return df_combined


def main():
    parser = argparse.ArgumentParser(description='合并训练数据（站直、半蹲、完全蹲下）')
    parser.add_argument('--stand', type=str, default='data/pose_landmarks_stand.csv',
                        help='站直状态的CSV文件路径（默认: data/pose_landmarks_stand.csv）')
    parser.add_argument('--half-squat', type=str, default='data/pose_landmarks_Half-squat.csv',
                        help='半蹲状态的CSV文件路径（默认: data/pose_landmarks_Half-squat.csv）')
    parser.add_argument('--full-squat', type=str, default='pose_landmarks_dunxia_filtered.csv',
                        help='完全蹲下状态的CSV文件路径（默认: pose_landmarks_dunxia_filtered.csv）')
    parser.add_argument('--output', type=str, default='data/pose_landmarks_training.csv',
                        help='输出CSV文件路径（默认: data/pose_landmarks_training.csv）')
    parser.add_argument('--stand-label', type=int, default=0,
                        help='站直状态的标签（默认: 0）')
    parser.add_argument('--half-squat-label', type=int, default=1,
                        help='半蹲状态的标签（默认: 1）')
    parser.add_argument('--full-squat-label', type=int, default=2,
                        help='完全蹲下状态的标签（默认: 2）')
    
    args = parser.parse_args()
    
    merge_training_data(
        args.stand,
        getattr(args, 'half_squat'),
        getattr(args, 'full_squat'),
        args.output,
        args.stand_label,
        args.half_squat_label,
        args.full_squat_label
    )


if __name__ == "__main__":
    # 如果直接运行，使用默认参数
    import sys
    if len(sys.argv) == 1:
        # 使用默认路径
        merge_training_data(
            'data/pose_landmarks_stand.csv',
            'data/pose_landmarks_Half-squat.csv',
            'pose_landmarks_dunxia_filtered.csv',
            'data/pose_landmarks_training.csv',
            stand_label=0,
            half_squat_label=1,
            full_squat_label=2
        )
    else:
        main()




