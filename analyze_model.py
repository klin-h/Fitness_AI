"""
深度分析3分类深蹲模型
包括：训练曲线分析、特征分布分析、误分类分析、类别间特征对比
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.manifold import TSNE
from squat_classifier import SquatClassifier, load_data_from_csv
import os
import glob
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def find_latest_model():
    """找到最新的模型文件"""
    model_files = glob.glob("squat_classifier_model_*.h5")
    if not model_files:
        return None
    # 按修改时间排序
    model_files.sort(key=os.path.getmtime, reverse=True)
    return model_files[0]

def analyze_training_curves(history):
    """分析训练曲线，找出最佳epoch"""
    epochs = range(1, len(history.history['loss']) + 1)
    
    # 找出最佳epoch（验证集准确率最高）
    val_acc = history.history.get('val_accuracy', [])
    if val_acc:
        best_epoch = np.argmax(val_acc) + 1
        best_val_acc = max(val_acc)
        print(f"\n{'='*60}")
        print("训练曲线分析")
        print(f"{'='*60}")
        print(f"最佳Epoch: {best_epoch} (验证集准确率: {best_val_acc:.4f})")
        
        # 检查过拟合
        train_acc = history.history['accuracy']
        final_train_acc = train_acc[-1]
        final_val_acc = val_acc[-1]
        gap = final_train_acc - final_val_acc
        
        print(f"\n最终训练集准确率: {final_train_acc:.4f}")
        print(f"最终验证集准确率: {final_val_acc:.4f}")
        print(f"准确率差距: {gap:.4f} ({gap*100:.2f}%)")
        
        if gap > 0.1:
            print("⚠️  警告: 可能存在过拟合（训练集准确率明显高于验证集）")
        elif gap < 0.05:
            print("✓ 模型泛化能力良好（训练集和验证集准确率接近）")
        else:
            print("⚠️  注意: 存在轻微过拟合")
        
        # 检查损失曲线
        train_loss = history.history['loss']
        val_loss = history.history.get('val_loss', [])
        if val_loss:
            final_train_loss = train_loss[-1]
            final_val_loss = val_loss[-1]
            print(f"\n最终训练集损失: {final_train_loss:.4f}")
            print(f"最终验证集损失: {final_val_loss:.4f}")
            
            # 检查损失是否还在下降
            if len(val_loss) >= 10:
                recent_val_loss = val_loss[-10:]
                if recent_val_loss[-1] < recent_val_loss[0]:
                    print("✓ 验证集损失仍在下降，模型可能还能继续学习")
                else:
                    print("⚠️  验证集损失趋于稳定或上升，建议使用早停")
    
    return best_epoch if val_acc else None

def analyze_feature_distribution(X, y, feature_names=None):
    """分析各类别的特征分布"""
    print(f"\n{'='*60}")
    print("特征分布分析")
    print(f"{'='*60}")
    
    if feature_names is None:
        feature_names = [
            '左膝角度', '右膝角度', '左髋角度', '右髋角度',
            '髋部高度', '肩部高度', '左膝偏移', '右膝偏移'
        ]
    
    label_names = ['站直', '半蹲', '完全蹲下']
    num_classes = len(np.unique(y))
    
    # 为每个类别计算特征统计
    print("\n各类别特征统计:")
    for class_idx in range(num_classes):
        class_mask = y == class_idx
        class_data = X[class_mask]
        class_name = label_names[class_idx] if class_idx < len(label_names) else f'类别{class_idx}'
        
        print(f"\n{class_name} (标签{class_idx}):")
        print(f"  样本数: {np.sum(class_mask)}")
        print(f"  特征均值:")
        for i, feat_name in enumerate(feature_names):
            mean_val = np.mean(class_data[:, i])
            std_val = np.std(class_data[:, i])
            print(f"    {feat_name}: {mean_val:.2f} ± {std_val:.2f}")
    
    # 可视化特征分布
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    
    for i, feat_name in enumerate(feature_names):
        ax = axes[i]
        for class_idx in range(num_classes):
            class_mask = y == class_idx
            class_data = X[class_mask]
            class_name = label_names[class_idx] if class_idx < len(label_names) else f'类别{class_idx}'
            
            ax.hist(class_data[:, i], alpha=0.6, label=class_name, bins=30)
        
        ax.set_title(f'{feat_name} 分布', fontsize=12, fontweight='bold')
        ax.set_xlabel('特征值')
        ax.set_ylabel('频数')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f'feature_distribution_{timestamp}.png', dpi=300, bbox_inches='tight')
    print(f"\n特征分布图已保存到: feature_distribution_{timestamp}.png")
    plt.close()

def analyze_misclassification(X_val, y_val, y_pred, classifier):
    """分析误分类样本"""
    print(f"\n{'='*60}")
    print("误分类分析")
    print(f"{'='*60}")
    
    label_names = ['站直', '半蹲', '完全蹲下']
    misclassified = y_val != y_pred
    
    print(f"\n总误分类数: {np.sum(misclassified)} / {len(y_val)} ({np.sum(misclassified)/len(y_val)*100:.2f}%)")
    
    # 分析每种误分类类型
    print("\n误分类详情:")
    for true_label in range(3):
        true_name = label_names[true_label]
        true_mask = y_val == true_label
        mis_mask = misclassified & true_mask
        
        if np.sum(mis_mask) > 0:
            print(f"\n{true_name} (标签{true_label}) 被误分类为:")
            mis_samples = y_pred[mis_mask]
            for pred_label in range(3):
                if pred_label != true_label:
                    count = np.sum(mis_samples == pred_label)
                    if count > 0:
                        pred_name = label_names[pred_label]
                        print(f"  → {pred_name} (标签{pred_label}): {count} 个样本")
    
    # 分析误分类样本的特征
    if np.sum(misclassified) > 0:
        print("\n误分类样本特征分析:")
        mis_X = X_val[misclassified]
        mis_y_true = y_val[misclassified]
        mis_y_pred = y_pred[misclassified]
        
        # 获取预测概率
        mis_probs = classifier.model.predict(mis_X, verbose=0)
        
        print("\n误分类样本的平均预测概率:")
        for i in range(len(mis_X)):
            true_label = mis_y_true[i]
            pred_label = mis_y_pred[i]
            probs = mis_probs[i]
            true_name = label_names[true_label]
            pred_name = label_names[pred_label]
            
            print(f"\n样本 {i+1}: {true_name} → {pred_name}")
            for j, prob in enumerate(probs):
                label_name = label_names[j] if j < len(label_names) else f'类别{j}'
                marker = " ← 真实" if j == true_label else (" ← 预测" if j == pred_label else "")
                print(f"  {label_name}: {prob:.4f}{marker}")

def analyze_class_separation(X, y):
    """分析类别间的分离度"""
    print(f"\n{'='*60}")
    print("类别分离度分析")
    print(f"{'='*60}")
    
    label_names = ['站直', '半蹲', '完全蹲下']
    
    # 计算各类别的特征中心
    class_centers = []
    for class_idx in range(3):
        class_mask = y == class_idx
        class_data = X[class_mask]
        center = np.mean(class_data, axis=0)
        class_centers.append(center)
    
    class_centers = np.array(class_centers)
    
    # 计算类别间距离
    print("\n类别间欧氏距离:")
    for i in range(3):
        for j in range(i+1, 3):
            dist = np.linalg.norm(class_centers[i] - class_centers[j])
            name_i = label_names[i]
            name_j = label_names[j]
            print(f"  {name_i} ↔ {name_j}: {dist:.4f}")
    
    # 计算类别内方差
    print("\n类别内方差:")
    for class_idx in range(3):
        class_mask = y == class_idx
        class_data = X[class_mask]
        variance = np.var(class_data, axis=0).mean()
        class_name = label_names[class_idx]
        print(f"  {class_name}: {variance:.4f}")
    
    # 计算分离度（类间距离 / 类内方差）
    print("\n类别分离度 (类间距离 / 类内方差):")
    for i in range(3):
        for j in range(i+1, 3):
            dist = np.linalg.norm(class_centers[i] - class_centers[j])
            var_i = np.var(X[y == i], axis=0).mean()
            var_j = np.var(X[y == j], axis=0).mean()
            avg_var = (var_i + var_j) / 2
            separation = dist / avg_var if avg_var > 0 else 0
            name_i = label_names[i]
            name_j = label_names[j]
            print(f"  {name_i} ↔ {name_j}: {separation:.4f}")

def visualize_confusion_matrix_detailed(y_true, y_pred):
    """详细可视化混淆矩阵"""
    label_names = ['站直', '半蹲', '完全蹲下']
    cm = confusion_matrix(y_true, y_pred)
    
    # 计算百分比
    cm_percent = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # 绝对数量
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=label_names, yticklabels=label_names,
                ax=axes[0], cbar_kws={'label': '样本数'})
    axes[0].set_title('混淆矩阵 (绝对数量)', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('预测类别')
    axes[0].set_ylabel('真实类别')
    
    # 百分比
    sns.heatmap(cm_percent, annot=True, fmt='.1f', cmap='Blues',
                xticklabels=label_names, yticklabels=label_names,
                ax=axes[1], cbar_kws={'label': '百分比 (%)'})
    axes[1].set_title('混淆矩阵 (百分比)', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('预测类别')
    axes[1].set_ylabel('真实类别')
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f'confusion_matrix_detailed_{timestamp}.png', dpi=300, bbox_inches='tight')
    print(f"\n详细混淆矩阵已保存到: confusion_matrix_detailed_{timestamp}.png")
    plt.close()

def analyze_prediction_confidence(X_val, y_val, classifier):
    """分析预测置信度"""
    print(f"\n{'='*60}")
    print("预测置信度分析")
    print(f"{'='*60}")
    
    label_names = ['站直', '半蹲', '完全蹲下']
    
    # 获取预测概率
    probs = classifier.model.predict(X_val, verbose=0)
    y_pred = np.argmax(probs, axis=1)
    max_probs = np.max(probs, axis=1)
    
    print("\n各类别预测置信度统计:")
    for class_idx in range(3):
        class_mask = y_val == class_idx
        class_name = label_names[class_idx]
        
        if np.sum(class_mask) > 0:
            correct_mask = (y_pred == y_val) & class_mask
            incorrect_mask = (y_pred != y_val) & class_mask
            
            if np.sum(correct_mask) > 0:
                correct_conf = max_probs[correct_mask]
                print(f"\n{class_name} (标签{class_idx}):")
                print(f"  正确预测 ({np.sum(correct_mask)} 个):")
                print(f"    平均置信度: {np.mean(correct_conf):.4f}")
                print(f"    最小置信度: {np.min(correct_conf):.4f}")
                print(f"    最大置信度: {np.max(correct_conf):.4f}")
            
            if np.sum(incorrect_mask) > 0:
                incorrect_conf = max_probs[incorrect_mask]
                print(f"  错误预测 ({np.sum(incorrect_mask)} 个):")
                print(f"    平均置信度: {np.mean(incorrect_conf):.4f}")
                print(f"    最小置信度: {np.min(incorrect_conf):.4f}")
                print(f"    最大置信度: {np.max(incorrect_conf):.4f}")
    
    # 可视化置信度分布
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for class_idx in range(3):
        ax = axes[class_idx]
        class_mask = y_val == class_idx
        class_name = label_names[class_idx]
        
        correct_mask = (y_pred == y_val) & class_mask
        incorrect_mask = (y_pred != y_val) & class_mask
        
        if np.sum(correct_mask) > 0:
            ax.hist(max_probs[correct_mask], alpha=0.6, label='正确预测', bins=20, color='green')
        if np.sum(incorrect_mask) > 0:
            ax.hist(max_probs[incorrect_mask], alpha=0.6, label='错误预测', bins=20, color='red')
        
        ax.set_title(f'{class_name} 预测置信度分布', fontsize=12, fontweight='bold')
        ax.set_xlabel('最大概率')
        ax.set_ylabel('频数')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f'prediction_confidence_{timestamp}.png', dpi=300, bbox_inches='tight')
    print(f"\n预测置信度分布图已保存到: prediction_confidence_{timestamp}.png")
    plt.close()

def main():
    """主函数"""
    print("="*60)
    print("3分类深蹲模型深度分析")
    print("="*60)
    
    # 加载数据
    print("\n[1/6] 加载数据...")
    data_path = "data/pose_landmarks_training.csv"
    X, y = load_data_from_csv(data_path, label_column='label')
    
    # 划分训练集和验证集（与训练时保持一致）
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"训练集: {len(X_train)} 个样本")
    print(f"验证集: {len(X_val)} 个样本")
    
    # 加载模型
    print("\n[2/6] 加载模型...")
    model_path = find_latest_model()
    if model_path is None:
        print("错误: 未找到模型文件")
        return
    
    print(f"加载模型: {model_path}")
    classifier = SquatClassifier()
    classifier.load_model(model_path)
    
    # 评估模型
    print("\n[3/6] 评估模型...")
    val_loss, val_accuracy = classifier.model.evaluate(X_val, y_val, verbose=0)
    print(f"验证集准确率: {val_accuracy:.4f}")
    print(f"验证集损失: {val_loss:.4f}")
    
    y_pred = classifier.model.predict(X_val, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)
    
    label_names = ['站直', '半蹲', '完全蹲下']
    print("\n分类报告:")
    print(classification_report(y_val, y_pred_classes, target_names=label_names))
    
    # 分析训练曲线（如果有历史数据，这里简化处理）
    print("\n[4/6] 分析特征分布...")
    analyze_feature_distribution(X_train, y_train)
    
    print("\n[5/6] 分析类别分离度...")
    analyze_class_separation(X_train, y_train)
    
    print("\n[6/6] 分析误分类...")
    analyze_misclassification(X_val, y_val, y_pred_classes, classifier)
    
    print("\n[7/6] 分析预测置信度...")
    analyze_prediction_confidence(X_val, y_val, classifier)
    
    print("\n[8/6] 生成详细混淆矩阵...")
    visualize_confusion_matrix_detailed(y_val, y_pred_classes)
    
    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)

if __name__ == "__main__":
    main()

