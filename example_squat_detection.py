"""
深蹲状态检测示例
演示如何使用深度学习模型实时检测深蹲状态
"""

import cv2
import mediapipe as mp
import numpy as np
from squat_classifier_api import predict_squat_state_from_mediapipe_results, initialize_classifier

# 初始化MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# 状态名称映射
STATE_NAMES = {0: "站直", 1: "半蹲", 2: "完全蹲下"}
STATE_COLORS = {
    0: (0, 255, 0),    # 绿色 - 站直
    1: (0, 165, 255),  # 橙色 - 半蹲
    2: (255, 0, 0)     # 红色 - 完全蹲下
}


def main():
    # 初始化分类器（首次使用需要训练模型）
    try:
        initialize_classifier('squat_classifier_model.h5')
        print("[INFO] 分类器已初始化")
    except Exception as e:
        print(f"[WARN] 模型文件不存在，将使用未训练的模型: {e}")
        print("[INFO] 请先运行 train_squat_classifier.py 训练模型")
        initialize_classifier()
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return
    
    # 初始化MediaPipe Pose
    with mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        
        print("[INFO] 开始检测，按 'q' 退出")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 转换颜色空间
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            
            # MediaPipe姿态检测
            results = pose.process(image_rgb)
            
            # 转换回BGR用于显示
            image_rgb.flags.writeable = True
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            
            # 绘制姿态关键点
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    image_bgr,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
                
                # 预测深蹲状态
                try:
                    state, confidence, details = predict_squat_state_from_mediapipe_results(results)
                    
                    # 显示结果
                    state_name = details['state_name']
                    state_color = STATE_COLORS[state]
                    
                    # 绘制状态文本
                    text = f"状态: {state_name} ({confidence:.2f})"
                    cv2.putText(image_bgr, text, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, state_color, 2)
                    
                    # 绘制概率信息
                    prob_text = f"站直:{details['probabilities']['站直']:.2f} | " \
                               f"半蹲:{details['probabilities']['半蹲']:.2f} | " \
                               f"完全蹲下:{details['probabilities']['完全蹲下']:.2f}"
                    cv2.putText(image_bgr, prob_text, (10, 70),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                except Exception as e:
                    cv2.putText(image_bgr, f"预测错误: {str(e)}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(image_bgr, "未检测到人体", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # 显示图像
            cv2.imshow('深蹲状态检测', image_bgr)
            
            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cap.release()
    cv2.destroyAllWindows()


def process_single_image(image_path: str):
    """
    处理单张图片
    
    Args:
        image_path: 图片路径
    """
    # 初始化分类器
    try:
        initialize_classifier('squat_classifier_model.h5')
    except:
        initialize_classifier()
    
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] 无法读取图片: {image_path}")
        return
    
    # 转换颜色空间
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # MediaPipe处理
    with mp_pose.Pose(
        static_image_mode=True,
        min_detection_confidence=0.5
    ) as pose:
        results = pose.process(image_rgb)
        
        if results.pose_landmarks:
            # 预测状态
            state, confidence, details = predict_squat_state_from_mediapipe_results(results)
            
            print(f"\n图片: {image_path}")
            print(f"状态: {details['state_name']}")
            print(f"置信度: {confidence:.4f}")
            print(f"概率分布:")
            for state_name, prob in details['probabilities'].items():
                print(f"  {state_name}: {prob:.4f}")
            
            # 绘制结果
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            mp_drawing.draw_landmarks(
                image_bgr,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )
            
            # 添加文本
            text = f"{details['state_name']} ({confidence:.2f})"
            cv2.putText(image_bgr, text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, STATE_COLORS[state], 2)
            
            # 显示
            cv2.imshow('深蹲状态检测', image_bgr)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print(f"[WARN] 未检测到人体姿态: {image_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 处理单张图片
        image_path = sys.argv[1]
        process_single_image(image_path)
    else:
        # 实时视频检测
        main()


