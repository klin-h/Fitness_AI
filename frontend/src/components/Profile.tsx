import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { User, Lock, Mail, UserCircle, Save, LogOut, ArrowLeft, Edit2, History, Target, Sparkles, Trophy, TrendingUp } from 'lucide-react';
import AchievementsTab from './AchievementsTab';
import LeaderboardTab from './LeaderboardTab';

const Profile: React.FC = () => {
  const { user, token, logout, updateUser } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // 从URL参数获取初始标签页
  const tabFromUrl = searchParams.get('tab') as 'profile' | 'password' | 'history' | 'plan' | 'achievements' | 'leaderboard' | null;
  const [activeTab, setActiveTab] = useState<'profile' | 'password' | 'history' | 'plan' | 'achievements' | 'leaderboard'>(
    tabFromUrl && ['profile', 'password', 'history', 'plan', 'achievements', 'leaderboard'].includes(tabFromUrl) ? tabFromUrl : 'profile'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // 历史记录相关
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyRecords, setHistoryRecords] = useState<any[]>([]);
  
  // 健身计划相关
  const [planLoading, setPlanLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [aiReasoning, setAiReasoning] = useState('');
  const [showAiResult, setShowAiResult] = useState(false);
  const [dailyGoals, setDailyGoals] = useState({
    squat: 20,
    pushup: 15,
    plank: 60,
    jumping_jack: 30
  });
  const [weeklyGoals, setWeeklyGoals] = useState({
    total_sessions: 5,
    total_duration: 150
  });

  // 个人资料表单
  const [nickname, setNickname] = useState('');
  const [email, setEmail] = useState('');
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');

  // 密码修改表单
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // 监听URL参数变化
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab') as 'profile' | 'password' | 'history' | 'plan' | 'achievements' | 'leaderboard' | null;
    if (tabFromUrl && ['profile', 'password', 'history', 'plan', 'achievements', 'leaderboard'].includes(tabFromUrl)) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams]);

  // 加载用户完整信息（只在组件挂载时执行一次）
  useEffect(() => {
    const loadUserProfile = async () => {
      if (!user || !token) return;
      
      try {
        const userData = await api.get('/api/user/profile', token);
        // 更新表单数据
        setNickname(userData.nickname || '');
        setEmail(userData.email || '');
        setHeight(userData.profile?.height?.toString() || '');
        setWeight(userData.profile?.weight?.toString() || '');
        setAge(userData.profile?.age?.toString() || '');
        setGender(userData.profile?.gender || '');
        // 更新AuthContext中的用户信息
        updateUser(userData);
      } catch (err: any) {
        console.error('加载用户信息失败:', err);
        // 如果API失败，使用AuthContext中的user数据作为后备
        if (user) {
          setNickname(user.nickname || '');
          setEmail(user.email || '');
          setHeight(user.profile?.height?.toString() || '');
          setWeight(user.profile?.weight?.toString() || '');
          setAge(user.profile?.age?.toString() || '');
          setGender(user.profile?.gender || '');
        }
      }
    };

    loadUserProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 只在组件挂载时执行一次

  // 加载历史记录（只在切换到history标签时加载）
  useEffect(() => {
    const loadHistory = async () => {
      if (!user || !token || activeTab !== 'history') return;
      
      setHistoryLoading(true);
      try {
        const response = await api.get(`/api/user/${user.user_id}/history?limit=50`, token);
        setHistoryRecords(response.sessions || []);
      } catch (err: any) {
        console.error('加载历史记录失败:', err);
        setError('加载历史记录失败');
      } finally {
        setHistoryLoading(false);
      }
    };

    if (activeTab === 'history') {
      loadHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]); // 只在activeTab变化时执行，移除user和token依赖

  // 加载健身计划（只在切换到plan标签时加载）
  useEffect(() => {
    const loadPlan = async () => {
      if (!user || !token || activeTab !== 'plan') return;
      
      setPlanLoading(true);
      try {
        const plan = await api.get('/api/user/plan', token);
        if (plan.daily_goals) {
          setDailyGoals(plan.daily_goals);
        }
        if (plan.weekly_goals) {
          setWeeklyGoals(plan.weekly_goals);
        }
      } catch (err: any) {
        console.error('加载健身计划失败:', err);
        setError('加载健身计划失败');
      } finally {
        setPlanLoading(false);
      }
    };

    if (activeTab === 'plan') {
      loadPlan();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]); // 只在activeTab变化时执行，移除user和token依赖

  // AI生成健身计划建议
  const [aiResponse, setAiResponse] = useState<any>(null);
  
  const handleGenerateAIPlan = async () => {
    setError('');
    setSuccess('');
    setAiLoading(true);
    setShowAiResult(false);
    setAiResponse(null);

    try {
      const response = await api.post(
        '/api/ai/generate-plan',
        {
          height: height ? parseFloat(height) : undefined,
          weight: weight ? parseFloat(weight) : undefined,
          age: age ? parseInt(age) : undefined,
          gender: gender || undefined
        },
        token || undefined
      );

      // 保存完整响应
      setAiResponse(response);

      // 应用AI建议到表单
      if (response.daily_goals) {
        setDailyGoals(response.daily_goals);
      }
      if (response.weekly_goals) {
        setWeeklyGoals(response.weekly_goals);
      }
      
      setAiSuggestions(response.suggestions || []);
      setAiReasoning(response.reasoning || '');
      setShowAiResult(false); // 不显示AI建议板块
      
      // 静默应用，不显示成功消息
      // setSuccess('✅ 智谱AI已为您生成个性化健身计划！');
    } catch (err: any) {
      setError(err.message || 'AI生成建议失败，请稍后重试');
      setShowAiResult(false);
    } finally {
      setAiLoading(false);
    }
  };

  // 保存健身计划
  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setPlanLoading(true);

    try {
      await api.put(
        '/api/user/plan',
        {
          daily_goals: dailyGoals,
          weekly_goals: weeklyGoals
        },
        token || undefined
      );

      setSuccess('健身计划更新成功！');
      setShowAiResult(false); // 保存后隐藏AI结果
    } catch (err: any) {
      setError(err.message || '更新失败，请稍后重试');
    } finally {
      setPlanLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const profileData: any = {};
      if (height) profileData.height = parseFloat(height);
      if (weight) profileData.weight = parseFloat(weight);
      if (age) profileData.age = parseInt(age);
      if (gender) profileData.gender = gender;

      const updatedUser = await api.put(
        '/api/user/profile',
        {
          nickname: nickname || undefined,
          email: email || undefined,
          profile: profileData
        },
        token || undefined
      );

      updateUser(updatedUser);
      setSuccess('个人资料更新成功！');
    } catch (err: any) {
      setError(err.message || '更新失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (newPassword.length < 6) {
      setError('新密码长度至少6位');
      return;
    }

    setLoading(true);

    try {
      await api.post(
        '/api/auth/change-password',
        {
          old_password: oldPassword,
          new_password: newPassword
        },
        token || undefined
      );

      setSuccess('密码修改成功！');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err.message || '密码修改失败，请检查旧密码是否正确');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-blue-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white border-b border-blue-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <button
              onClick={() => navigate('/')}
              className="flex items-center text-gray-700 hover:text-blue-600 transition-colors group"
            >
              <ArrowLeft className="h-5 w-5 mr-2 group-hover:-translate-x-1 transition-transform" />
              <span>返回首页</span>
            </button>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 px-4 py-2 bg-blue-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                  {(user.nickname || user.username)[0].toUpperCase()}
                </div>
                <span className="text-gray-900 font-medium">{user.nickname || user.username}</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center text-gray-600 hover:text-red-600 transition-colors px-3 py-2 rounded-lg hover:bg-red-50"
              >
                <LogOut className="h-5 w-5 mr-1" />
                <span className="hidden sm:inline">退出</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-xl p-8 shadow-md border border-blue-100">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              个人中心
            </h1>
            <p className="text-gray-600">管理您的账户信息和设置</p>
          </div>

          {/* 标签页 */}
          <div className="flex space-x-2 mb-8 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('profile')}
              className={`px-6 py-3 font-semibold transition-all rounded-t-lg ${
                activeTab === 'profile'
                  ? 'text-blue-600 bg-blue-50 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              <UserCircle className="inline h-5 w-5 mr-2" />
              个人资料
            </button>
            <button
              onClick={() => setActiveTab('password')}
              className={`px-6 py-3 font-semibold transition-all rounded-t-lg ${
                activeTab === 'password'
                  ? 'text-blue-600 bg-blue-50 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              <Lock className="inline h-5 w-5 mr-2" />
              修改密码
            </button>
            <button
              onClick={() => setActiveTab('history')}
              data-tab="history"
              className={`px-6 py-3 font-semibold transition-all rounded-t-lg ${
                activeTab === 'history'
                  ? 'text-blue-600 bg-blue-50 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              <History className="inline h-5 w-5 mr-2" />
              历史记录
            </button>
            <button
              onClick={() => setActiveTab('plan')}
              data-tab="plan"
              className={`px-6 py-3 font-semibold transition-all rounded-t-lg ${
                activeTab === 'plan'
                  ? 'text-blue-600 bg-blue-50 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              <Target className="inline h-5 w-5 mr-2" />
              健身计划
            </button>
            <button
              onClick={() => setActiveTab('achievements')}
              data-tab="achievements"
              className={`px-6 py-3 font-semibold transition-all rounded-t-lg ${
                activeTab === 'achievements'
                  ? 'text-blue-600 bg-blue-50 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              <Trophy className="inline h-5 w-5 mr-2" />
              成就徽章
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              data-tab="leaderboard"
              className={`px-6 py-3 font-semibold transition-all rounded-t-lg ${
                activeTab === 'leaderboard'
                  ? 'text-blue-600 bg-blue-50 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              <TrendingUp className="inline h-5 w-5 mr-2" />
              排行榜
            </button>
          </div>

          {/* 错误和成功提示 */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center gap-2 animate-shake">
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <span className="text-sm">{error}</span>
            </div>
          )}
          {success && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm">{success}</span>
            </div>
          )}

          {/* 个人资料标签页 */}
          {activeTab === 'profile' && (
            <form onSubmit={handleUpdateProfile} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="block text-gray-700 text-sm font-semibold">
                    用户名
                  </label>
                  <input
                    type="text"
                    value={user.username}
                    disabled
                    className="w-full px-4 py-3.5 bg-gray-50 border border-gray-300 rounded-lg text-gray-500 cursor-not-allowed"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-gray-700 text-sm font-semibold">
                    昵称
                  </label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                      <UserCircle className="h-5 w-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                    </div>
                    <input
                      type="text"
                      value={nickname}
                      onChange={(e) => setNickname(e.target.value)}
                      className="w-full pl-12 pr-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      placeholder="请输入昵称"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-gray-700 text-sm font-semibold">
                    邮箱
                  </label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                      <Mail className="h-5 w-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full pl-12 pr-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      placeholder="请输入邮箱"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-gray-700 text-sm font-semibold">
                    身高 (cm)
                  </label>
                  <input
                    type="number"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    className="w-full px-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="请输入身高"
                    min="0"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-gray-700 text-sm font-semibold">
                    体重 (kg)
                  </label>
                  <input
                    type="number"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                    className="w-full px-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="请输入体重"
                    min="0"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-gray-700 text-sm font-semibold">
                    年龄
                  </label>
                  <input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    className="w-full px-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="请输入年龄"
                    min="0"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-gray-300 text-sm font-semibold">
                    性别
                  </label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full px-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  >
                    <option value="">请选择</option>
                    <option value="male">男</option>
                    <option value="female">女</option>
                    <option value="other">其他</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full md:w-auto bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3.5 px-8 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>保存中...</span>
                  </>
                ) : (
                  <>
                    <Save className="h-5 w-5" />
                    <span>保存修改</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* 修改密码标签页 */}
          {activeTab === 'password' && (
            <form onSubmit={handleChangePassword} className="space-y-6 max-w-md">
              <div className="space-y-2">
                <label className="block text-gray-700 text-sm font-semibold">
                  旧密码
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                  </div>
                  <input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    className="w-full pl-12 pr-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="请输入旧密码"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-gray-700 text-sm font-semibold">
                  新密码
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                  </div>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full pl-12 pr-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="至少6位字符"
                    required
                    minLength={6}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-gray-700 text-sm font-semibold">
                  确认新密码
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                  </div>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pl-12 pr-4 py-3.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="请再次输入新密码"
                    required
                    minLength={6}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3.5 px-6 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>修改中...</span>
                  </>
                ) : (
                  <>
                    <Save className="h-5 w-5" />
                    <span>修改密码</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* 历史记录标签页 */}
          {activeTab === 'history' && (
            <div className="space-y-4">
              {historyLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                  <span className="ml-3 text-gray-600">加载中...</span>
                </div>
              ) : historyRecords.length === 0 ? (
                <div className="text-center py-12">
                  <History className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500 text-lg">暂无历史记录</p>
                  <p className="text-gray-400 text-sm mt-2">开始运动后，您的记录将显示在这里</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {historyRecords.map((record, index) => {
                    const startTime = new Date(record.start_time);
                    const endTime = record.end_time ? new Date(record.end_time) : null;
                    const duration = endTime 
                      ? Math.floor((endTime.getTime() - startTime.getTime()) / 1000)
                      : null;
                    // 确保准确率不超过100%，并且correct_count不超过total_count
                    const correctCount = Math.min(record.correct_count || 0, record.total_count || 0);
                    const accuracy = record.total_count > 0 
                      ? Math.min(100, (correctCount / record.total_count) * 100).toFixed(1)
                      : '0';
                    
                    const exerciseNames: { [key: string]: string } = {
                      'squat': '深蹲',
                      'pushup': '俯卧撑',
                      'plank': '平板支撑',
                      'jumping_jack': '开合跳'
                    };
                    
                    return (
                      <div key={index} className="bg-gray-50 rounded-lg p-6 border border-gray-200 hover:border-blue-300 transition-all">
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900">
                              {exerciseNames[record.exercise_type] || record.exercise_type}
                            </h3>
                            <p className="text-sm text-gray-500 mt-1">
                              {startTime.toLocaleString('zh-CN')}
                            </p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            record.status === 'completed' 
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {record.status === 'completed' ? '已完成' : '进行中'}
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <p className="text-xs text-gray-500 mb-1">完成次数</p>
                            <p className="text-lg font-semibold text-gray-900">{record.total_count}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500 mb-1">准确次数</p>
                            <p className="text-lg font-semibold text-green-600">{record.correct_count}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500 mb-1">准确率</p>
                            <p className="text-lg font-semibold text-blue-600">{accuracy}%</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500 mb-1">运动时长</p>
                            <p className="text-lg font-semibold text-gray-900">
                              {duration ? `${Math.floor(duration / 60)}分${duration % 60}秒` : '进行中'}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* 健身计划标签页 */}
          {activeTab === 'plan' && (
            <form onSubmit={handleSavePlan} className="space-y-6">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm text-blue-800 mb-2">
                      💡 设置您的每日和每周健身目标，系统将根据您的计划跟踪进度
                    </p>
                    <p className="text-xs text-gray-600">
                      🤖 点击下方"AI生成建议"按钮，让AI根据您的身体指标生成个性化健身计划
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleGenerateAIPlan}
                    disabled={aiLoading || planLoading}
                    className="ml-4 flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold py-2.5 px-5 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md whitespace-nowrap"
                  >
                    {aiLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        <span>AI生成中...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        <span>AI生成建议</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* AI生成结果展示 - 已隐藏 */}

              {/* 每日目标 */}
              <div>
                <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Target className="h-6 w-6 text-blue-600" />
                  每日目标
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="block text-gray-700 text-sm font-semibold">
                      深蹲 (次)
                    </label>
                    <input
                      type="number"
                      value={dailyGoals.squat}
                      onChange={(e) => setDailyGoals({...dailyGoals, squat: parseInt(e.target.value) || 0})}
                      className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      min="0"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="block text-gray-700 text-sm font-semibold">
                      俯卧撑 (次)
                    </label>
                    <input
                      type="number"
                      value={dailyGoals.pushup}
                      onChange={(e) => setDailyGoals({...dailyGoals, pushup: parseInt(e.target.value) || 0})}
                      className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      min="0"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="block text-gray-700 text-sm font-semibold">
                      平板支撑 (秒)
                    </label>
                    <input
                      type="number"
                      value={dailyGoals.plank}
                      onChange={(e) => setDailyGoals({...dailyGoals, plank: parseInt(e.target.value) || 0})}
                      className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      min="0"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="block text-gray-700 text-sm font-semibold">
                      开合跳 (次)
                    </label>
                    <input
                      type="number"
                      value={dailyGoals.jumping_jack}
                      onChange={(e) => setDailyGoals({...dailyGoals, jumping_jack: parseInt(e.target.value) || 0})}
                      className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      min="0"
                    />
                  </div>
                </div>
              </div>

              {/* 每周目标 */}
              <div>
                <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Target className="h-6 w-6 text-blue-600" />
                  每周目标
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="block text-gray-700 text-sm font-semibold">
                      总运动次数
                    </label>
                    <input
                      type="number"
                      value={weeklyGoals.total_sessions}
                      onChange={(e) => setWeeklyGoals({...weeklyGoals, total_sessions: parseInt(e.target.value) || 0})}
                      className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      min="0"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="block text-gray-700 text-sm font-semibold">
                      总运动时长 (分钟)
                    </label>
                    <input
                      type="number"
                      value={weeklyGoals.total_duration}
                      onChange={(e) => setWeeklyGoals({...weeklyGoals, total_duration: parseInt(e.target.value) || 0})}
                      className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      min="0"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={planLoading}
                className="w-full md:w-auto bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3.5 px-8 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md flex items-center justify-center gap-2"
              >
                {planLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>保存中...</span>
                  </>
                ) : (
                  <>
                    <Save className="h-5 w-5" />
                    <span>保存计划</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* 成就徽章标签页 */}
          {activeTab === 'achievements' && (
            <AchievementsTab token={token || null} />
          )}

          {/* 排行榜标签页 */}
          {activeTab === 'leaderboard' && (
            <LeaderboardTab />
          )}
        </div>
      </main>
    </div>
  );
};

export default Profile;

