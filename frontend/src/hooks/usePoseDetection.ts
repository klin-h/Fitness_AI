import { useEffect, useRef, useState, useCallback } from 'react';
import { Pose, Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';

export interface PoseResults {
  poseLandmarks?: any;
  poseWorldLandmarks?: any;
}

export interface ExerciseStats {
  count: number;
  isCorrect: boolean;
  feedback: string;
  score: number;
}

export const usePoseDetection = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const poseRef = useRef<Pose | null>(null);
  const cameraRef = useRef<Camera | null>(null);
  
  const [isActive, setIsActive] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [poseResults, setPoseResults] = useState<PoseResults | null>(null);
  const [exerciseStats, setExerciseStats] = useState<ExerciseStats>({
    count: 0,
    isCorrect: false,
    feedback: '准备开始运动',
    score: 0
  });

  // 动作状态追踪
  const stateRef = useRef({
    isSquatting: false,
    lastFeedbackTime: 0
  });

  // 计算角度辅助函数
  const calculateAngle = (a: any, b: any, c: any) => {
    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    if (angle > 180.0) angle = 360 - angle;
    return angle;
  };

  const onResults = useCallback((results: Results) => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvasCtx = canvasRef.current.getContext('2d');
    if (!canvasCtx) return;

    // 设置画布尺寸匹配视频
    canvasRef.current.width = videoRef.current.videoWidth;
    canvasRef.current.height = videoRef.current.videoHeight;

    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    
    // 绘制骨架
    if (results.poseLandmarks) {
      drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS,
                     {color: '#00FF00', lineWidth: 4});
      drawLandmarks(canvasCtx, results.poseLandmarks,
                    {color: '#FF0000', lineWidth: 2});
      
      // 简单的深蹲计数逻辑
      const landmarks = results.poseLandmarks;
      
      // 获取左腿关键点 (23: 左髋, 25: 左膝, 27: 左踝)
      const leftHip = landmarks[23];
      const leftKnee = landmarks[25];
      const leftAnkle = landmarks[27];

      // 获取右腿关键点 (24: 右髋, 26: 右膝, 28: 右踝)
      const rightHip = landmarks[24];
      const rightKnee = landmarks[26];
      const rightAnkle = landmarks[28];

      if (leftHip && leftKnee && leftAnkle && rightHip && rightKnee && rightAnkle) {
        const leftAngle = calculateAngle(leftHip, leftKnee, leftAnkle);
        const rightAngle = calculateAngle(rightHip, rightKnee, rightAnkle);
        const avgAngle = (leftAngle + rightAngle) / 2;

        // 深蹲判定逻辑
        // 站立状态: 角度 > 160
        // 下蹲状态: 角度 < 100
        
        if (avgAngle < 100) {
          if (!stateRef.current.isSquatting) {
            stateRef.current.isSquatting = true;
            setExerciseStats(prev => ({
              ...prev,
              feedback: '保持住，姿势不错！',
              isCorrect: true
            }));
          }
        } else if (avgAngle > 160) {
          if (stateRef.current.isSquatting) {
            stateRef.current.isSquatting = false;
            setExerciseStats(prev => ({
              ...prev,
              count: prev.count + 1,
              score: prev.score + 10,
              feedback: `完成！当前个数: ${prev.count + 1}`,
              isCorrect: true
            }));
          }
        }
      }
    }
    canvasCtx.restore();
  }, []);

  // 初始化姿态检测
  const initializePose = useCallback(async () => {
    if (poseRef.current) return;

    const pose = new Pose({locateFile: (file) => {
      return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
    }});

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
      smoothSegmentation: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    });

    pose.onResults(onResults);
    poseRef.current = pose;

    if (videoRef.current) {
      const camera = new Camera(videoRef.current, {
        onFrame: async () => {
          if (poseRef.current && videoRef.current) {
            await poseRef.current.send({image: videoRef.current});
          }
        },
        width: 640,
        height: 480
      });
      cameraRef.current = camera;
    }
  }, [onResults]);

  // 开始检测
  const startDetection = async () => {
    await initializePose();
    if (cameraRef.current) {
      await cameraRef.current.start();
      setIsActive(true);
      setExerciseStats(prev => ({
        ...prev,
        feedback: '摄像头已启动，请站在画面中'
      }));
    }
  };

  // 停止检测
  const stopDetection = () => {
    if (cameraRef.current) {
      cameraRef.current.stop();
    }
    setIsActive(false);
    setExerciseStats(prev => ({
      ...prev,
      feedback: '检测已停止'
    }));
  };

  // 重置统计
  const resetStats = () => {
    setExerciseStats({
      count: 0,
      isCorrect: false,
      feedback: '准备开始运动',
      score: 0
    });
    stateRef.current.isSquatting = false;
  };

  return {
    videoRef,
    canvasRef,
    isActive,
    poseResults,
    exerciseStats,
    startDetection,
    stopDetection,
    resetStats
  };
}; 