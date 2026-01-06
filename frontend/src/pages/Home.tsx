import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import CameraView from '../components/CameraView';
import StatsPanel from '../components/StatsPanel';
import ExerciseSelector from '../components/ExerciseSelector';
import SessionSummaryModal from '../components/SessionSummaryModal';
import { usePoseDetection } from '../hooks/usePoseDetection';
import { Activity, User, LogOut, Calendar, Target, Trophy } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';

function Home() {
  const [selectedExercise, setSelectedExercise] = useState('squat');
  const [duration, setDuration] = useState(0);
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [sessionSummary, setSessionSummary] = useState<any>(null);
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const previousCountRef = useRef(0);
  
  // 打卡相关
  const [checkinStreak, setCheckinStreak] = useState(0);
  const [dailyChallenge, setDailyChallenge] = useState<any>(null);
  const [challengeCompleted, setChallengeCompleted] = useState(false);
  
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
  
  const [isFinishing, setIsFinishing] = useState(false);
  const {
    videoRef,
    canvasRef,
    isActive,
    exerciseStats,
    startDetection,
    stopDetection,
    resetStats
  } = usePoseDetection(selectedExercise);

  // 每日统计数据
  const [dailyStats, setDailyStats] = useState<{
    squat: number;
    pushup: number;
    jumping_jack: number;
    plank: number;
  }>({ squat: 0, pushup: 0, jumping_jack: 0, plank: 0 });

  // 加载每日统计
  const loadDailyStats = async () => {
    if (!user || !token) return;
    try {
      const stats = await api.get('/api/user/daily_stats', token);
      setDailyStats(stats);
    } catch (err) {
      console.error('加载每日统计失败:', err);
    }
  };

  useEffect(() => {
    loadDailyStats();
  }, [user, token, sessionId]); // 每次会话结束（sessionId变为null）或初始化时刷新

  // 包装 startDetection 以添加会话创建
  const handleStartDetection = async () => {
    await startDetection();
    setIsTimerActive(true); // 恢复/开始计时
    
    // 如果没有会话ID，则创建新的运动会话
    if (!sessionId && user && token) {
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

  // 包装 stopDetection 为暂停功能
  const handlePauseDetection = () => {
     // 仅停止摄像头检测和计时器，不结束会话
     stopDetection();
     setIsTimerActive(false); 
  };
  
  // 新增：结束本次运动
  const handleEndSession = async () => {
    if (isFinishing) return;
    
    // 停止检测和计时
    stopDetection();
    setIsTimerActive(false);
    setIsFinishing(true);
    
    // 结束运动会话
    if (sessionId && token) {
      try {
        // 计算前端的准确率
        const accuracy = exerciseStats.totalCount && exerciseStats.totalCount > 0 
           ? Math.round((exerciseStats.correctCount || 0) / exerciseStats.totalCount * 100) 
           : 0;

        const response = await api.post(
          `/api/session/${sessionId}/end`,
          {
            duration: duration, // 发送前端计算的实际运动时长(秒)
            stats: {            // 发送前端统计的准确数据
                total_count: exerciseStats.count,         
                accuracy: accuracy
            }
          },
          token
        );
        
        if (response.summary) {
          setSessionSummary(response.summary);
          setShowSummaryModal(true);
        }

        setSessionId(null);
        setDuration(0); // 重置计时器
        
        // 自动打卡
        try {
          await api.post('/api/checkin', {}, token);
          const checkin = await api.get('/api/user/checkin/streak', token);
          setCheckinStreak(checkin.current_streak || 0);
        } catch (err) {
          console.error('自动打卡失败:', err);
        }
        
        // 检查成就
        try {
          await api.post('/api/user/achievements/check', {}, token);
        } catch (err) {
          console.error('检查成就失败:', err);
        }
      } catch (err) {
        console.error('结束运动会话失败:', err);
        alert('生成报告失败，请检查网络连接');
      } finally {
        setIsFinishing(false);
      }
    } else {
        setIsFinishing(false);
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
    // 移除这个副作用，因为我们现在手动控制计时器状态
    // setIsTimerActive(isActive); 
  }, [isActive]);

  // 加载用户健身计划
  useEffect(() => {
    const loadUserPlan = async () => {
      if (!user || !token) return;
      
      try {
        const plan = await api.get('/api/user/plan', token);
        setUserPlan(plan);
      } catch (err: any) {
        // 401错误会被api.ts自动处理（重定向到登录页）
        if (err.message && !err.message.includes('无效或过期的token')) {
          console.error('加载健身计划失败:', err);
        }
      }
    };

    loadUserPlan();
  }, [user, token]);

  // 加载打卡数据
  useEffect(() => {
    const loadCheckin = async () => {
      if (!user || !token) return;
      
      try {
        const checkin = await api.get('/api/user/checkin/streak', token);
        setCheckinStreak(checkin.current_streak || 0);
      } catch (err: any) {
        if (err.message && !err.message.includes('无效或过期的token')) {
          console.error('加载打卡数据失败:', err);
        }
      }
    };

    loadCheckin();
  }, [user, token]);

  // 加载每日挑战
  useEffect(() => {
    const loadChallenge = async () => {
      if (!user || !token) return;
      
      try {
        const challenge = await api.get('/api/challenges/daily', token);
        setDailyChallenge(challenge);
      } catch (err: any) {
        if (err.message && !err.message.includes('无效或过期的token')) {
          console.error('加载每日挑战失败:', err);
        }
      }
    };

    loadChallenge();
  }, [user, token]);

  // 打卡功能
  const handleCheckin = async () => {
    if (!token) return;
    
    try {
      await api.post('/api/checkin', {}, token);
      const checkin = await api.get('/api/user/checkin/streak', token);
      setCheckinStreak(checkin.current_streak || 0);
      // 检查成就
      await api.post('/api/user/achievements/check', {}, token);
    } catch (err) {
      console.error('打卡失败:', err);
    }
  };

  // 完成挑战
  const handleCompleteChallenge = async () => {
    if (!token || !dailyChallenge || challengeCompleted) return;
    
    try {
      const response = await api.post(`/api/challenges/${dailyChallenge.id}/complete`, {}, token);
      if (response.completed) {
        setChallengeCompleted(true);
        // 检查成就
        const achievementsResponse = await api.post('/api/user/achievements/check', {}, token);
        if (achievementsResponse.new_achievements && achievementsResponse.new_achievements.length > 0) {
          // 显示成就解锁提示
          const achievementNames = achievementsResponse.new_achievements.map((a: any) => `${a.icon} ${a.name}`).join('、');
          alert(`🎉 恭喜！您解锁了新的成就：${achievementNames}`);
        }
      }
    } catch (err: any) {
      if (err.message && err.message.includes('挑战未完成')) {
        // 显示友好的错误提示
        const errorData = err.response?.data || {};
        alert(errorData.message || '您还没有完成挑战目标，请继续努力！');
      } else {
        console.error('完成挑战失败:', err);
        alert('完成挑战失败，请稍后重试');
      }
    }
  };

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
                  stopDetection={handlePauseDetection}
                  endSession={handleEndSession}
                  resetStats={resetStats}
                  isLoading={isFinishing}
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
                <button 
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md"
                  onClick={() => navigate('/profile?tab=leaderboard')}
                >
                  查看排行榜
                </button>
                <button 
                  className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center gap-2"
                  onClick={handleCheckin}
                >
                  <Calendar className="h-5 w-5" />
                  打卡 ({checkinStreak}天)
                </button>
              </div>
            </div>

            {/* 每日挑战 */}
            {dailyChallenge && (
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-6 shadow-md border border-purple-200">
                <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Target className="h-6 w-6 text-purple-600" />
                  每日挑战
                </h3>
                <div className="space-y-3">
                  <div>
                    <h4 className="font-semibold text-gray-900">{dailyChallenge.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{dailyChallenge.description}</p>
                  </div>
                  {dailyChallenge.type === 'count' && (
                    <div className="text-sm text-gray-700">
                      目标: {dailyChallenge.target} 次 {getExerciseName(dailyChallenge.exercise)}
                    </div>
                  )}
                  {dailyChallenge.type === 'duration' && (
                    <div className="text-sm text-gray-700">
                      目标: {dailyChallenge.target} 秒 {getExerciseName(dailyChallenge.exercise)}
                    </div>
                  )}
                  {dailyChallenge.type === 'combo' && dailyChallenge.targets && (
                    <div className="text-sm text-gray-700 space-y-1">
                      {Object.entries(dailyChallenge.targets).map(([ex, target]) => (
                        <div key={ex}>{getExerciseName(ex)}: {target as number} 次</div>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-sm text-purple-600">
                    <Trophy className="h-4 w-4" />
                    完成挑战可获得成就奖励 🏆
                  </div>
                  <button
                    onClick={handleCompleteChallenge}
                    disabled={challengeCompleted}
                    className={`w-full font-semibold py-2 px-4 rounded-lg transition-all duration-200 ${
                      challengeCompleted
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        : 'bg-purple-600 hover:bg-purple-700 text-white shadow-sm hover:shadow-md'
                    }`}
                  >
                    {challengeCompleted ? '✓ 已完成' : '完成挑战'}
                  </button>
                </div>
              </div>
            )}

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
                    // 历史累计 + 当前会话时长
                    currentValue = (dailyStats?.plank || 0) + duration;
                    if (userPlan?.daily_goals?.plank) {
                      targetValue = userPlan.daily_goals.plank; // 目标秒数
                    } else {
                      targetValue = 60; // 默认60秒
                    }
                  } else {
                    // 其他运动：显示次数
                    // 历史累计 + 当前会话次数
                    const dailyCount = dailyStats?.[selectedExercise as keyof typeof dailyStats] || 0;
                    currentValue = dailyCount + exerciseStats.count;
                    
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
        <SessionSummaryModal
          isOpen={showSummaryModal}
          onClose={() => setShowSummaryModal(false)}
          summary={sessionSummary}
        />
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

