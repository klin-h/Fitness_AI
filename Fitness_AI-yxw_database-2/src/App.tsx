import React, { useState, useEffect } from 'react';
import CameraView from './components/CameraView';
import StatsPanel from './components/StatsPanel';
import ExerciseSelector from './components/ExerciseSelector';
import { usePoseDetection } from './hooks/usePoseDetection';
import { Activity, Users, Settings } from 'lucide-react';
import './App.css';

function App() {
  const [selectedExercise, setSelectedExercise] = useState('squat');
  const [duration, setDuration] = useState(0);
  const [isTimerActive, setIsTimerActive] = useState(false);
  
  const { exerciseStats, isActive } = usePoseDetection();

  // 计时器效果
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    
    if (isActive && isTimerActive) {
      interval = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    } else if (!isTimerActive) {
      if (interval) clearInterval(interval);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isActive, isTimerActive]);

  // 当开始检测时启动计时器
  useEffect(() => {
    setIsTimerActive(isActive);
    if (!isActive) {
      // 当停止检测时，可以选择重置时间或保持
      // setDuration(0);
    }
  }, [isActive]);

  const getExerciseName = (id: string) => {
    const exerciseNames: { [key: string]: string } = {
      'squat': '深蹲',
      'pushup': '俯卧撑',
      'plank': '平板支撑',
      'jumping_jack': '开合跳'
    };
    return exerciseNames[id] || '未知运动';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900">
      {/* 顶部导航栏 */}
      <nav className="bg-black bg-opacity-30 backdrop-filter backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Activity className="h-8 w-8 text-blue-400" />
              <span className="ml-2 text-xl font-bold text-white">FitnessAI</span>
            </div>
            <div className="flex items-center space-x-4">
              <button className="text-gray-300 hover:text-white">
                <Users size={20} />
              </button>
              <button className="text-gray-300 hover:text-white">
                <Settings size={20} />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容区域 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左侧：摄像头和控制 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 标题区域 */}
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold text-white mb-2">
                智能健身助手
              </h1>
              <p className="text-gray-300">
                实时姿态识别，科学健身指导
              </p>
            </div>

            {/* 摄像头视图 */}
            <CameraView />

            {/* 运动选择器 */}
            <ExerciseSelector
              selectedExercise={selectedExercise}
              onExerciseSelect={setSelectedExercise}
            />
          </div>

          {/* 右侧：统计面板 */}
          <div className="space-y-6">
            <StatsPanel
              exerciseStats={exerciseStats}
              currentExercise={getExerciseName(selectedExercise)}
              duration={duration}
            />

            {/* 快速操作面板 */}
            <div className="bg-white bg-opacity-10 backdrop-filter backdrop-blur-lg rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">快速操作</h3>
              <div className="space-y-3">
                <button 
                  className="w-full bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-all"
                  onClick={() => setDuration(0)}
                >
                  重置计时器
                </button>
                <button className="w-full bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white font-medium py-2 px-4 rounded-lg transition-all">
                  查看历史记录
                </button>
                <button className="w-full bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white font-medium py-2 px-4 rounded-lg transition-all">
                  健身计划定制
                </button>
              </div>
            </div>

            {/* 今日目标 */}
            <div className="bg-white bg-opacity-10 backdrop-filter backdrop-blur-lg rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">今日目标</h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300">深蹲</span>
                  <span className="text-white">15/20</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: '75%' }}></div>
                </div>
                
                <div className="flex justify-between text-sm mt-3">
                  <span className="text-gray-300">运动时长</span>
                  <span className="text-white">{Math.floor(duration / 60)}/30 分钟</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: `${Math.min((duration / 1800) * 100, 100)}%` }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 底部信息 */}
      <footer className="bg-black bg-opacity-30 backdrop-filter backdrop-blur-lg mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="text-center text-gray-400 text-sm">
            <p>FitnessAI - 让科技赋能健康生活 | 基于MediaPipe姿态识别技术</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App; 