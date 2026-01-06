import React from 'react';
import { usePoseDetection } from '../hooks/usePoseDetection';
import { Play, Pause, RotateCcw } from 'lucide-react';

const CameraView: React.FC = () => {
  const {
    videoRef,
    canvasRef,
    isActive,
    exerciseStats,
    startDetection,
    stopDetection,
    resetStats
  } = usePoseDetection();

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
          className="pose-overlay"
          width={640}
          height={480}
          style={{ transform: 'scaleX(-1)' }}
        />
        
        {/* 状态指示器 */}
        <div className="absolute top-4 left-4">
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium ${
            isActive ? 'bg-green-500 text-white' : 'bg-gray-500 text-white'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-white animate-pulse' : 'bg-gray-300'}`} />
            <span>{isActive ? '检测中' : '未激活'}</span>
          </div>
        </div>

        {/* 动作反馈 */}
        <div className="absolute top-4 right-4 bg-black bg-opacity-50 text-white px-4 py-2 rounded-lg">
          <div className={`text-lg font-bold ${exerciseStats.isCorrect ? 'text-green-400' : 'text-yellow-400'}`}>
            {exerciseStats.feedback}
          </div>
        </div>

        {/* 分数显示 */}
        <div className="absolute bottom-4 right-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-4 py-2 rounded-lg">
          <div className="text-2xl font-bold">分数: {exerciseStats.score}</div>
        </div>
      </div>

      {/* 控制按钮 */}
      <div className="flex justify-center space-x-4 mt-6">
        <button
          onClick={isActive ? stopDetection : startDetection}
          className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all ${
            isActive 
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-green-500 hover:bg-green-600 text-white'
          }`}
        >
          {isActive ? <Pause size={20} /> : <Play size={20} />}
          <span>{isActive ? '暂停检测' : '开始检测'}</span>
        </button>

        <button
          onClick={resetStats}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-all"
        >
          <RotateCcw size={20} />
          <span>重置数据</span>
        </button>
      </div>
    </div>
  );
};

export default CameraView; 