import os
import glob
import csv

import cv2
import mediapipe as mp


def extract_pose_landmarks_from_images(
    image_dir: str,
    output_csv: str,
    image_extensions=(".jpg", ".jpeg", ".png", ".bmp"),
):
    """
    从指定文件夹中读取图片，使用 MediaPipe Pose 提取 33 个身体关键点，
    并将结果保存到 CSV 文件中。

    每行格式：
    filename, 0_x,0_y,0_z,0_visibility, 1_x,..., 32_visibility
    """

    # 收集所有图片路径
    image_paths = []
    for ext in image_extensions:
        image_paths.extend(glob.glob(os.path.join(image_dir, f"*{ext}")))
        image_paths.extend(glob.glob(os.path.join(image_dir, f"*{ext.upper()}")))

    image_paths = sorted(set(image_paths))
    if not image_paths:
        print(f"[WARN] 在文件夹 {image_dir} 下没有找到图片")
        return

    print(f"[INFO] 在 {image_dir} 找到 {len(image_paths)} 张图片")

    mp_pose = mp.solutions.pose

    # 构造 CSV header
    header = ["filename"]
    for i in range(33):  # 33 个关键点
        header.extend([f"{i}_x", f"{i}_y", f"{i}_z", f"{i}_visibility"])

    # 打开 CSV 文件准备写入
    with open(output_csv, "w", newline="", encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(header)

        # 使用 MediaPipe Pose
        with mp_pose.Pose(
            static_image_mode=True,      # 处理单张图片，设置为 True
            model_complexity=1,          # 模型复杂度（0/1/2）
            enable_segmentation=False,
            min_detection_confidence=0.5
        ) as pose:

            for idx, img_path in enumerate(image_paths):
                print(f"[INFO] ({idx+1}/{len(image_paths)}) 处理: {img_path}")

                image_bgr = cv2.imread(img_path)
                if image_bgr is None:
                    print(f"[WARN] 无法读取图片: {img_path}")
                    continue

                image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

                results = pose.process(image_rgb)

                if not results.pose_landmarks:
                    print(f"[WARN] 未检测到人体: {img_path}")
                    # 如果希望即使没检测到也写一行，可以在这里写入空值
                    continue

                # 将 33 个 landmark 展平为一维列表
                row = [os.path.basename(img_path)]  # 第一列为文件名
                for lm in results.pose_landmarks.landmark:
                    # x, y 为归一化坐标 (0~1)，z 为相对深度，visibility 为可见度
                    row.extend([lm.x, lm.y, lm.z, lm.visibility])

                writer.writerow(row)

    print(f"[INFO] 关键点数据已保存到: {output_csv}")


if __name__ == "__main__":
    # 你可以在这里修改默认的输入文件夹和输出 CSV 路径
    image_folder = "./image/dunxia"            # 替换成你的图片目录
    output_file = "./pose_landmarks_dunxia.csv" # 输出文件路径

    extract_pose_landmarks_from_images(image_folder, output_file)