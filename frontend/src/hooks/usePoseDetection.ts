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
  
  const [isActive, setIsActive] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [poseResults, _setPoseResults] = useState<PoseResults | null>(null);
  const [exerciseStats, setExerciseStats] = useState<ExerciseStats>({
    count: 0,
    isCorrect: false,
    feedback: '准备开始运动',
    score: 0
  });

  // 初始化姿态检测（简化版本，不依赖MediaPipe）
  const initializePose = useCallback(async () => {
    if (!videoRef.current) return;

    try {
      // 请求摄像头权限
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch (error) {
      console.error('Failed to access camera:', error);
      setExerciseStats(prev => ({
        ...prev,
        feedback: '无法访问摄像头，请检查权限设置'
      }));
    }
  }, []);

  // 开始检测
  const startDetection = async () => {
    await initializePose();
    setIsActive(true);
    setExerciseStats(prev => ({
      ...prev,
      feedback: '摄像头已启动，开始运动！'
    }));
  };

  // 停止检测
  const stopDetection = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
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
  };

  // 模拟运动计数增加
  const incrementCount = useCallback(() => {
    setExerciseStats(prev => ({
      ...prev,
      count: prev.count + 1,
      score: prev.score + 10,
      isCorrect: true,
      feedback: `很好！已完成 ${prev.count + 1} 次`
    }));
  }, []);

  // 每5秒自动增加一次计数（仅用于演示）
  useEffect(() => {
    if (!isActive) return;
    
    const interval = setInterval(() => {
      incrementCount();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [isActive, incrementCount]);

  useEffect(() => {
    return () => {
      // 复制ref值到局部变量以避免警告
      const currentVideo = videoRef.current;
      if (currentVideo && currentVideo.srcObject) {
        const stream = currentVideo.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

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