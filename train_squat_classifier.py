"""
深蹲分类器训练脚本
从CSV文件加载标注数据，提取特征并训练模型
"""

import numpy as np
import argparse
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from squat_classifier import SquatClassifier, load_data_from_csv, extract_squat_features
import os
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description='训练深蹲状态分类模型')
    parser.add_argument('--data', type=str, required=True,
                        help='CSV数据文件路径（包含骨骼点坐标和标签）')
    parser.add_argument('--label-column', type=str, default='label',
                        help='标签列名（默认: label）')
    parser.add_argument('--output', type=str, default='squat_classifier_model.h5',
                        help='输出模型路径（默认: squat_classifier_model.h5）')
    parser.add_argument('--epochs', type=int, default=100,
                        help='训练轮数（默认: 100）')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='批次大小（默认: 32）')
    parser.add_argument('--validation-split', type=float, default=0.2,
                        help='验证集比例（默认: 0.2）')
    parser.add_argument('--no-class-weight', action='store_true',
                        help='不使用类别权重（默认: 使用类别权重）')
    parser.add_argument('--no-raw-coords', action='store_true',
                        help='不使用关键点原始坐标特征（默认: 使用关键点坐标，共24维特征）')
    parser.add_argument('--no-early-stopping', action='store_true',
                        help='不使用早停（默认: 使用早停）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("深蹲状态分类器训练")
    print("=" * 60)
    
    # 加载数据（会自动提取特征）
    print(f"\n[1/4] 加载数据从: {args.data}")
    include_raw_coords = not args.no_raw_coords
    try:
        X, y = load_data_from_csv(
            args.data, 
            label_column=args.label_column, 
            include_raw_coords=include_raw_coords
        )
        expected_dim = 24 if include_raw_coords else 8
        print(f"特征维度: {X.shape[1]} (期望: {expected_dim}维)")
        print(f"特征统计:")
        print(f"  均值: {X.mean(axis=0)}")
        print(f"  标准差: {X.std(axis=0)}")
    except Exception as e:
        print(f"[ERROR] 加载数据失败: {e}")
        return
    
    # 划分训练集和验证集
    print(f"\n[2/4] 划分训练集和验证集（验证集比例: {args.validation_split})")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, 
        test_size=args.validation_split, 
        random_state=42,
        stratify=y  # 保持标签分布
    )
    print(f"训练集: {len(X_train)} 个样本")
    print(f"验证集: {len(X_val)} 个样本")
    
    # 根据类别数量确定标签名称
    num_classes = len(np.unique(y_train))
    if num_classes == 2:
        label_names = ['站直', '完全蹲下']
    elif num_classes == 3:
        label_names = ['站直', '半蹲', '完全蹲下']
    else:
        label_names = [f'类别{i}' for i in range(num_classes)]
    
    # 计算类别权重（处理数据不平衡）
    class_weight_dict = None
    if not args.no_class_weight:
        from sklearn.utils.class_weight import compute_class_weight
        class_weights = compute_class_weight(
            'balanced',
            classes=np.unique(y_train),
            y=y_train
        )
        class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}
        
        print(f"\n类别权重（用于处理数据不平衡）:")
        for i in range(num_classes):
            name = label_names[i] if i < len(label_names) else f'类别{i}'
            count = np.sum(y_train == i)
            if i in class_weight_dict:
                print(f"  {name} (标签{i}): 权重={class_weight_dict[i]:.3f}, 样本数={count}")
    else:
        print(f"\n不使用类别权重")
        for i in range(num_classes):
            name = label_names[i] if i < len(label_names) else f'类别{i}'
            count = np.sum(y_train == i)
            print(f"  {name} (标签{i}): 样本数={count}")
    
    # 创建模型（优化版本）
    print(f"\n[3/4] 创建模型（优化架构）")
    input_dim = X.shape[1]  # 从数据获取特征维度
    num_classes = len(np.unique(y))
    classifier = SquatClassifier(input_dim=input_dim, num_classes=num_classes)
    classifier.get_model_summary()
    
    # 训练模型（优化版本，支持早停）
    print(f"\n[4/4] 开始训练（epochs={args.epochs}, batch_size={args.batch_size}）")
    use_early_stopping = not args.no_early_stopping
    if use_early_stopping:
        print("使用早停机制（patience=15）和学习率调度")
    history = classifier.train(
        X_train, y_train,
        X_val, y_val,
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight_dict,
        use_early_stopping=use_early_stopping,
        patience=15
    )
    
    # 评估模型
    print("\n" + "=" * 60)
    print("训练完成，评估模型性能")
    print("=" * 60)
    
    # 在验证集上评估
    val_loss, val_accuracy = classifier.model.evaluate(X_val, y_val, verbose=0)
    print(f"验证集准确率: {val_accuracy:.4f}")
    print(f"验证集损失: {val_loss:.4f}")
    
    # 计算混淆矩阵和分类报告
    from sklearn.metrics import confusion_matrix, classification_report
    y_pred = classifier.model.predict(X_val, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)
    
    # 根据类别数量确定标签名称
    num_classes = len(np.unique(y_val))
    if num_classes == 2:
        label_names = ['站直', '完全蹲下']
    elif num_classes == 3:
        label_names = ['站直', '半蹲', '完全蹲下']
    else:
        label_names = [f'类别{i}' for i in range(num_classes)]
    
    print(f"\n分类报告:")
    print(classification_report(y_val, y_pred_classes, target_names=label_names))
    
    cm = confusion_matrix(y_val, y_pred_classes)
    print(f"\n混淆矩阵:")
    # 打印表头
    header = "        " + "".join([f"{name:<10}" for name in label_names])
    print(header)
    # 打印每一行
    for i, row in enumerate(cm):
        row_str = f"{label_names[i]:<8} " + "".join([f"{val:<10}" for val in row])
        print(row_str)
    
    # 生成带时间戳的模型文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output.endswith('.h5'):
        model_path_with_timestamp = args.output.replace('.h5', f'_{timestamp}.h5')
    else:
        model_path_with_timestamp = f"{args.output}_{timestamp}.h5"
    
    # 绘制训练曲线（使用带时间戳的文件名）
    print(f"\n绘制训练曲线...")
    plot_training_history(history, model_path_with_timestamp)
    
    # 保存模型
    print(f"\n保存模型到: {model_path_with_timestamp}")
    classifier.save_model(model_path_with_timestamp)
    
    print("\n训练完成！")


def plot_training_history(history, model_path):
    """
    绘制并保存训练曲线
    
    Args:
        history: Keras训练历史对象
        model_path: 模型保存路径（用于生成图片文件名）
    """
    # 获取训练历史
    epochs = range(1, len(history.history['loss']) + 1)
    
    # 创建图表
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # 绘制Loss曲线
    axes[0].plot(epochs, history.history['loss'], 'b-', label='训练集 Loss', linewidth=2)
    if 'val_loss' in history.history:
        axes[0].plot(epochs, history.history['val_loss'], 'r-', label='验证集 Loss', linewidth=2)
    axes[0].set_title('模型 Loss 曲线', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].legend(fontsize=11)
    axes[0].grid(True, alpha=0.3)
    
    # 绘制Accuracy曲线
    axes[1].plot(epochs, history.history['accuracy'], 'b-', label='训练集 Accuracy', linewidth=2)
    if 'val_accuracy' in history.history:
        axes[1].plot(epochs, history.history['val_accuracy'], 'r-', label='验证集 Accuracy', linewidth=2)
    axes[1].set_title('模型 Accuracy 曲线', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Accuracy', fontsize=12)
    axes[1].legend(fontsize=11)
    axes[1].grid(True, alpha=0.3)
    
    # 调整布局
    plt.tight_layout()
    
    # 生成图片文件名
    if model_path.endswith('.h5'):
        plot_path = model_path.replace('.h5', '_training_curves.png')
    else:
        plot_path = model_path + '_training_curves.png'
    
    # 保存图片
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"  训练曲线已保存到: {plot_path}")
    
    # 也保存一个单独的详细版本（更大的图）
    fig_detailed, axes_detailed = plt.subplots(2, 1, figsize=(12, 10))
    
    # Loss详细图
    axes_detailed[0].plot(epochs, history.history['loss'], 'b-', label='训练集 Loss', linewidth=2, marker='o', markersize=3)
    if 'val_loss' in history.history:
        axes_detailed[0].plot(epochs, history.history['val_loss'], 'r-', label='验证集 Loss', linewidth=2, marker='s', markersize=3)
    axes_detailed[0].set_title('模型 Loss 曲线', fontsize=16, fontweight='bold')
    axes_detailed[0].set_xlabel('Epoch', fontsize=14)
    axes_detailed[0].set_ylabel('Loss', fontsize=14)
    axes_detailed[0].legend(fontsize=12)
    axes_detailed[0].grid(True, alpha=0.3)
    
    # Accuracy详细图
    axes_detailed[1].plot(epochs, history.history['accuracy'], 'b-', label='训练集 Accuracy', linewidth=2, marker='o', markersize=3)
    if 'val_accuracy' in history.history:
        axes_detailed[1].plot(epochs, history.history['val_accuracy'], 'r-', label='验证集 Accuracy', linewidth=2, marker='s', markersize=3)
    axes_detailed[1].set_title('模型 Accuracy 曲线', fontsize=16, fontweight='bold')
    axes_detailed[1].set_xlabel('Epoch', fontsize=14)
    axes_detailed[1].set_ylabel('Accuracy', fontsize=14)
    axes_detailed[1].legend(fontsize=12)
    axes_detailed[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存详细版本
    if model_path.endswith('.h5'):
        plot_detailed_path = model_path.replace('.h5', '_training_curves_detailed.png')
    else:
        plot_detailed_path = model_path + '_training_curves_detailed.png'
    
    plt.savefig(plot_detailed_path, dpi=300, bbox_inches='tight')
    print(f"  详细训练曲线已保存到: {plot_detailed_path}")
    
    plt.close('all')


if __name__ == "__main__":
    main()


