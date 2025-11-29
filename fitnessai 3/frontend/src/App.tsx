import React, { useState, useEffect } from 'react';
import CameraView from './components/CameraView';
import StatsPanel from './components/StatsPanel';
import ExerciseSelector from './components/ExerciseSelector';
import { usePoseDetection } from './hooks/usePoseDetection';
import { Activity, Users, Settings, Wifi, WifiOff, User, Edit3, Save, X, Volume2, VolumeX, Monitor, Smartphone } from 'lucide-react';
import './App.css';

function App() {
  const [duration, setDuration] = useState(0);
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showPlan, setShowPlan] = useState(false);
  const [isCountingDown, setIsCountingDown] = useState(false);
  const [countdown, setCountdown] = useState(3);
  const [historyRecords, setHistoryRecords] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [plan, setPlan] = useState<any>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);

  // 新增状态：个人资料弹窗
  const [showProfile, setShowProfile] = useState(false);
  const [userProfile, setUserProfile] = useState({
    name: localStorage.getItem('user_name') || '健身达人',
    age: localStorage.getItem('user_age') || '25',
    height: localStorage.getItem('user_height') || '170',
    weight: localStorage.getItem('user_weight') || '65',
    goal: localStorage.getItem('user_goal') || '减脂',
    avatar: localStorage.getItem('user_avatar') || '🏋️'
  });
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [tempProfile, setTempProfile] = useState(userProfile);

  // 新增状态：设置弹窗
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    soundEnabled: localStorage.getItem('sound_enabled') !== 'false',
    voiceEnabled: localStorage.getItem('voice_enabled') !== 'false',
    language: localStorage.getItem('language') || 'zh-CN',
    theme: localStorage.getItem('theme') || 'dark',
    difficulty: localStorage.getItem('difficulty') || 'medium',
    autoStart: localStorage.getItem('auto_start') === 'true',
    notifications: localStorage.getItem('notifications') !== 'false'
  });

  // 用户ID管理
  const [userId] = useState(() => {
    let uid = localStorage.getItem('user_id');
    if (!uid) {
      uid = `web_user_${Date.now()}`;
      localStorage.setItem('user_id', uid);
    }
    return uid;
  });

  // 只在App顶层调用一次
  const poseDetection = usePoseDetection();
  const {
    exerciseStats,
    isActive,
    isInitialized,
    initError,
    currentExercise,
    startDetection: originalStartDetection,
    stopDetection: originalStopDetection,
    resetStats,
    switchExercise
  } = poseDetection;

  // 包装startDetection函数以添加倒计时
  const startDetection = async () => {
    if (!isInitialized) {
      return;
    }
    
    // 开始倒计时
    setIsCountingDown(true);
    setCountdown(3);
    
    // 倒计时逻辑
    for (let i = 3; i > 0; i--) {
      setCountdown(i);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    // 倒计时结束，开始正式检测
    setIsCountingDown(false);
    await originalStartDetection();
  };

  // 包装stopDetection函数以保存历史记录
  const stopDetection = async () => {
    // 如果正在倒计时，取消倒计时
    if (isCountingDown) {
      setIsCountingDown(false);
      setCountdown(3);
      return;
    }
    
    // 只有在真正进行过运动时才保存记录（次数大于0或时间大于10秒）
    if (exerciseStats.count > 0 || duration > 10) {
      const record = {
        exercise_type: currentExercise,
        duration: duration,
        count: exerciseStats.count,
        score: exerciseStats.score,
        accuracy: exerciseStats.accuracy
      };
      
      const savedRecord = saveHistoryRecord(record);
      if (savedRecord) {
        // 历史记录已保存
      }
    }
    
    // 调用原始的停止检测函数
    await originalStopDetection();
    
    // 重置计时器
    setDuration(0);
    setIsTimerActive(false);
  };

  // 处理个人资料保存
  const handleSaveProfile = () => {
    setUserProfile(tempProfile);
    // 保存到localStorage
    localStorage.setItem('user_name', tempProfile.name);
    localStorage.setItem('user_age', tempProfile.age);
    localStorage.setItem('user_height', tempProfile.height);
    localStorage.setItem('user_weight', tempProfile.weight);
    localStorage.setItem('user_goal', tempProfile.goal);
    localStorage.setItem('user_avatar', tempProfile.avatar);
    setIsEditingProfile(false);
  };

  // 处理设置保存
  const handleSaveSettings = (newSettings: typeof settings) => {
    const oldDifficulty = settings.difficulty;
    setSettings(newSettings);
    // 保存到localStorage
    Object.entries(newSettings).forEach(([key, value]) => {
      localStorage.setItem(key.replace(/([A-Z])/g, '_$1').toLowerCase(), String(value));
    });

    // 如果难度级别改变且健身计划弹窗正在显示，则重新生成计划
    if (newSettings.difficulty !== oldDifficulty && showPlan) {
      setPlanLoading(true);
      setTimeout(() => {
        const generatedPlan = generatePlanByDifficulty(newSettings.difficulty);
        setPlan(generatedPlan);
        setPlanLoading(false);
      }, 300);
    }
  };

  // 获取用户统计数据
  const getUserStats = () => {
    const allRecords = loadHistoryRecords();
    const totalSessions = allRecords.length;
    const totalTime = allRecords.reduce((sum: number, record: any) => sum + (record.duration || 0), 0);
    const avgAccuracy = allRecords.length > 0 
      ? allRecords.reduce((sum: number, record: any) => sum + (record.accuracy || 0), 0) / allRecords.length 
      : 0;
    
    // 简化连续训练天数计算
    const today = new Date().toLocaleDateString('zh-CN');
    const todayRecords = allRecords.filter((record: any) => record.date === today);
    const streak = todayRecords.length > 0 ? Math.max(1, Math.floor(allRecords.length / 3)) : 0;
    
    return {
      totalSessions,
      totalTime: Math.floor(totalTime / 60), // 转换为分钟
      avgAccuracy: Math.round(avgAccuracy * 100),
      streak
    };
  };

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

  useEffect(() => {
    setIsTimerActive(isActive);
  }, [isActive]);

  // 从localStorage获取历史记录
  const loadHistoryRecords = () => {
    try {
      const stored = localStorage.getItem('fitness_history');
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('读取历史记录失败:', error);
      return [];
    }
  };

  // 保存历史记录到localStorage
  const saveHistoryRecord = (record: any) => {
    try {
      const existing = loadHistoryRecords();
      const newRecord = {
        id: Date.now().toString(),
        date: new Date().toLocaleDateString('zh-CN'),
        time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        exercise_type: getExerciseName(record.exercise_type),
        duration: record.duration,
        count: record.count,
        score: record.score,
        accuracy: record.accuracy || 0,
        user_id: userId
      };
      
      const updated = [newRecord, ...existing].slice(0, 50); // 只保留最近50条记录
      localStorage.setItem('fitness_history', JSON.stringify(updated));
      return newRecord;
    } catch (error) {
      console.error('保存历史记录失败:', error);
      return null;
    }
  };

  // 拉取历史记录
  useEffect(() => {
    if (showHistory) {
      setHistoryLoading(true);
      setHistoryError(null);
      
      // 模拟加载延迟
      setTimeout(() => {
        try {
          const records = loadHistoryRecords();
          setHistoryRecords(records);
          setHistoryLoading(false);
        } catch (error) {
          setHistoryError('获取历史记录失败');
          setHistoryLoading(false);
        }
      }, 300);
    }
  }, [showHistory, userId]);

  // 根据难度级别生成健身计划
  const generatePlanByDifficulty = (difficulty: string) => {
    // 根据用户资料调整计划
    const userAge = parseInt(userProfile.age);
    const userGoal = userProfile.goal;
    
    const plans = {
      easy: {
        title: '初级健身计划',
        description: '适合初学者的轻松健身计划，重点培养运动习惯',
        squat: userAge > 50 ? '2组 × 6-8次' : '2组 × 8-10次',
        pushup: userAge > 50 ? '2组 × 3-5次（墙式俯卧撑）' : '2组 × 5-8次（可膝盖着地）',
        plank: userAge > 50 ? '2组 × 10-15秒' : '2组 × 15-20秒',
        jumping_jack: userAge > 50 ? '2组 × 8-12次' : '2组 × 10-15次',
        rest_time: userAge > 50 ? 90 : 60,
        total_time: '15-20分钟',
        calories: '80-120卡路里',
        tips: [
          '动作幅度可以较小，重点是动作标准',
          '感到疲劳时及时休息',
          '每周训练3-4次即可',
          userGoal === '减脂' ? '配合有氧运动效果更佳' : '循序渐进增加强度'
        ]
      },
      medium: {
        title: '中级健身计划',
        description: '适合有一定基础的健身爱好者，平衡力量与耐力',
        squat: userGoal === '增肌' ? '3组 × 15-18次' : '3组 × 12-15次',
        pushup: userGoal === '增肌' ? '3组 × 10-15次' : '3组 × 8-12次',
        plank: userGoal === '塑形' ? '3组 × 45-60秒' : '3组 × 30-45秒',
        jumping_jack: userGoal === '减脂' ? '3组 × 25-30次' : '3组 × 20-25次',
        rest_time: userGoal === '力量' ? 60 : 45,
        total_time: '25-35分钟',
        calories: '150-220卡路里',
        tips: [
          '保持动作节奏稳定，控制动作质量',
          '注意呼吸配合，避免憋气',
          '组间休息不宜过长',
          userGoal === '减脂' ? '可适当增加有氧强度' : userGoal === '增肌' ? '注重力量输出' : '保持训练一致性'
        ]
      },
      hard: {
        title: '高级健身计划',
        description: '适合有经验的健身达人，挑战身体极限',
        squat: userGoal === '力量' ? '4组 × 20-25次' : '4组 × 18-20次',
        pushup: userGoal === '力量' ? '4组 × 18-25次' : '4组 × 15-20次',
        plank: '4组 × 60-90秒',
        jumping_jack: userGoal === '减脂' ? '4组 × 40-50次' : '4组 × 30-40次',
        rest_time: userGoal === '减脂' ? 20 : 30,
        total_time: '40-50分钟',
        calories: '250-350卡路里',
        tips: [
          '追求动作的完美执行，而非数量',
          '严格控制休息时间，保持高强度',
          '可尝试变式动作增加难度',
          userGoal === '减脂' ? '高强度间歇训练模式' : userGoal === '力量' ? '注重爆发力输出' : '全面发展身体素质',
          '训练后充分拉伸放松'
        ]
      }
    };
    return plans[difficulty as keyof typeof plans] || plans.medium;
  };

  // 拉取健身计划
  useEffect(() => {
    if (showPlan) {
      setPlanLoading(true);
      setPlanError(null);
      
      // 模拟加载时间，然后根据难度级别生成计划
      setTimeout(() => {
        try {
          const generatedPlan = generatePlanByDifficulty(settings.difficulty);
          setPlan(generatedPlan);
          setPlanLoading(false);
        } catch (err) {
          setPlanError('生成健身计划失败');
          setPlanLoading(false);
        }
      }, 500); // 500ms 模拟加载时间
    }
  }, [showPlan, userId, settings.difficulty]);

  const getExerciseName = (id: string) => {
    const exerciseNames: { [key: string]: string } = {
      'squat': '深蹲',
      'pushup': '俯卧撑',
      'plank': '平板支撑',
      'jumping_jack': '开合跳'
    };
    return exerciseNames[id] || '未知运动';
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
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
              <span className="ml-2 text-sm text-gray-300">智能健身助手</span>
            </div>
            <div className="flex items-center space-x-4">
              {/* AI状态指示器 */}
              <div className="flex items-center space-x-2 text-sm">
                {initError ? (
                  <div className="flex items-center text-red-400">
                    <WifiOff size={16} className="mr-1" />
                    <span>AI未连接</span>
                  </div>
                ) : !isInitialized ? (
                  <div className="flex items-center text-yellow-400">
                    <Wifi size={16} className="mr-1 animate-pulse" />
                    <span>AI初始化中</span>
                  </div>
                ) : (
                  <div className="flex items-center text-green-400">
                    <Wifi size={16} className="mr-1" />
                    <span>AI已就绪</span>
                  </div>
                )}
              </div>
              
              <div className="text-sm text-gray-300">
                当前运动: <span className="text-blue-400 font-medium">{getExerciseName(currentExercise)}</span>
              </div>
              <button 
                className="text-gray-300 hover:text-white transition-colors" 
                onClick={() => setShowProfile(true)}
                title="个人资料"
              >
                <Users size={20} />
              </button>
              <button 
                className="text-gray-300 hover:text-white transition-colors" 
                onClick={() => setShowSettings(true)}
                title="设置"
              >
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
              <p className="text-gray-300 mb-4">
                基于MediaPipe的实时姿态识别，科学健身指导
              </p>
              
              {/* 状态指示器 */}
              <div className="flex justify-center space-x-4">
                {initError ? (
                  <div className="inline-flex items-center px-3 py-1 rounded-full bg-red-500 bg-opacity-20 border border-red-400">
                    <div className="w-2 h-2 bg-red-400 rounded-full mr-2"></div>
                    <span className="text-red-300 text-sm">AI初始化失败</span>
                  </div>
                ) : !isInitialized ? (
                  <div className="inline-flex items-center px-3 py-1 rounded-full bg-yellow-500 bg-opacity-20 border border-yellow-400">
                    <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse mr-2"></div>
                    <span className="text-yellow-300 text-sm">AI初始化中...</span>
                  </div>
                ) : isActive ? (
                  <div className="inline-flex items-center px-3 py-1 rounded-full bg-green-500 bg-opacity-20 border border-green-400">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></div>
                    <span className="text-green-300 text-sm">AI实时分析中...</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-500 bg-opacity-20 border border-blue-400">
                    <div className="w-2 h-2 bg-blue-400 rounded-full mr-2"></div>
                    <span className="text-blue-300 text-sm">AI已就绪</span>
                  </div>
                )}
                
                {/* 计时器显示 */}
                {isActive && (
                  <div className="inline-flex items-center px-3 py-1 rounded-full bg-purple-500 bg-opacity-20 border border-purple-400">
                    <span className="text-purple-300 text-sm">运动时长: {formatTime(duration)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* 摄像头视图 */}
            <CameraView
              {...poseDetection}
              isCountingDown={isCountingDown}
              countdown={countdown}
              startDetection={startDetection}
              stopDetection={stopDetection}
            />

            {/* 运动选择器 */}
            <ExerciseSelector
              currentExercise={currentExercise}
              switchExercise={switchExercise}
              isActive={isActive}
            />
          </div>

          {/* 右侧：统计面板 */}
          <div className="space-y-6">
            <StatsPanel
              exerciseStats={exerciseStats}
              currentExercise={getExerciseName(currentExercise)}
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
                <button className="w-full bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white font-medium py-2 px-4 rounded-lg transition-all" onClick={() => setShowHistory(true)}>
                  查看历史记录
                </button>
                <button className="w-full bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white font-medium py-2 px-4 rounded-lg transition-all" onClick={() => setShowPlan(true)}>
                  健身计划定制
                </button>
              </div>
            </div>

            {/* 历史记录弹窗 */}
            {showHistory && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[80vh] overflow-y-auto">
                  <h2 className="text-xl font-bold mb-4">历史记录</h2>
                  {historyLoading ? (
                    <div className="text-gray-500">加载中...</div>
                  ) : historyError ? (
                    <div className="text-red-500">{historyError}</div>
                  ) : historyRecords.length === 0 ? (
                    <div className="text-gray-700 mb-4">暂无历史记录</div>
                  ) : (
                    <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
                      {historyRecords.map((rec, idx) => (
                        <div key={rec.id || idx} className="bg-gray-50 p-3 rounded-lg">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <div className="font-medium text-gray-900">{rec.exercise_type}</div>
                              <div className="text-xs text-gray-500">{rec.date} {rec.time}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-medium text-blue-600">
                                {typeof rec.duration === 'number'
                                  ? (() => {
                                      const min = Math.floor(rec.duration / 60);
                                      const s = rec.duration % 60;
                                      return `${min}分${s}秒`;
                                    })()
                                  : '-'}
                              </div>
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-xs">
                            <div className="text-center">
                              <div className="font-medium text-green-600">{rec.count || 0}</div>
                              <div className="text-gray-500">次数</div>
                            </div>
                            <div className="text-center">
                              <div className="font-medium text-purple-600">{rec.score || 0}</div>
                              <div className="text-gray-500">分数</div>
                            </div>
                            <div className="text-center">
                              <div className="font-medium text-orange-600">
                                {rec.accuracy ? `${(rec.accuracy * 100).toFixed(1)}%` : '0%'}
                              </div>
                              <div className="text-gray-500">准确率</div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                                      )}
                    
                    {/* 统计信息 */}
                    {historyRecords.length > 0 && (
                      <div className="bg-blue-50 p-3 rounded-lg mb-4">
                        <div className="text-sm text-blue-700">
                          <div><strong>📊 训练统计:</strong></div>
                          <div>• 总训练次数: {historyRecords.length} 次</div>
                          <div>• 累计时长: {Math.floor(historyRecords.reduce((sum, record) => sum + (record.duration || 0), 0) / 60)} 分钟</div>
                          <div>• 平均准确率: {historyRecords.length > 0 ? ((historyRecords.reduce((sum, record) => sum + (record.accuracy || 0), 0) / historyRecords.length) * 100).toFixed(1) : 0}%</div>
                        </div>
                      </div>
                    )}
                    
                    <div className="flex space-x-2">
                      {historyRecords.length > 0 && (
                        <button 
                          className="flex-1 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                          onClick={() => {
                            if (window.confirm('确定要清空所有历史记录吗？此操作不可恢复。')) {
                              localStorage.removeItem('fitness_history');
                              setHistoryRecords([]);
                            }
                          }}
                        >
                          清空记录
                        </button>
                      )}
                      <button 
                        className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600" 
                        onClick={() => setShowHistory(false)}
                      >
                        关闭
                      </button>
                    </div>
                </div>
              </div>
            )}

            {/* 健身计划定制弹窗 */}
            {showPlan && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                <div className="bg-white rounded-lg p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">健身计划定制</h2>
                    <button 
                      onClick={() => setShowPlan(false)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <X size={20} />
                    </button>
                  </div>
                  
                  {planLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="text-gray-500">生成个性化计划中...</div>
                    </div>
                  ) : planError ? (
                    <div className="text-red-500 text-center py-8">{planError}</div>
                  ) : plan ? (
                    <div className="space-y-6">
                      {/* 计划标题和描述 */}
                      <div className="text-center">
                        <h3 className="text-lg font-semibold text-blue-600 mb-2">{plan.title}</h3>
                        <p className="text-sm text-gray-600 mb-4">{plan.description}</p>
                        
                                               {/* 难度级别选择 */}
                         <div className="space-y-2">
                           <div className="text-sm text-gray-600">选择难度级别:</div>
                           <div className="flex justify-center space-x-2">
                             {['easy', 'medium', 'hard'].map((difficulty) => (
                               <button
                                 key={difficulty}
                                 onClick={() => {
                                   const newSettings = {...settings, difficulty};
                                   handleSaveSettings(newSettings);
                                 }}
                                 className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                                   settings.difficulty === difficulty 
                                     ? 'bg-blue-500 text-white' 
                                     : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                 }`}
                               >
                                 {difficulty === 'easy' ? '简单' : difficulty === 'medium' ? '中等' : '困难'}
                               </button>
                             ))}
                           </div>
                         </div>
                      </div>

                      {/* 计划概览 */}
                      <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                        <div className="text-center">
                          <div className="text-lg font-bold text-green-600">{plan.total_time}</div>
                          <div className="text-xs text-gray-600">预计时长</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-bold text-orange-600">{plan.calories}</div>
                          <div className="text-xs text-gray-600">预计消耗</div>
                        </div>
                      </div>

                      {/* 训练项目 */}
                      <div>
                        <h4 className="font-semibold mb-3">训练项目</h4>
                        <div className="space-y-3">
                          <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                            <div className="flex items-center">
                              <span className="text-2xl mr-3">🏋️</span>
                              <span className="font-medium">深蹲</span>
                            </div>
                            <span className="text-blue-600 font-semibold">{plan.squat}</span>
                          </div>
                          
                          <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                            <div className="flex items-center">
                              <span className="text-2xl mr-3">💪</span>
                              <span className="font-medium">俯卧撑</span>
                            </div>
                            <span className="text-green-600 font-semibold">{plan.pushup}</span>
                          </div>
                          
                          <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                            <div className="flex items-center">
                              <span className="text-2xl mr-3">⏱️</span>
                              <span className="font-medium">平板支撑</span>
                            </div>
                            <span className="text-purple-600 font-semibold">{plan.plank}</span>
                          </div>
                          
                          <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                            <div className="flex items-center">
                              <span className="text-2xl mr-3">🤸</span>
                              <span className="font-medium">开合跳</span>
                            </div>
                            <span className="text-red-600 font-semibold">{plan.jumping_jack}</span>
                          </div>
                        </div>
                      </div>

                      {/* 训练建议 */}
                      <div>
                        <h4 className="font-semibold mb-3">训练建议</h4>
                        <div className="bg-yellow-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-700 space-y-1">
                            <div><strong>组间休息:</strong> {plan.rest_time}秒</div>
                            {plan.tips && plan.tips.map((tip: string, index: number) => (
                              <div key={index} className="flex items-start">
                                <span className="text-yellow-500 mr-2 mt-0.5">•</span>
                                <span>{tip}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                                             {/* 个性化提示 */}
                       <div className="bg-blue-50 p-4 rounded-lg">
                         <div className="text-sm text-blue-700 space-y-1">
                           <div><strong>🎯 个性化定制:</strong></div>
                           <div>• 根据您的年龄 ({userProfile.age}岁) 和健身目标 ({userProfile.goal}) 调整</div>
                           <div>• 可通过上方按钮快速切换难度级别</div>
                           <div>• 在个人资料中修改信息可获得更精准的计划</div>
                         </div>
                       </div>

                      <div className="flex space-x-2">
                        <button 
                          onClick={() => setShowSettings(true)}
                          className="flex-1 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                        >
                          调整难度
                        </button>
                        <button 
                          onClick={() => setShowPlan(false)}
                          className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                          开始训练
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-700 text-center py-8">暂无推荐计划</div>
                  )}
                </div>
              </div>
            )}

            {/* 个人资料弹窗 */}
            {showProfile && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[80vh] overflow-y-auto">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">个人资料</h2>
                    <button 
                      onClick={() => {
                        setShowProfile(false);
                        setIsEditingProfile(false);
                        setTempProfile(userProfile);
                      }}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <X size={20} />
                    </button>
                  </div>
                  
                  {!isEditingProfile ? (
                    <div className="space-y-4">
                      {/* 头像和基本信息 */}
                      <div className="text-center">
                        <div className="text-6xl mb-2">{userProfile.avatar}</div>
                        <h3 className="text-lg font-semibold">{userProfile.name}</h3>
                      </div>
                      
                      {/* 用户信息 */}
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">年龄:</span>
                          <span>{userProfile.age} 岁</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">身高:</span>
                          <span>{userProfile.height} cm</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">体重:</span>
                          <span>{userProfile.weight} kg</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">健身目标:</span>
                          <span>{userProfile.goal}</span>
                        </div>
                      </div>

                      {/* 用户统计 */}
                      <div className="border-t pt-4">
                        <h4 className="font-semibold mb-2">运动统计</h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="text-center">
                            <div className="text-2xl font-bold text-blue-500">{getUserStats().totalSessions}</div>
                            <div className="text-xs text-gray-600">训练次数</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-green-500">{getUserStats().totalTime}</div>
                            <div className="text-xs text-gray-600">总时长(分钟)</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-purple-500">{getUserStats().avgAccuracy}%</div>
                            <div className="text-xs text-gray-600">平均准确率</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-orange-500">{getUserStats().streak}</div>
                            <div className="text-xs text-gray-600">连续天数</div>
                          </div>
                        </div>
                      </div>

                      <button 
                        onClick={() => {
                          setIsEditingProfile(true);
                          setTempProfile(userProfile);
                        }}
                        className="w-full mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center justify-center"
                      >
                        <Edit3 size={16} className="mr-2" />
                        编辑资料
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* 编辑表单 */}
                      <div className="space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">头像</label>
                          <div className="flex space-x-2">
                            {['🏋️', '💪', '🤸', '🏃', '⚡', '🔥'].map(emoji => (
                              <button
                                key={emoji}
                                onClick={() => setTempProfile({...tempProfile, avatar: emoji})}
                                className={`text-2xl p-2 rounded ${tempProfile.avatar === emoji ? 'bg-blue-100' : 'hover:bg-gray-100'}`}
                              >
                                {emoji}
                              </button>
                            ))}
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">姓名</label>
                          <input
                            type="text"
                            value={tempProfile.name}
                            onChange={(e) => setTempProfile({...tempProfile, name: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">年龄</label>
                            <input
                              type="number"
                              value={tempProfile.age}
                              onChange={(e) => setTempProfile({...tempProfile, age: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">身高(cm)</label>
                            <input
                              type="number"
                              value={tempProfile.height}
                              onChange={(e) => setTempProfile({...tempProfile, height: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">体重(kg)</label>
                          <input
                            type="number"
                            value={tempProfile.weight}
                            onChange={(e) => setTempProfile({...tempProfile, weight: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">健身目标</label>
                          <select
                            value={tempProfile.goal}
                            onChange={(e) => setTempProfile({...tempProfile, goal: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          >
                            <option value="减脂">减脂</option>
                            <option value="增肌">增肌</option>
                            <option value="塑形">塑形</option>
                            <option value="健康">健康</option>
                            <option value="力量">力量</option>
                          </select>
                        </div>
                      </div>

                      <div className="flex space-x-2">
                        <button 
                          onClick={handleSaveProfile}
                          className="flex-1 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 flex items-center justify-center"
                        >
                          <Save size={16} className="mr-2" />
                          保存
                        </button>
                        <button 
                          onClick={() => {
                            setIsEditingProfile(false);
                            setTempProfile(userProfile);
                          }}
                          className="flex-1 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 设置弹窗 */}
            {showSettings && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[80vh] overflow-y-auto">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">系统设置</h2>
                    <button 
                      onClick={() => setShowSettings(false)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <X size={20} />
                    </button>
                  </div>
                  
                  <div className="space-y-6">
                    {/* 声音设置 */}
                    <div>
                      <h3 className="font-semibold mb-3 flex items-center">
                        {settings.soundEnabled ? <Volume2 size={16} className="mr-2" /> : <VolumeX size={16} className="mr-2" />}
                        声音设置
                      </h3>
                      <div className="space-y-2">
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={settings.soundEnabled}
                            onChange={(e) => handleSaveSettings({...settings, soundEnabled: e.target.checked})}
                            className="mr-2"
                          />
                          <span className="text-sm">启用音效</span>
                        </label>
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={settings.voiceEnabled}
                            onChange={(e) => handleSaveSettings({...settings, voiceEnabled: e.target.checked})}
                            className="mr-2"
                          />
                          <span className="text-sm">语音指导</span>
                        </label>
                      </div>
                    </div>

                    {/* 显示设置 */}
                    <div>
                      <h3 className="font-semibold mb-3 flex items-center">
                        <Monitor size={16} className="mr-2" />
                        显示设置
                      </h3>
                      <div className="space-y-2">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">主题</label>
                          <select
                            value={settings.theme}
                            onChange={(e) => handleSaveSettings({...settings, theme: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          >
                            <option value="dark">深色主题</option>
                            <option value="light">浅色主题</option>
                            <option value="auto">自动</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">语言</label>
                          <select
                            value={settings.language}
                            onChange={(e) => handleSaveSettings({...settings, language: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          >
                            <option value="zh-CN">简体中文</option>
                            <option value="zh-TW">繁体中文</option>
                            <option value="en-US">English</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    {/* 训练设置 */}
                    <div>
                      <h3 className="font-semibold mb-3 flex items-center">
                        <Activity size={16} className="mr-2" />
                        训练设置
                      </h3>
                      <div className="space-y-2">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">难度级别</label>
                          <select
                            value={settings.difficulty}
                            onChange={(e) => handleSaveSettings({...settings, difficulty: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          >
                            <option value="easy">简单</option>
                            <option value="medium">中等</option>
                            <option value="hard">困难</option>
                          </select>
                        </div>
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={settings.autoStart}
                            onChange={(e) => handleSaveSettings({...settings, autoStart: e.target.checked})}
                            className="mr-2"
                          />
                          <span className="text-sm">自动开始下一组</span>
                        </label>
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={settings.notifications}
                            onChange={(e) => handleSaveSettings({...settings, notifications: e.target.checked})}
                            className="mr-2"
                          />
                          <span className="text-sm">训练提醒</span>
                        </label>
                      </div>
                    </div>

                    {/* 系统信息 */}
                    <div className="border-t pt-4">
                      <h3 className="font-semibold mb-3">系统信息</h3>
                      <div className="space-y-1 text-sm text-gray-600">
                        <div>版本: 1.0.0</div>
                        <div>用户ID: {userId.substring(0, 8)}...</div>
                        <div>MediaPipe: {isInitialized ? '已加载' : '未加载'}</div>
                        <div>摄像头: {isActive ? '已连接' : '未连接'}</div>
                      </div>
                    </div>
                  </div>

                  <button 
                    onClick={() => setShowSettings(false)}
                    className="w-full mt-6 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    确定
                  </button>
                </div>
              </div>
            )}

            {/* 今日目标 */}
            <div className="bg-white bg-opacity-10 backdrop-filter backdrop-blur-lg rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">今日目标</h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300">{getExerciseName(currentExercise)}</span>
                  <span className="text-white">{exerciseStats.count}/20</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300" 
                    style={{ width: `${Math.min((exerciseStats.count / 20) * 100, 100)}%` }}
                  ></div>
                </div>
                
                <div className="flex justify-between text-sm mt-3">
                  <span className="text-gray-300">运动时长</span>
                  <span className="text-white">{Math.floor(duration / 60)}/30 分钟</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full transition-all duration-300" 
                    style={{ width: `${Math.min((duration / 1800) * 100, 100)}%` }}
                  ></div>
                </div>

                {/* 准确率显示 */}
                <div className="flex justify-between text-sm mt-3">
                  <span className="text-gray-300">动作准确率</span>
                  <span className="text-white">{(exerciseStats.accuracy * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-purple-500 h-2 rounded-full transition-all duration-300" 
                    style={{ width: `${exerciseStats.accuracy * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* 系统状态面板 */}
            <div className="bg-white bg-opacity-10 backdrop-filter backdrop-blur-lg rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">系统状态</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-300">MediaPipe状态:</span>
                  <span className={initError ? 'text-red-400' : isInitialized ? 'text-green-400' : 'text-yellow-400'}>
                    {initError ? '初始化失败' : isInitialized ? '正常运行' : '初始化中'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">摄像头状态:</span>
                  <span className={isActive ? 'text-green-400' : 'text-gray-400'}>
                    {isActive ? '已连接' : '未连接'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">当前运动:</span>
                  <span className="text-blue-400">{getExerciseName(currentExercise)}</span>
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
            {isActive ? (
              <p className="mt-1 text-green-400">
                ✨ AI分析引擎正在为您提供实时指导
              </p>
            ) : initError ? (
              <p className="mt-1 text-red-400">
                ⚠️ AI服务连接异常，请刷新页面重试
              </p>
            ) : !isInitialized ? (
              <p className="mt-1 text-yellow-400">
                🔄 AI服务正在初始化，请稍候...
              </p>
            ) : (
              <p className="mt-1 text-blue-400">
                🚀 AI服务已就绪，开始您的健身之旅
              </p>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
