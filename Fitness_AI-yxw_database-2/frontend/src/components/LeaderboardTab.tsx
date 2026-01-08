import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Trophy, Medal, Award, TrendingUp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const LeaderboardTab: React.FC = () => {
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'count' | 'duration' | 'streak' | 'accuracy'>('count');
  const [leaderboard, setLeaderboard] = useState<any[]>([]);

  useEffect(() => {
    loadLeaderboard();
  }, [activeTab]);

  const loadLeaderboard = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      let endpoint = '';
      switch (activeTab) {
        case 'count':
          endpoint = '/api/leaderboard/weekly-count';
          break;
        case 'duration':
          endpoint = '/api/leaderboard/weekly-duration';
          break;
        case 'streak':
          endpoint = '/api/leaderboard/streak';
          break;
        case 'accuracy':
          endpoint = '/api/leaderboard/accuracy';
          break;
      }
      
      const response = await api.get(endpoint, token);
      setLeaderboard(response.leaderboard || []);
    } catch (err: any) {
      console.error('加载排行榜失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRankIcon = (rank: number | undefined) => {
    const rankNum = rank ?? 0;
    if (rankNum === 1) return <Trophy className="h-6 w-6 text-yellow-500" />;
    if (rankNum === 2) return <Medal className="h-6 w-6 text-gray-400" />;
    if (rankNum === 3) return <Award className="h-6 w-6 text-orange-500" />;
    return <span className="text-gray-400 font-bold">#{rankNum}</span>;
  };

  const getValueDisplay = (item: any) => {
    switch (activeTab) {
      case 'count':
        return `${item.count ?? 0} 次`;
      case 'duration':
        return `${Math.round(item.duration ?? 0)} 分钟`;
      case 'streak':
        return `${item.streak ?? 0} 天`;
      case 'accuracy':
        const accuracy = item.accuracy ?? 0;
        return `${typeof accuracy === 'number' ? accuracy.toFixed(1) : '0.0'}%`;
      default:
        return '';
    }
  };

  const getTabName = () => {
    switch (activeTab) {
      case 'count':
        return '本周运动次数';
      case 'duration':
        return '本周运动时长';
      case 'streak':
        return '连续打卡';
      case 'accuracy':
        return '平均准确率';
      default:
        return '';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
        <span className="ml-3 text-gray-600">加载中...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 标签切换 */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveTab('count')}
          className={`px-4 py-2 rounded-lg font-semibold transition-all ${
            activeTab === 'count'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          运动次数
        </button>
        <button
          onClick={() => setActiveTab('duration')}
          className={`px-4 py-2 rounded-lg font-semibold transition-all ${
            activeTab === 'duration'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          运动时长
        </button>
        <button
          onClick={() => setActiveTab('streak')}
          className={`px-4 py-2 rounded-lg font-semibold transition-all ${
            activeTab === 'streak'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          连续打卡
        </button>
        <button
          onClick={() => setActiveTab('accuracy')}
          className={`px-4 py-2 rounded-lg font-semibold transition-all ${
            activeTab === 'accuracy'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          准确率
        </button>
      </div>

      {/* 排行榜标题 */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200">
        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-blue-600" />
          {getTabName()}排行榜
        </h3>
      </div>

      {/* 排行榜列表 */}
      {leaderboard.length === 0 ? (
        <div className="text-center py-12">
          <Trophy className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">暂无排行榜数据</p>
        </div>
      ) : (
        <div className="space-y-3">
          {leaderboard.map((item: any, index: number) => {
            const isCurrentUser = user && item.user_id === user.user_id;
            return (
              <div
                key={index}
                className={`flex items-center gap-4 p-4 rounded-lg border-2 transition-all ${
                  isCurrentUser
                    ? 'bg-blue-50 border-blue-300 shadow-md'
                    : (item.rank ?? 0) <= 3
                    ? 'bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-300'
                    : 'bg-white border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex-shrink-0 w-12 flex items-center justify-center">
                  {getRankIcon(item.rank ?? index + 1)}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-gray-900">{item.nickname || item.username || '匿名用户'}</h4>
                    {isCurrentUser && (
                      <span className="px-2 py-1 bg-blue-600 text-white text-xs rounded-full">我</span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-gray-900">{getValueDisplay(item)}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default LeaderboardTab;

