import React from 'react';
import { Trophy, Target, Clock, TrendingUp } from 'lucide-react';

interface StatsPanelProps {
  exerciseStats: {
    count: number;
    isCorrect: boolean;
    feedback: string;
    score: number;
  };
  currentExercise: string;
  duration: number;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ 
  exerciseStats, 
  currentExercise,
  duration 
}) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-white bg-opacity-10 backdrop-filter backdrop-blur-lg rounded-xl p-6 space-y-6">
      {/* 当前运动 */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white mb-2">{currentExercise}</h2>
        <div className={`inline-block px-4 py-2 rounded-full text-sm font-medium ${
          exerciseStats.isCorrect ? 'bg-green-500 text-white' : 'bg-yellow-500 text-black'
        }`}>
          {exerciseStats.feedback}
        </div>
      </div>

      {/* 统计数据网格 */}
      <div className="grid grid-cols-2 gap-4">
        {/* 计数 */}
        <div className="exercise-card rounded-lg p-4 text-center">
          <div className="flex items-center justify-center mb-2">
            <Target className="text-blue-400" size={24} />
          </div>
          <div className="text-3xl font-bold text-white mb-1">{exerciseStats.count}</div>
          <div className="text-sm text-gray-300">完成次数</div>
        </div>

        {/* 分数 */}
        <div className="exercise-card rounded-lg p-4 text-center">
          <div className="flex items-center justify-center mb-2">
            <Trophy className="text-yellow-400" size={24} />
          </div>
          <div className="text-3xl font-bold text-white mb-1">{exerciseStats.score}</div>
          <div className="text-sm text-gray-300">总分数</div>
        </div>

        {/* 时间 */}
        <div className="exercise-card rounded-lg p-4 text-center">
          <div className="flex items-center justify-center mb-2">
            <Clock className="text-green-400" size={24} />
          </div>
          <div className="text-3xl font-bold text-white mb-1">{formatTime(duration)}</div>
          <div className="text-sm text-gray-300">运动时间</div>
        </div>

        {/* 准确率 */}
        <div className="exercise-card rounded-lg p-4 text-center">
          <div className="flex items-center justify-center mb-2">
            <TrendingUp className="text-purple-400" size={24} />
          </div>
          <div className="text-3xl font-bold text-white mb-1">
            {exerciseStats.count > 0 ? Math.round((exerciseStats.score / exerciseStats.count) * 100) : 0}%
          </div>
          <div className="text-sm text-gray-300">准确率</div>
        </div>
      </div>

      {/* 进度条 */}
      <div className="space-y-3">
        <div className="text-white text-sm font-medium">今日目标进度</div>
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${Math.min((exerciseStats.count / 20) * 100, 100)}%` }}
          ></div>
        </div>
        <div className="text-right text-gray-300 text-sm">{exerciseStats.count}/20</div>
      </div>

      {/* 成就徽章 */}
      <div className="space-y-3">
        <div className="text-white text-sm font-medium">成就徽章</div>
        <div className="flex space-x-2">
          {exerciseStats.count >= 5 && (
            <div className="w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center">
              🥉
            </div>
          )}
          {exerciseStats.count >= 10 && (
            <div className="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center">
              🥈
            </div>
          )}
          {exerciseStats.count >= 20 && (
            <div className="w-8 h-8 bg-yellow-400 rounded-full flex items-center justify-center">
              🥇
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatsPanel; 