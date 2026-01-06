import csv
import os

def filter_anomalous_data(input_csv, output_csv, 
                          min_visibility_threshold=0.5,
                          min_visible_landmarks=20,
                          max_invalid_coords=5):
    """
    筛选并删除异常的姿态数据
    
    参数:
    - input_csv: 输入CSV文件路径
    - output_csv: 输出CSV文件路径
    - min_visibility_threshold: 关键点可见度阈值（低于此值视为不可见）
    - min_visible_landmarks: 最少可见关键点数量（低于此值视为异常）
    - max_invalid_coords: 最多允许的无效坐标数量（x,y不在0-1范围内）
    """
    
    removed_count = 0
    kept_count = 0
    removed_files = []
    
    with open(input_csv, 'r', encoding='utf-8') as f_in, \
         open(output_csv, 'w', newline='', encoding='utf-8') as f_out:
        
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        # 读取并写入header
        header = next(reader)
        writer.writerow(header)
        
        # 处理每一行数据
        for row in reader:
            if len(row) < 2:  # 跳过空行或格式错误的行
                removed_count += 1
                removed_files.append(row[0] if row else "unknown")
                continue
            
            filename = row[0]
            landmarks = row[1:]  # 从第2列开始是关键点数据
            
            # 检查数据完整性
            if len(landmarks) != 33 * 4:  # 应该有33个关键点，每个4个值
                print(f"[异常] {filename}: 关键点数量不正确 ({len(landmarks)}/132)")
                removed_count += 1
                removed_files.append(filename)
                continue
            
            # 解析关键点数据
            visible_count = 0
            invalid_coords = 0
            
            try:
                for i in range(33):
                    idx = i * 4
                    x = float(landmarks[idx])
                    y = float(landmarks[idx + 1])
                    z = float(landmarks[idx + 2])
                    visibility = float(landmarks[idx + 3])
                    
                    # 检查可见度
                    if visibility >= min_visibility_threshold:
                        visible_count += 1
                    
                    # 检查坐标有效性（x, y应该在0-1范围内）
                    if not (0 <= x <= 1) or not (0 <= y <= 1):
                        invalid_coords += 1
                
                # 判断是否为异常数据
                is_anomalous = False
                reason = []
                
                if visible_count < min_visible_landmarks:
                    is_anomalous = True
                    reason.append(f"可见关键点过少({visible_count}/{min_visible_landmarks})")
                
                if invalid_coords > max_invalid_coords:
                    is_anomalous = True
                    reason.append(f"无效坐标过多({invalid_coords})")
                
                if is_anomalous:
                    print(f"[删除] {filename}: {', '.join(reason)}")
                    removed_count += 1
                    removed_files.append(filename)
                else:
                    writer.writerow(row)
                    kept_count += 1
                    
            except (ValueError, IndexError) as e:
                print(f"[异常] {filename}: 数据解析错误 - {e}")
                removed_count += 1
                removed_files.append(filename)
    
    print(f"\n[统计]")
    print(f"  保留数据: {kept_count} 条")
    print(f"  删除数据: {removed_count} 条")
    print(f"  总计: {kept_count + removed_count} 条")
    
    if removed_files:
        print(f"\n[已删除的文件列表]")
        for f in removed_files[:20]:  # 只显示前20个
            print(f"  - {f}")
        if len(removed_files) > 20:
            print(f"  ... 还有 {len(removed_files) - 20} 个文件")
    
    return kept_count, removed_count, removed_files


if __name__ == "__main__":
    input_file = "pose_landmarks_dunxia.csv"
    output_file = "pose_landmarks_dunxia_filtered.csv"
    
    # 备份原文件
    if os.path.exists(output_file):
        backup_file = output_file.replace(".csv", "_backup.csv")
        if os.path.exists(backup_file):
            os.remove(backup_file)
        os.rename(output_file, backup_file)
        print(f"[备份] 已备份之前的输出文件到: {backup_file}")
    
    print(f"[开始] 筛选异常数据...")
    print(f"  输入文件: {input_file}")
    print(f"  输出文件: {output_file}")
    print(f"  参数: 最少可见关键点={20}, 可见度阈值={0.5}, 最多无效坐标={5}\n")
    
    kept, removed, removed_files = filter_anomalous_data(
        input_file, 
        output_file,
        min_visibility_threshold=0.5,
        min_visible_landmarks=20,
        max_invalid_coords=5
    )
    
    print(f"\n[完成] 筛选完成！")
    print(f"  清理后的数据已保存到: {output_file}")




