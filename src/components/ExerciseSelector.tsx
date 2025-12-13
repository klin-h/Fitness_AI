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
    videoUrl: 'https://www.youtube.com/watch?v=example1',
    thumbnail: '/api/placeholder/200/150',
    targetMuscles: ['大腿', '臀部', '核心']
  },
  {
    id: 'pushup',
    name: '俯卧撑',
    description: '上肢力量训练的基础动作',
    difficulty: 'medium',
    videoUrl: 'https://www.youtube.com/watch?v=example2',
    thumbnail: '/api/placeholder/200/150',
    targetMuscles: ['胸部', '肩部', '三头肌']
  },
  {
    id: 'plank',
    name: '平板支撑',
    description: '核心稳定性训练的金标准',
    difficulty: 'medium',
    videoUrl: 'https://www.youtube.com/watch?v=example3',
    thumbnail: '/api/placeholder/200/150',
    targetMuscles: ['核心', '肩部', '背部']
  },
  {
    id: 'jumping_jack',
    name: '开合跳',
    description: '全身有氧运动，提高心率',
    difficulty: 'easy',
    videoUrl: 'https://www.youtube.com/watch?v=example4',
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
    <div className="bg-white bg-opacity-10 backdrop-filter backdrop-blur-lg rounded-xl p-6">
      <h3 className="text-xl font-bold text-white mb-4">选择运动</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {exercises.map((exercise) => (
          <div
            key={exercise.id}
            className={`exercise-card rounded-lg p-4 cursor-pointer transition-all hover:scale-105 ${
              selectedExercise === exercise.id 
                ? 'ring-2 ring-blue-400 bg-blue-500 bg-opacity-20' 
                : 'hover:bg-white hover:bg-opacity-20'
            }`}
            onClick={() => onExerciseSelect(exercise.id)}
          >
            {/* 运动标题和难度 */}
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-lg font-semibold text-white">{exercise.name}</h4>
              <span className={`px-2 py-1 rounded-full text-xs font-medium text-white ${getDifficultyColor(exercise.difficulty)}`}>
                {getDifficultyText(exercise.difficulty)}
              </span>
            </div>

            {/* 描述 */}
            <p className="text-gray-300 text-sm mb-3">{exercise.description}</p>

            {/* 目标肌群 */}
            <div className="mb-3">
              <div className="text-xs text-gray-400 mb-1">目标肌群:</div>
              <div className="flex flex-wrap gap-1">
                {exercise.targetMuscles.map((muscle, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-gray-600 text-white text-xs rounded-full"
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
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-600 hover:bg-gray-500 text-white'
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
                className="px-3 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium transition-all flex items-center space-x-1"
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
        <div className="mt-6 p-4 bg-blue-500 bg-opacity-20 rounded-lg border border-blue-400">
          <div className="text-white">
            <span className="font-medium">当前选择: </span>
            {exercises.find(ex => ex.id === selectedExercise)?.name}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExerciseSelector; 