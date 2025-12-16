import { useEffect, useRef, useState, useCallback } from 'react';
import { Pose } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { POSE_CONNECTIONS } from '@mediapipe/pose';
import { createAnalyzer, Landmark } from '../utils/exerciseAnalyzer';

export interface PoseResults {
  poseLandmarks?: Landmark[];
  poseWorldLandmarks?: any;
}

export interface ExerciseStats {
  count: number;
  isCorrect: boolean;
  feedback: string;
  score: number;
  duration?: number; // 用于平板支撑等计时类运动
}

export const usePoseDetection = (exerciseType: string = 'squat') => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const poseRef = useRef<Pose | null>(null);
  const cameraRef = useRef<Camera | null>(null);
  const analyzerRef = useRef(createAnalyzer(exerciseType));
  
  const [isActive, setIsActive] = useState(false);
  const [poseResults, setPoseResults] = useState<PoseResults | null>(null);
  const [exerciseStats, setExerciseStats] = useState<ExerciseStats>({
    count: 0,
    isCorrect: false,
    feedback: '准备开始运动',
    score: 0
  });

  // 当运动类型改变时，更新分析器
  useEffect(() => {
    analyzerRef.current = createAnalyzer(exerciseType);
    setExerciseStats({
      count: 0,
      isCorrect: false,
      feedback: '准备开始运动',
      score: 0
    });
  }, [exerciseType]);

  // 绘制姿态关键点
  const drawPose = useCallback((results: any) => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvasCtx = canvasRef.current.getContext('2d');
    if (!canvasCtx) return;

    // 设置画布尺寸
    canvasRef.current.width = videoRef.current.videoWidth;
    canvasRef.current.height = videoRef.current.videoHeight;

    // 清除画布
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    canvasCtx.drawImage(
      results.image,
      0,
      0,
      canvasRef.current.width,
      canvasRef.current.height
    );

      // 绘制姿态关键点和连接线
      if (results.poseLandmarks) {
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {
          color: '#00FF00',
          lineWidth: 2
        });
      drawLandmarks(canvasCtx, results.poseLandmarks, {
        color: '#FF0000',
        lineWidth: 1,
        radius: 3
      });
    }

    canvasCtx.restore();
  }, []);

  // 分析运动动作
  const analyzeExercise = useCallback((results: any) => {
    if (!results.poseLandmarks || results.poseLandmarks.length === 0) {
      return;
    }

    const landmarks: Landmark[] = results.poseLandmarks.map((lm: any) => ({
      x: lm.x,
      y: lm.y,
      z: lm.z,
      visibility: lm.visibility
    }));

    // 使用分析器分析动作
    const analysis = analyzerRef.current.analyze(landmarks);

    // 更新统计信息
    setExerciseStats(prev => {
      // 对于计数类运动，使用分析器的计数
      // 对于平板支撑，使用分析器的时长（存储在 duration 字段）
      const newCount = analysis.count !== undefined ? analysis.count : prev.count;
      const newDuration = analysis.duration !== undefined ? analysis.duration : prev.duration;
      
      // 只有当计数、时长、反馈或分数真正改变时才更新
      const shouldUpdate = 
        (analysis.count !== undefined && analysis.count !== prev.count) ||
        (analysis.duration !== undefined && analysis.duration !== (prev.duration || 0)) ||
        analysis.feedback !== prev.feedback ||
        analysis.score !== prev.score;

      if (!shouldUpdate) {
        return prev;
      }

      return {
        count: newCount,
        isCorrect: analysis.isCorrect,
        feedback: analysis.feedback,
        score: analysis.score,
        duration: newDuration
      };
    });
  }, []);

  // 初始化MediaPipe Pose
  const initializePose = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;

    try {
      const pose = new Pose({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
      });

      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      pose.onResults((results) => {
        setPoseResults({
          poseLandmarks: results.poseLandmarks,
          poseWorldLandmarks: results.poseWorldLandmarks
        });
        drawPose(results);
        analyzeExercise(results);
      });

      poseRef.current = pose;

      const camera = new Camera(videoRef.current, {
        onFrame: async () => {
          if (poseRef.current && videoRef.current) {
            await poseRef.current.send({ image: videoRef.current });
      }
        },
        width: 640,
        height: 480
      });

      cameraRef.current = camera;
    } catch (error) {
      console.error('Failed to initialize pose detection:', error);
      setExerciseStats(prev => ({
        ...prev,
        feedback: '初始化姿态检测失败，请刷新页面重试'
      }));
    }
  }, [drawPose, analyzeExercise]);

  // 开始检测
  const startDetection = async () => {
    if (!poseRef.current || !cameraRef.current) {
    await initializePose();
    }
    
    if (cameraRef.current) {
      await cameraRef.current.start();
    setIsActive(true);
    setExerciseStats(prev => ({
      ...prev,
      feedback: '摄像头已启动，开始运动！'
    }));
    }
  };

  // 停止检测
  const stopDetection = () => {
    if (cameraRef.current) {
      cameraRef.current.stop();
    setIsActive(false);
    setExerciseStats(prev => ({
      ...prev,
      feedback: '检测已停止'
    }));
    }
  };

  // 重置统计
  const resetStats = () => {
    analyzerRef.current.reset();
    setExerciseStats({
      count: 0,
      isCorrect: false,
      feedback: '准备开始运动',
      score: 0,
      duration: 0
    });
  };

  // 清理资源
  useEffect(() => {
    return () => {
      if (cameraRef.current) {
        cameraRef.current.stop();
      }
      // 复制ref值到局部变量以避免警告
      const currentVideo = videoRef.current;
      if (currentVideo && currentVideo.srcObject) {
        const stream = currentVideo.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
        currentVideo.srcObject = null;
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