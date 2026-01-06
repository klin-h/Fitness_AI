import React from 'react';
import { Play, ExternalLink } from 'lucide-react';

interface Exercise {
  id: string;
  name: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  videoUrl: string;
  thumbnail: string;
  targetMuscles: string[];
}

interface ExerciseSelectorProps {
  selectedExercise: string;
  onExerciseSelect: (exerciseId: string) => void;
}

const exercises: Exercise[] = [
  {
    id: 'squat',
    name: '深蹲',
    description: '训练大腿和臀部肌肉的经典动作',
    difficulty: 'easy',
    videoUrl: 'https://www.bilibili.com/video/BV1Rb411w7Hz/?spm_id_from=..search-card.all.click',
    thumbnail: '/api/placeholder/200/150',
    targetMuscles: ['大腿', '臀部', '核心']
  },
  {
    id: 'pushup',
    name: '俯卧撑',
    description: '上肢力量训练的基础动作',
    difficulty: 'medium',
    videoUrl: 'https://www.bilibili.com/video/BV1Ra4y177vh/?spm_id_from=..search-card.all.click',
    thumbnail: '/api/placeholder/200/150',
    targetMuscles: ['胸部', '肩部', '三头肌']
  },
  {
    id: 'plank',
    name: '平板支撑',
    description: '核心稳定性训练的金标准',
    difficulty: 'medium',
    videoUrl: 'https://www.bilibili.com/video/BV1Pq4y117uA/?spm_id_from=..search-card.all.click',
    thumbnail: '/api/placeholder/200/150',
    targetMuscles: ['核心', '肩部', '背部']
  },
  {
    id: 'jumping_jack',
    name: '开合跳',
    description: '全身有氧运动，提高心率',
    difficulty: 'easy',
    videoUrl: 'https://www.bilibili.com/video/BV1dH4y167Tr/?spm_id_from=..search-card.all.click',
    thumbnail: '/api/placeholder/200/150',
    targetMuscles: ['全身', '心肺']
  }
];

const ExerciseSelector: React.FC<ExerciseSelectorProps> = ({ 
  selectedExercise, 
  onExerciseSelect 
}) => {
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-green-500';
      case 'medium': return 'bg-yellow-500';
      case 'hard': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getDifficultyText = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '简单';
      case 'medium': return '中等';
      case 'hard': return '困难';
      default: return '未知';
    }
  };

  return (
    <div>
      <h3 className="text-xl font-bold text-gray-900 mb-4">选择运动</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {exercises.map((exercise) => (
          <div
            key={exercise.id}
            className={`rounded-lg p-4 cursor-pointer transition-all border-2 ${
              selectedExercise === exercise.id 
                ? 'border-blue-600 bg-blue-50' 
                : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50'
            }`}
            onClick={() => onExerciseSelect(exercise.id)}
          >
            {/* 运动标题和难度 */}
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-lg font-semibold text-gray-900">{exercise.name}</h4>
              <span className={`px-2 py-1 rounded-full text-xs font-medium text-white ${getDifficultyColor(exercise.difficulty)}`}>
                {getDifficultyText(exercise.difficulty)}
              </span>
            </div>

            {/* 描述 */}
            <p className="text-gray-600 text-sm mb-3">{exercise.description}</p>

            {/* 目标肌群 */}
            <div className="mb-3">
              <div className="text-xs text-gray-500 mb-1">目标肌群:</div>
              <div className="flex flex-wrap gap-1">
                {exercise.targetMuscles.map((muscle, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full border border-gray-200"
                  >
                    {muscle}
                  </span>
                ))}
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex space-x-2">
              <button
                className={`flex-1 flex items-center justify-center space-x-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedExercise === exercise.id
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  onExerciseSelect(exercise.id);
                }}
              >
                <Play size={16} />
                <span>选择</span>
              </button>

              <button
                className="px-3 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg text-sm font-medium transition-all flex items-center space-x-1 border border-blue-200"
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(exercise.videoUrl, '_blank');
                }}
              >
                <ExternalLink size={16} />
                <span>教学</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 当前选择的运动信息 */}
      {selectedExercise && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-gray-900">
            <span className="font-medium">当前选择: </span>
            {exercises.find(ex => ex.id === selectedExercise)?.name}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExerciseSelector; 