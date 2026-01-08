import { useEffect, useRef, useState, useCallback } from 'react';
import { Pose } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';

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
  const [poseResults, setPoseResults] = useState<PoseResults | null>(null);
  const [exerciseStats, setExerciseStats] = useState<ExerciseStats>({
    count: 0,
    isCorrect: false,
    feedback: '准备开始运动',
    score: 0
  });

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
        setPoseResults(results);
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
    }
  }, []);

  // 绘制姿态关键点
  const drawPose = useCallback((results: PoseResults) => {
    const canvas = canvasRef.current;
    if (!canvas || !results.poseLandmarks) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 绘制关键点
    results.poseLandmarks.forEach((landmark: any, index: number) => {
      const x = landmark.x * canvas.width;
      const y = landmark.y * canvas.height;
      
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, 2 * Math.PI);
      ctx.fillStyle = '#10b981';
      ctx.fill();
    });

    // 绘制骨骼连接线
    drawConnections(ctx, results.poseLandmarks, canvas.width, canvas.height);
  }, []);

  // 绘制骨骼连接线
  const drawConnections = (ctx: CanvasRenderingContext2D, landmarks: any[], width: number, height: number) => {
    const connections = [
      [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], // 上身
      [11, 23], [12, 24], [23, 24], // 躯干
      [23, 25], [25, 27], [24, 26], [26, 28], // 腿部
    ];

    ctx.strokeStyle = '#34d399';
    ctx.lineWidth = 2;

    connections.forEach(([start, end]) => {
      const startPoint = landmarks[start];
      const endPoint = landmarks[end];
      
      if (startPoint && endPoint) {
        ctx.beginPath();
        ctx.moveTo(startPoint.x * width, startPoint.y * height);
        ctx.lineTo(endPoint.x * width, endPoint.y * height);
        ctx.stroke();
      }
    });
  };

  // 分析运动动作（这里可以添加具体的运动分析逻辑）
  const analyzeExercise = useCallback((results: PoseResults) => {
    if (!results.poseLandmarks) return;

    // 这里是简化的分析逻辑，实际项目中需要根据具体运动类型实现
    const landmarks = results.poseLandmarks;
    
    // 检测深蹲动作示例
    const leftKnee = landmarks[25];
    const rightKnee = landmarks[26];
    const leftHip = landmarks[23];
    const rightHip = landmarks[24];

    if (leftKnee && rightKnee && leftHip && rightHip) {
      const kneeAngle = calculateAngle(leftHip, leftKnee, landmarks[27]);
      
      let feedback = '';
      let isCorrect = false;
      
      if (kneeAngle < 90) {
        feedback = '很好！深蹲姿势标准';
        isCorrect = true;
      } else if (kneeAngle < 120) {
        feedback = '可以蹲得更低一些';
        isCorrect = false;
      } else {
        feedback = '准备深蹲...';
        isCorrect = false;
      }

      setExerciseStats(prev => ({
        ...prev,
        isCorrect,
        feedback,
        score: isCorrect ? Math.min(prev.score + 1, 100) : prev.score
      }));
    }
  }, []);

  // 计算角度
  const calculateAngle = (a: any, b: any, c: any) => {
    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    if (angle > 180.0) {
      angle = 360 - angle;
    }
    return angle;
  };

  // 开始检测
  const startDetection = async () => {
    if (!poseRef.current || !cameraRef.current) {
      await initializePose();
    }
    
    if (cameraRef.current) {
      await cameraRef.current.start();
      setIsActive(true);
    }
  };

  // 停止检测
  const stopDetection = () => {
    if (cameraRef.current) {
      cameraRef.current.stop();
      setIsActive(false);
    }
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

  useEffect(() => {
    return () => {
      if (cameraRef.current) {
        cameraRef.current.stop();
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