import React from 'react';
import { Play, Pause, RotateCcw, AlertCircle, CheckCircle, Loader } from 'lucide-react';

interface CameraViewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  isActive: boolean;
  isInitialized: boolean;
  initError: string | null;
  exerciseStats: any;
  startDetection: () => void;
  stopDetection: () => void;
  resetStats: () => void;
  isCountingDown: boolean;
  countdown: number;
}

const CameraView: React.FC<CameraViewProps> = ({
  videoRef,
  canvasRef,
  isActive,
  isInitialized,
  initError,
  exerciseStats,
  startDetection,
  stopDetection,
  resetStats,
  isCountingDown,
  countdown
}) => {
  // 获取状态指示器信息
  const getStatusInfo = () => {
    if (initError) {
      return {
        color: 'bg-red-500',
        icon: <AlertCircle size={16} />,
        text: '初始化失败',
        pulse: false
      };
    }
    
    if (!isInitialized) {
      return {
        color: 'bg-yellow-500',
        icon: <Loader size={16} className="animate-spin" />,
        text: '正在初始化',
        pulse: true
      };
    }
    
    if (isCountingDown) {
      return {
        color: 'bg-orange-500',
        icon: <CheckCircle size={16} />,
        text: '准备开始',
        pulse: true
      };
    }
    
    if (isActive) {
      return {
        color: 'bg-green-500',
        icon: <CheckCircle size={16} />,
        text: '检测中',
        pulse: true
      };
    }
    
    return {
      color: 'bg-blue-500',
      icon: <CheckCircle size={16} />,
      text: '已就绪',
      pulse: false
    };
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="relative w-full max-w-4xl mx-auto">
      {/* 摄像头视频容器 */}
      <div className="camera-frame overflow-hidden">
        {/* 视频元素 */}
        <video
          ref={videoRef}
          className="w-full h-auto"
          autoPlay
          playsInline
          muted
          style={{ 
            transform: 'scaleX(-1)',
            display: isActive ? 'block' : 'block'
          }}
          width={640}
          height={480}
        />
        
        {/* 姿态检测画布叠加层 */}
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full pose-overlay"
          width={640}
          height={480}
          style={{ 
            transform: 'scaleX(-1)',
            pointerEvents: 'none'
          }}
        />
        
        {/* 状态指示器 */}
        <div className="absolute top-4 left-4">
          <div className={`status-indicator ${isActive || isCountingDown ? 'active' : 'inactive'} ${statusInfo.pulse ? 'pulse' : ''}`}>
            {statusInfo.icon}
            <span>{statusInfo.text}</span>
          </div>
        </div>

        {/* MediaPipe状态指示器 */}
        <div className="absolute top-4 right-4 max-w-xs">
          <div className="bg-black bg-opacity-70 text-white px-4 py-2 rounded-lg">
            <div className={`text-sm font-bold ${
              exerciseStats.isCorrect ? 'text-green-400' : 
              initError ? 'text-red-400' : 
              !isInitialized ? 'text-yellow-400' : 'text-blue-400'
            }`}>
            {exerciseStats.feedback}
            </div>
            
            {/* 显示初始化错误详情 */}
            {initError && (
              <div className="text-xs text-red-300 mt-1">
                错误: {initError}
              </div>
            )}
          </div>
        </div>

        {/* 计数显示 */}
        <div className="absolute bottom-4 left-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-4 py-2 rounded-lg">
          <div className="text-xl font-bold">次数: {exerciseStats.count}</div>
        </div>

        {/* 分数显示 */}
        <div className="absolute bottom-4 right-4 bg-gradient-to-r from-green-500 to-blue-600 text-white px-4 py-2 rounded-lg">
          <div className="text-xl font-bold">分数: {exerciseStats.score}</div>
        </div>

        {/* 准确率显示 */}
        <div className="absolute bottom-16 right-4 bg-gradient-to-r from-purple-500 to-pink-600 text-white px-4 py-2 rounded-lg">
          <div className="text-sm font-bold">
            准确率: {(exerciseStats.accuracy * 100).toFixed(1)}%
          </div>
        </div>

        {/* 倒计时叠加层 */}
        {isCountingDown && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-70 z-20">
            <div className="text-center text-white">
              <div className="text-8xl font-bold mb-4 animate-pulse text-red-500">
                {countdown}
              </div>
              <div className="text-xl font-medium">准备开始运动...</div>
            </div>
          </div>
        )}

        {/* 未激活时的提示 */}
        {!isActive && !isCountingDown && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
            <div className="text-center text-white max-w-md px-4">
              {!isInitialized ? (
                // 初始化中
                <div>
                  <Loader className="w-12 h-12 mx-auto mb-4 animate-spin" />
                  <div className="text-lg font-medium mb-2">正在初始化MediaPipe</div>
                  <div className="text-sm opacity-75">首次加载可能需要几秒钟...</div>
                </div>
              ) : initError ? (
                // 初始化失败
                <div>
                  <AlertCircle className="w-12 h-12 mx-auto mb-4 text-red-400" />
                  <div className="text-lg font-medium mb-2 text-red-400">初始化失败</div>
                  <div className="text-sm opacity-75 mb-4">{initError}</div>
                  <div className="text-xs text-gray-300">
                    <div>解决方案:</div>
                    <div>• 刷新页面重试</div>
                    <div>• 检查网络连接</div>
                    <div>• 使用Chrome浏览器</div>
                  </div>
                </div>
              ) : (
                // 就绪状态
                <div>
                  <div className="text-2xl mb-4">📷</div>
                  <div className="text-lg font-medium mb-2">摄像头未启动</div>
                  <div className="text-sm opacity-75">点击"开始检测"启动姿态识别</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 控制按钮 */}
      <div className="flex justify-center space-x-4 mt-6">
        <button
          onClick={isActive ? stopDetection : startDetection}
          disabled={initError !== null}
          className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all ${
            initError 
              ? 'bg-gray-400 cursor-not-allowed text-gray-600'
              : isActive || isCountingDown
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-green-500 hover:bg-green-600 text-white'
          }`}
        >
          {isActive || isCountingDown ? <Pause size={20} /> : <Play size={20} />}
          <span>
            {initError 
              ? '初始化失败' 
              : isCountingDown 
              ? '取消倒计时'
              : isActive 
              ? '停止检测' 
              : !isInitialized 
              ? '初始化中...' 
              : '开始检测'}
          </span>
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