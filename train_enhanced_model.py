"""
使用增强特征训练模型
"""

import numpy as np
import argparse
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from squat_classifier import SquatClassifier, load_data_from_csv
from optimize_model import extract_enhanced_features, data_augmentation, smote_oversampling
import pandas as pd
import os
from datetime import datetime


def load_data_with_enhanced_features(csv_path: str, label_column: str = 'label', 
                                     use_augmentation: bool = False,
                                     use_smote: bool = False) -> tuple:
    """加载数据并使用增强特征"""
    df = pd.read_csv(csv_path)
    
    # 提取特征列
    feature_cols = []
    for i in range(33):
        feature_cols.extend([f"{i}_x", f"{i}_y", f"{i}_z", f"{i}_visibility"])
    
    raw_data = df[feature_cols].values.astype(np.float32)
    
    # 提取增强特征
    features_list = []
    for row in raw_data:
        landmarks = row.reshape(33, 4)
        features = extract_enhanced_features(landmarks, include_raw_coords=True)
        features_list.append(features)
    
    X = np.array(features_list)
    y = df[label_column].values.astype(np.int32)
    
    print(f"[INFO] 加载了 {len(X)} 个样本，特征维度: {X.shape[1]}")
    print(f"[INFO] 标签分布: {np.bincount(y)}")
    
    # 数据增强
    if use_augmentation:
        print("[INFO] 应用数据增强...")
        X, y = data_augmentation(X, y, noise_level=0.01)
        print(f"[INFO] 增强后: {len(X)} 个样本")
    
    # SMOTE过采样
    if use_smote:
        print("[INFO] 应用SMOTE过采样...")
        X, y = smote_oversampling(X, y)
        print(f"[INFO] SMOTE后: {len(X)} 个样本，标签分布: {np.bincount(y)}")
    
    return X, y


def main():
    parser = argparse.ArgumentParser(description='使用增强特征训练深蹲分类器')
    parser.add_argument('--data', type=str, default='data/pose_landmarks_training.csv',
                        help='训练数据CSV文件路径')
    parser.add_argument('--label-column', type=str, default='label',
                        help='标签列名')
    parser.add_argument('--epochs', type=int, default=150,
                        help='训练轮数')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='批次大小')
    parser.add_argument('--validation-split', type=float, default=0.2,
                        help='验证集比例')
    parser.add_argument('--no-class-weight', action='store_true',
                        help='不使用类别权重')
    parser.add_argument('--augmentation', action='store_true',
                        help='使用数据增强')
    parser.add_argument('--smote', action='store_true',
                        help='使用SMOTE过采样')
    parser.add_argument('--output', type=str, default='squat_classifier_model.h5',
                        help='输出模型文件名')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("增强特征深蹲分类器训练")
    print("=" * 60)
    
    # 加载数据
    print(f"\n[1/4] 加载数据从: {args.data}")
    X, y = load_data_with_enhanced_features(
        args.data, 
        label_column=args.label_column,
        use_augmentation=args.augmentation,
        use_smote=args.smote
    )
    
    # 划分训练集和验证集
    print(f"\n[2/4] 划分训练集和验证集（验证集比例: {args.validation_split})")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, 
        test_size=args.validation_split, 
        random_state=42,
        stratify=y
    )
    print(f"训练集: {len(X_train)} 个样本")
    print(f"验证集: {len(X_val)} 个样本")
    
    # 类别权重
    num_classes = len(np.unique(y_train))
    label_names = ['站直', '半蹲', '完全蹲下'] if num_classes == 3 else ['站直', '完全蹲下']
    
    class_weight_dict = None
    if not args.no_class_weight:
        from sklearn.utils.class_weight import compute_class_weight
        class_weights = compute_class_weight(
            'balanced',
            classes=np.unique(y_train),
            y=y_train
        )
        class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}
        print(f"\n类别权重:")
        for i in range(num_classes):
            name = label_names[i] if i < len(label_names) else f'类别{i}'
            count = np.sum(y_train == i)
            print(f"  {name} (标签{i}): 权重={class_weight_dict[i]:.3f}, 样本数={count}")
    else:
        print(f"\n不使用类别权重")
        for i in range(num_classes):
            name = label_names[i] if i < len(label_names) else f'类别{i}'
            count = np.sum(y_train == i)
            print(f"  {name} (标签{i}): 样本数={count}")
    
    # 创建模型（使用更大的架构）
    print(f"\n[3/4] 创建增强模型")
    input_dim = X.shape[1]
    classifier = SquatClassifier(input_dim=input_dim, num_classes=num_classes)
    # 使用更大的模型架构
    classifier.build_model(
        hidden_units=[256, 128, 64, 32],
        dropout_rates=[0.5, 0.4, 0.3, 0.2],
        learning_rate=0.001
    )
    classifier.get_model_summary()
    
    # 训练模型
    print(f"\n[4/4] 开始训练（epochs={args.epochs}, batch_size={args.batch_size}）")
    print("使用早停机制（patience=15）和学习率调度")
    history = classifier.train(
        X_train, y_train,
        X_val, y_val,
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight_dict,
        use_early_stopping=True,
        patience=15
    )
    
    # 评估
    print("\n" + "=" * 60)
    print("训练完成，评估模型性能")
    print("=" * 60)
    
    val_loss, val_accuracy = classifier.model.evaluate(X_val, y_val, verbose=0)
    print(f"验证集准确率: {val_accuracy:.4f}")
    print(f"验证集损失: {val_loss:.4f}")
    
    y_pred = classifier.model.predict(X_val, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)
    
    print(f"\n分类报告:")
    print(classification_report(y_val, y_pred_classes, target_names=label_names))
    
    cm = confusion_matrix(y_val, y_pred_classes)
    print(f"\n混淆矩阵:")
    header = "        " + "".join([f"{name:<10}" for name in label_names])
    print(header)
    for i, row in enumerate(cm):
        row_str = f"{label_names[i]:<8} " + "".join([f"{val:<10}" for val in row])
        print(row_str)
    
    # 保存模型
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = os.path.splitext(args.output)[0] + f"_{timestamp}.h5"
    print(f"\n保存模型到: {model_path}")
    classifier.save_model(model_path)
    
    # 绘制并保存训练曲线
    if history and hasattr(history, 'history'):
        print("\n绘制训练曲线...")
        epochs = range(1, len(history.history['loss']) + 1)
        
        # 创建标准版本
        fig, axes = plt.subplots(2, 1, figsize=(10, 8))
        
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
        
        plt.tight_layout()
        
        # 生成图片文件名
        plot_path = model_path.replace('.h5', '_training_curves.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"  训练曲线已保存到: {plot_path}")
        
        # 创建详细版本
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
        plot_detailed_path = model_path.replace('.h5', '_training_curves_detailed.png')
        plt.savefig(plot_detailed_path, dpi=300, bbox_inches='tight')
        print(f"  详细训练曲线已保存到: {plot_detailed_path}")
        
        plt.close('all')
    
    print("\n训练完成！")


if __name__ == "__main__":
    main()



