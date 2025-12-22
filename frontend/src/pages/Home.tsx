import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import CameraView from '../components/CameraView';
import StatsPanel from '../components/StatsPanel';
import ExerciseSelector from '../components/ExerciseSelector';
import { usePoseDetection } from '../hooks/usePoseDetection';
import { Activity, User, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';

function Home() {
  const [selectedExercise, setSelectedExercise] = useState('squat');
  const [duration, setDuration] = useState(0);
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const previousCountRef = useRef(0);
  
  // 用户健身计划
  const [userPlan, setUserPlan] = useState<{
    daily_goals?: {
      squat?: number;
      pushup?: number;
      plank?: number;
      jumping_jack?: number;
    };
    weekly_goals?: {
      total_sessions?: number;
      total_duration?: number;
    };
  } | null>(null);
  
  const {
    videoRef,
    canvasRef,
    isActive,
    exerciseStats,
    startDetection,
    stopDetection,
    resetStats
  } = usePoseDetection(selectedExercise);

  // 包装 startDetection 以添加会话创建
  const handleStartDetection = async () => {
    await startDetection();
    
    // 创建新的运动会话
    if (user && token) {
      try {
        const response = await api.post(
          '/api/session/start',
          {
            exercise_type: selectedExercise,
            user_id: user.user_id
          },
          token
        );
        setSessionId(response.session_id);
        previousCountRef.current = 0; // 重置计数
      } catch (err) {
        console.error('创建运动会话失败:', err);
      }
    }
  };

  // 包装 stopDetection 以添加会话结束
  const handleStopDetection = async () => {
    await stopDetection();
    
    // 结束运动会话
    if (sessionId && token) {
      try {
        await api.post(
          `/api/session/${sessionId}/end`,
          {},
          token
        );
        setSessionId(null);
      } catch (err) {
        console.error('结束运动会话失败:', err);
      }
    }
  };

  // 当运动计数增加时，更新会话数据
  useEffect(() => {
    if (sessionId && token && isActive && exerciseStats.count > previousCountRef.current) {
      const countDiff = exerciseStats.count - previousCountRef.current;
      previousCountRef.current = exerciseStats.count;
      
      // 提交每次计数增加的数据
      api.post(
        `/api/session/${sessionId}/data`,
        {
          is_correct: exerciseStats.isCorrect,
          score: exerciseStats.score,
          feedback: exerciseStats.feedback,
          pose_data: null // 实际项目中可以包含姿态数据
        },
        token
      ).catch(err => {
        console.error('提交运动数据失败:', err);
      });
    }
  }, [exerciseStats.count, sessionId, token, isActive, exerciseStats.isCorrect, exerciseStats.score, exerciseStats.feedback]);

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

  // 加载用户健身计划
  useEffect(() => {
    const loadUserPlan = async () => {
      if (!user || !token) return;
      
      try {
        const plan = await api.get('/api/user/plan', token);
        setUserPlan(plan);
      } catch (err) {
        console.error('加载健身计划失败:', err);
      }
    };

    loadUserPlan();
  }, [user, token]);

  const getExerciseName = (id: string) => {
    const exerciseNames: { [key: string]: string } = {
      'squat': '深蹲',
      'pushup': '俯卧撑',
      'plank': '平板支撑',
      'jumping_jack': '开合跳'
    };
    return exerciseNames[id] || '未知运动';
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-blue-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white border-b border-blue-100 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <Activity className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">
                FitnessAI
              </span>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => navigate('/profile')}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-50 hover:bg-blue-100 rounded-lg text-gray-700 hover:text-blue-700 transition-all"
                title="个人中心"
              >
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                  {(user?.nickname || user?.username)?.[0]?.toUpperCase()}
                </div>
                <span className="hidden sm:inline font-medium">{user?.nickname || user?.username}</span>
                <User size={18} className="sm:hidden" />
              </button>
              <button
                onClick={handleLogout}
                className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                title="退出登录"
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容区域 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 标题区域 - 居中显示 */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-gray-900 mb-3">
            智能健身助手
          </h1>
          <p className="text-gray-600 text-lg">
            实时姿态识别，科学健身指导
          </p>
        </div>

        <div className="space-y-6">
          {/* 第一行：摄像头和统计面板 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* 左侧：摄像头视图 */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl p-6 shadow-md border border-blue-100">
                <CameraView
                  videoRef={videoRef}
                  canvasRef={canvasRef}
                  isActive={isActive}
                  exerciseStats={exerciseStats}
                  startDetection={handleStartDetection}
                  stopDetection={handleStopDetection}
                  resetStats={resetStats}
                />
              </div>
            </div>

            {/* 右侧：统计面板 */}
            <div>
              <div className="bg-white rounded-xl p-6 shadow-md border border-blue-100">
                <StatsPanel
                  exerciseStats={exerciseStats}
                  currentExercise={getExerciseName(selectedExercise)}
                  duration={duration}
                />
              </div>
            </div>
          </div>

          {/* 第二行：选择运动和快速操作对齐 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* 左侧：运动选择器 */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl p-6 shadow-md border border-blue-100">
                <ExerciseSelector
                  selectedExercise={selectedExercise}
                  onExerciseSelect={setSelectedExercise}
                />
              </div>
            </div>

            {/* 右侧：快速操作和今日目标 */}
            <div className="space-y-6">
            {/* 快速操作面板 */}
            <div className="bg-white rounded-xl p-6 shadow-md border border-blue-100">
              <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <div className="w-1 h-6 bg-blue-600 rounded-full"></div>
                快速操作
              </h3>
              <div className="space-y-3">
                <button 
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md"
                  onClick={() => setDuration(0)}
                >
                  重置计时器
                </button>
                <button 
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md"
                  onClick={() => navigate('/profile?tab=history')}
                >
                  查看历史记录
                </button>
                <button 
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md"
                  onClick={() => navigate('/profile?tab=plan')}
                >
                  健身计划定制
                </button>
              </div>
            </div>

            {/* 今日目标 */}
            <div className="bg-white rounded-xl p-6 shadow-md border border-blue-100">
              <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <div className="w-1 h-6 bg-blue-600 rounded-full"></div>
                今日目标
              </h3>
              <div className="space-y-5">
                {/* 当前选择的运动目标 */}
                {(() => {
                  const exerciseName = getExerciseName(selectedExercise);
                  const isPlank = selectedExercise === 'plank';
                  
                  // 平板支撑显示时长（秒），其他显示次数
                  let currentValue = 0;
                  let targetValue = 0;
                  
                  if (isPlank) {
                    // 平板支撑：显示时长（秒）
                    currentValue = duration; // 当前运动时长（秒）
                    if (userPlan?.daily_goals?.plank) {
                      targetValue = userPlan.daily_goals.plank; // 目标秒数
                    } else {
                      targetValue = 60; // 默认60秒
                    }
                  } else {
                    // 其他运动：显示次数
                    currentValue = exerciseStats.count;
                    if (userPlan?.daily_goals) {
                      switch (selectedExercise) {
                        case 'squat':
                          targetValue = userPlan.daily_goals.squat || 20;
                          break;
                        case 'pushup':
                          targetValue = userPlan.daily_goals.pushup || 15;
                          break;
                        case 'jumping_jack':
                          targetValue = userPlan.daily_goals.jumping_jack || 30;
                          break;
                        default:
                          targetValue = 20;
                      }
                    } else {
                      targetValue = 20; // 默认值
                    }
                  }
                  
                  const progress = targetValue > 0 ? Math.min((currentValue / targetValue) * 100, 100) : 0;
                  const unit = isPlank ? '秒' : '次';
                  
                  // 格式化显示：平板支撑显示为"分:秒"格式
                  const formatValue = (val: number, isTime: boolean) => {
                    if (isTime) {
                      const mins = Math.floor(val / 60);
                      const secs = val % 60;
                      return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`;
                    }
                    return val;
                  };
                  
                  const formatTarget = (val: number, isTime: boolean) => {
                    if (isTime) {
                      const mins = Math.floor(val / 60);
                      const secs = val % 60;
                      return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`;
                    }
                    return val;
                  };
                  
                  return (
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-gray-600 font-medium">{exerciseName}</span>
                        <span className="text-gray-900 font-semibold">
                          {isPlank ? formatValue(currentValue, true) : currentValue}/{isPlank ? formatTarget(targetValue, true) : targetValue} {unit}
                        </span>
                      </div>
                      <div className="w-full bg-blue-100 rounded-full h-3 overflow-hidden">
                        <div 
                          className="bg-blue-600 h-3 rounded-full transition-all duration-500" 
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
            </div>
          </div>
        </div>
      </main>

      {/* 底部信息 */}
      <footer className="bg-white border-t border-blue-100 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-gray-600 text-sm">
            <p className="flex items-center justify-center gap-2">
              <span>FitnessAI - 让科技赋能健康生活</span>
              <span className="text-gray-400">|</span>
              <span>基于MediaPipe姿态识别技术</span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Home;

