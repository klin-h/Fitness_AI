import React from 'react';
import { X, Flame, Clock, Activity, Target, Brain } from 'lucide-react';

interface SessionSummary {
  duration: number; // Duration in minutes
  exercise_type: string;
  total_count: number;
  accuracy: number;
  calories: number;
  ai_comment: string;
}

interface SessionSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary: SessionSummary | null;
}

const SessionSummaryModal: React.FC<SessionSummaryModalProps> = ({ isOpen, onClose, summary }) => {
  if (!isOpen || !summary) return null;

  const exerciseNames: { [key: string]: string } = {
    'squat': '深蹲',
    'pushup': '俯卧撑',
    'plank': '平板支撑',
    'jumping_jack': '开合跳'
  };

  const exerciseName = exerciseNames[summary.exercise_type] || summary.exercise_type;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden animate-scale-in">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-6 text-white relative">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-white/80 hover:text-white hover:bg-white/20 rounded-full p-1 transition-all"
          >
            <X size={24} />
          </button>
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-white/20 rounded-lg backdrop-blur-md">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-2xl font-bold">训练总结</h2>
          </div>
          <p className="text-blue-100 pl-1">
            恭喜你完成了一组 {exerciseName} 训练！
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-orange-50 p-4 rounded-xl border border-orange-100 flex flex-col items-center justify-center">
              <div className="flex items-center space-x-2 text-orange-600 mb-1">
                <Flame size={20} />
                <span className="font-medium">消耗热量</span>
              </div>
              <div className="text-2xl font-bold text-gray-800">
                {summary.calories.toFixed(1)} <span className="text-sm font-normal text-gray-500">kcal</span>
              </div>
            </div>

            <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 flex flex-col items-center justify-center">
              <div className="flex items-center space-x-2 text-blue-600 mb-1">
                <Target size={20} />
                <span className="font-medium">动作次数</span>
              </div>
              <div className="text-2xl font-bold text-gray-800">
                {summary.total_count} <span className="text-sm font-normal text-gray-500">次</span>
              </div>
            </div>

            <div className="bg-green-50 p-4 rounded-xl border border-green-100 flex flex-col items-center justify-center">
              <div className="flex items-center space-x-2 text-green-600 mb-1">
                <Activity size={20} />
                <span className="font-medium">准确率</span>
              </div>
              <div className="text-2xl font-bold text-gray-800">
                {summary.accuracy.toFixed(1)}<span className="text-sm font-normal text-gray-500">%</span>
              </div>
            </div>

            <div className="bg-purple-50 p-4 rounded-xl border border-purple-100 flex flex-col items-center justify-center">
              <div className="flex items-center space-x-2 text-purple-600 mb-1">
                <Clock size={20} />
                <span className="font-medium">训练时长</span>
              </div>
              <div className="text-2xl font-bold text-gray-800">
                {summary.duration.toFixed(1)} <span className="text-sm font-normal text-gray-500">分钟</span>
              </div>
            </div>
          </div>

          {/* AI Feedback Section */}
          <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-5 border border-indigo-100">
            <div className="flex items-center space-x-2 text-indigo-700 mb-3">
              <Brain className="w-5 h-5" />
              <h3 className="font-bold text-lg">AI 智能教练反馈</h3>
            </div>
            <div className="bg-white/60 p-4 rounded-lg text-gray-700 leading-relaxed text-sm shadow-sm">
              {summary.ai_comment || "正在生成智能反馈..."}
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-200 transition-all transform hover:scale-[1.02] active:scale-[0.98]"
          >
            我已知晓
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionSummaryModal;
