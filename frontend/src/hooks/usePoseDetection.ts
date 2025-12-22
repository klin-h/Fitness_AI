import { useEffect, useRef, useState, useCallback } from 'react';
import { Pose, Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { api } from '../services/api';

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

export const usePoseDetection = (exerciseType: string = 'squat') => {
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
    lastRequestTime: 0,
    isProcessing: false
  });

  const onResults = useCallback(async (results: Results) => {
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
      
      // 发送数据到后端进行分析
      // 限制请求频率：每100ms发送一次，且等待上一次请求完成
      const now = Date.now();
      if (now - stateRef.current.lastRequestTime > 100 && !stateRef.current.isProcessing) {
        stateRef.current.isProcessing = true;
        stateRef.current.lastRequestTime = now;

        try {
          // 转换关键点数据格式以匹配后端期望
          // MediaPipe JS 返回的是 NormalizedLandmarkList
          const landmarks = results.poseLandmarks;
          
          const response = await api.post('/api/analytics/pose', {
            pose_landmarks: landmarks,
            exercise_type: exerciseType
          });

          if (response && !response.error) {
            setExerciseStats(prev => ({
              count: response.count !== undefined ? response.count : prev.count,
              isCorrect: response.is_correct,
              feedback: response.feedback || prev.feedback,
              score: response.score || prev.score
            }));
          }
        } catch (error) {
          console.error('Pose analysis error:', error);
        } finally {
          stateRef.current.isProcessing = false;
        }
      }
    }
    canvasCtx.restore();
  }, [exerciseType]);

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
    // 重置后端状态可能需要一个新的API，或者依赖后端的超时清理
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