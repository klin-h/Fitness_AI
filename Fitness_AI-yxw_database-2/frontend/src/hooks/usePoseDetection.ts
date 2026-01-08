import { useEffect, useRef, useState, useCallback } from 'react';
import { Pose, Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { createAnalyzer, Landmark } from '../utils/exerciseAnalyzer';

export interface PoseResults {
  poseLandmarks?: any;
  poseWorldLandmarks?: any;
}

export interface ExerciseStats {
  count: number;
  isCorrect: boolean;
  feedback: string;
  score: number;
  duration?: number; // 用于平板支撑等计时类运动
  correctCount: number; // 正确动作次数
  totalCount: number; // 总动作次数（用于计算准确率）
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
    score: 0,
    correctCount: 0,
    totalCount: 0
  });

  // 当运动类型改变时，更新分析器
  useEffect(() => {
    analyzerRef.current = createAnalyzer(exerciseType);
    setExerciseStats({
      count: 0,
      isCorrect: false,
      feedback: '准备开始运动',
      score: 0,
      correctCount: 0,
      totalCount: 0
    });
  }, [exerciseType]);

  // 绘制姿态关键点
  const drawPose = useCallback((results: any) => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvasCtx = canvasRef.current.getContext('2d');
    if (!canvasCtx) return;

    // 获取video的实际尺寸
    const videoWidth = videoRef.current.videoWidth || videoRef.current.clientWidth;
    const videoHeight = videoRef.current.videoHeight || videoRef.current.clientHeight;

    // 设置画布尺寸（必须与实际显示尺寸匹配）
    if (canvasRef.current.width !== videoWidth || canvasRef.current.height !== videoHeight) {
      canvasRef.current.width = videoWidth;
      canvasRef.current.height = videoHeight;
    }

    // 清除画布
    canvasCtx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    
    // 绘制视频帧（如果需要）
    if (results.image) {
      canvasCtx.drawImage(
        results.image,
        0,
        0,
        canvasRef.current.width,
        canvasRef.current.height
      );
    }

    // 绘制姿态关键点和连接线
    if (results.poseLandmarks && results.poseLandmarks.length > 0) {
      // 绘制骨骼连接线（绿色）
      drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {
        color: '#00FF00',
        lineWidth: 3
      });
      
      // 绘制关键点（红色）
      drawLandmarks(canvasCtx, results.poseLandmarks, {
        color: '#FF0000',
        lineWidth: 2,
        radius: 5
      });
    }
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
      
      // 累计总动作次数（每次分析都算一次）
      const newTotalCount = prev.totalCount + 1;
      
      // 如果动作正确，累计正确次数
      const newCorrectCount = analysis.isCorrect ? prev.correctCount + 1 : prev.correctCount;
      
      // 只有当计数、时长、反馈或分数真正改变时才更新
      const shouldUpdate = 
        (analysis.count !== undefined && analysis.count !== prev.count) ||
        (analysis.duration !== undefined && analysis.duration !== (prev.duration || 0)) ||
        analysis.feedback !== prev.feedback ||
        analysis.score !== prev.score ||
        analysis.isCorrect !== prev.isCorrect;

      if (!shouldUpdate) {
        return prev;
      }

      return {
        count: newCount,
        isCorrect: analysis.isCorrect,
        feedback: analysis.feedback,
        score: analysis.score,
        duration: newDuration,
        correctCount: newCorrectCount,
        totalCount: newTotalCount
      };
    });
  }, []);

  // 初始化MediaPipe Pose
  const initializePose = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;

    try {
      // 使用多个备用 CDN 镜像，提高加载成功率
      // MediaPipe 的 locateFile 是同步的，所以我们需要选择一个最可靠的 CDN
      // 优先使用 jsdelivr，如果失败 MediaPipe 会抛出错误，我们可以在 catch 中处理
      const pose = new Pose({
        locateFile: (file) => {
          // 优先使用 jsdelivr CDN（通常最稳定且在中国大陆访问较好）
          // 如果失败，MediaPipe 会抛出错误，我们可以在 catch 中捕获并提示用户
          return `https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5.1675469404/${file}`;
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
    } catch (error: any) {
      console.error('Failed to initialize pose detection:', error);
      const errorMessage = error?.message || String(error);
      
      // 根据错误类型提供更具体的提示
      let feedback = '初始化姿态检测失败';
      if (errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('timeout')) {
        feedback = '网络连接失败，请检查网络后重试';
      } else if (errorMessage.includes('camera') || errorMessage.includes('permission')) {
        feedback = '无法访问摄像头，请检查权限设置';
      } else {
        feedback = '初始化失败，请刷新页面重试';
      }
      
      setExerciseStats(prev => ({
        ...prev,
        feedback
      }));
    }
  }, [drawPose, analyzeExercise]);

  // 开始检测
  const startDetection = async () => {
    try {
      if (!poseRef.current || !cameraRef.current) {
        await initializePose();
      }
      
      if (!poseRef.current) {
        setExerciseStats(prev => ({
          ...prev,
          feedback: '姿态检测初始化失败，请刷新页面重试'
        }));
        return;
      }
      
      if (cameraRef.current) {
        await cameraRef.current.start();
        setIsActive(true);
        setExerciseStats(prev => ({
          ...prev,
          feedback: '摄像头已启动，开始运动！'
        }));
      }
    } catch (error: any) {
      console.error('启动检测失败:', error);
      const errorMessage = error?.message || String(error);
      
      let feedback = '启动失败';
      if (errorMessage.includes('camera') || errorMessage.includes('permission')) {
        feedback = '无法访问摄像头，请检查浏览器权限设置';
      } else if (errorMessage.includes('NotAllowedError')) {
        feedback = '摄像头权限被拒绝，请在浏览器设置中允许摄像头访问';
      } else {
        feedback = '启动失败，请刷新页面重试';
      }
      
      setExerciseStats(prev => ({
        ...prev,
        feedback
      }));
      setIsActive(false);
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
    analyzerRef.current.reset();
    setExerciseStats({
      count: 0,
      isCorrect: false,
      feedback: '准备开始运动',
      score: 0,
      duration: 0,
      correctCount: 0,
      totalCount: 0
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
