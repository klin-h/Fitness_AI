import React from 'react';
import { Trophy, Target, Clock, TrendingUp } from 'lucide-react';

interface StatsPanelProps {
  exerciseStats: {
    count: number;
    isCorrect: boolean;
    feedback: string;
    score: number;
    correctCount?: number;
    totalCount?: number;
  };
  currentExercise: string;
  duration: number;
  dailyGoal?: {
    current: number;
    target: number;
  };
}

const StatsPanel: React.FC<StatsPanelProps> = ({ 
  exerciseStats, 
  currentExercise,
  duration,
  dailyGoal
}) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      {/* 当前运动 */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{currentExercise}</h2>
        <div className={`inline-block px-4 py-2 rounded-full text-sm font-medium ${
          exerciseStats.isCorrect ? 'bg-green-100 text-green-700 border border-green-200' : 'bg-yellow-100 text-yellow-700 border border-yellow-200'
        }`}>
          {exerciseStats.feedback}
        </div>
      </div>

      {/* 统计数据网格 */}
      <div className="grid grid-cols-2 gap-4">
        {/* 计数 */}
        <div className="bg-blue-50 rounded-lg p-4 text-center border border-blue-100">
          <div className="flex items-center justify-center mb-2">
            <Target className="text-blue-600" size={24} />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{exerciseStats.count}</div>
          <div className="text-sm text-gray-600">完成次数</div>
        </div>

        {/* 分数 */}
        <div className="bg-blue-50 rounded-lg p-4 text-center border border-blue-100">
          <div className="flex items-center justify-center mb-2">
            <Trophy className="text-blue-600" size={24} />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{exerciseStats.score}</div>
          <div className="text-sm text-gray-600">总分数</div>
        </div>

        {/* 时间 */}
        <div className="bg-blue-50 rounded-lg p-4 text-center border border-blue-100">
          <div className="flex items-center justify-center mb-2">
            <Clock className="text-blue-600" size={24} />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{formatTime(duration)}</div>
          <div className="text-sm text-gray-600">运动时间</div>
        </div>

        {/* 准确率 */}
        <div className="bg-blue-50 rounded-lg p-4 text-center border border-blue-100">
          <div className="flex items-center justify-center mb-2">
            <TrendingUp className="text-blue-600" size={24} />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">
            {exerciseStats.totalCount && exerciseStats.totalCount > 0 
              ? Math.min(100, Math.round((exerciseStats.correctCount || 0) / exerciseStats.totalCount * 100))
              : 0}%
          </div>
          <div className="text-sm text-gray-600">准确率</div>
        </div>
      </div>

      {/* 进度条 - 现在使用传入的dailyGoal显示真正的今日目标进度 */}
      {dailyGoal && (
        <div className="space-y-3">
          <div className="flex justify-between text-gray-700 text-sm font-medium">
             <span>今日目标进度</span>
             <span>{dailyGoal.current}/{dailyGoal.target}</span>
          </div>
          <div className="w-full bg-blue-100 rounded-full h-3">
            <div 
              className="bg-blue-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${Math.min((dailyGoal.current / dailyGoal.target) * 100, 100)}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* 成就徽章 */}
      <div className="space-y-3">
        <div className="flex space-x-2">
          {exerciseStats.count >= 5 && (
            <div className="w-8 h-8 bg-yellow-100 border border-yellow-300 rounded-full flex items-center justify-center">
              🥉
            </div>
          )}
          {exerciseStats.count >= 10 && (
            <div className="w-8 h-8 bg-gray-100 border border-gray-300 rounded-full flex items-center justify-center">
              🥈
            </div>
          )}
          {exerciseStats.count >= 20 && (
            <div className="w-8 h-8 bg-yellow-100 border border-yellow-300 rounded-full flex items-center justify-center">
              🥇
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatsPanel; 