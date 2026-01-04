import React from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';
import { ExerciseStats } from '../hooks/usePoseDetection';

interface CameraViewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  isActive: boolean;
  exerciseStats: ExerciseStats;
  startDetection: () => Promise<void>;
  stopDetection: () => void;
  resetStats: () => void;
}

const CameraView: React.FC<CameraViewProps> = ({
  videoRef,
  canvasRef,
  isActive,
  exerciseStats,
  startDetection,
  stopDetection,
  resetStats
}) => {

  return (
    <div className="relative w-full max-w-4xl mx-auto">
      {/* 摄像头视频 */}
      <div className="relative camera-frame overflow-hidden">
        <video
          ref={videoRef}
          className="w-full h-auto"
          autoPlay
          playsInline
          muted
          style={{ transform: 'scaleX(-1)' }} // 镜像翻转
        />
        
        {/* 姿态检测画布叠加层 */}
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 pointer-events-none"
          style={{ 
            transform: 'scaleX(-1)', // 镜像翻转以匹配video
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            zIndex: 10 // 确保canvas在video之上
          }}
        />
        
        {/* 状态指示器 */}
        <div className="absolute top-4 left-4 z-20">
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium ${
            isActive ? 'bg-green-500 text-white' : 'bg-gray-500 text-white'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-white animate-pulse' : 'bg-gray-300'}`} />
            <span>{isActive ? '检测中' : '未激活'}</span>
          </div>
        </div>

        {/* 动作反馈 */}
        <div className="absolute top-4 right-4 bg-white border border-gray-200 text-gray-900 px-4 py-2 rounded-lg shadow-md z-20">
          <div className={`text-lg font-bold ${exerciseStats.isCorrect ? 'text-green-600' : 'text-yellow-600'}`}>
            {exerciseStats.feedback}
          </div>
        </div>

        {/* 分数显示 */}
        <div className="absolute bottom-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-md z-20">
          <div className="text-2xl font-bold">分数: {exerciseStats.score}</div>
        </div>
      </div>

      {/* 控制按钮 */}
      <div className="flex justify-center space-x-4 mt-6">
        <button
          onClick={isActive ? stopDetection : startDetection}
          className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all shadow-sm hover:shadow-md ${
            isActive 
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {isActive ? <Pause size={20} /> : <Play size={20} />}
          <span>{isActive ? '暂停检测' : '开始检测'}</span>
        </button>

        <button
          onClick={resetStats}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-all shadow-sm hover:shadow-md"
        >
          <RotateCcw size={20} />
          <span>重置数据</span>
        </button>
      </div>
    </div>
  );
};

export default CameraView;
