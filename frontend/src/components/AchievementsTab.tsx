import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Trophy, Sparkles } from 'lucide-react';

interface AchievementsTabProps {
  token: string | null;
}

const AchievementsTab: React.FC<AchievementsTabProps> = ({ token }) => {
  const [loading, setLoading] = useState(true);
  const [achievements, setAchievements] = useState<any[]>([]);
  const [newAchievements, setNewAchievements] = useState<any[]>([]);

  useEffect(() => {
    loadAchievements();
    checkAchievements();
  }, []);

  const loadAchievements = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const response = await api.get('/api/user/achievements', token);
      setAchievements(response.achievements || []);
    } catch (err: any) {
      console.error('加载成就失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const checkAchievements = async () => {
    if (!token) return;
    
    try {
      const response = await api.post('/api/user/achievements/check', {}, token);
      if (response.new_achievements && response.new_achievements.length > 0) {
        setNewAchievements(response.new_achievements);
        setTimeout(() => {
          setNewAchievements([]);
          loadAchievements();
        }, 5000);
      }
    } catch (err: any) {
      console.error('检查成就失败:', err);
    }
  };

  const unlockedAchievements = achievements.filter(a => a.unlocked);
  const lockedAchievements = achievements.filter(a => !a.unlocked);

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
      {/* 新成就提示 */}
      {newAchievements.length > 0 && (
        <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-300 rounded-lg p-4 animate-bounce">
          <div className="flex items-center gap-3">
            <Sparkles className="h-6 w-6 text-yellow-600" />
            <div>
              <h3 className="font-bold text-yellow-900">恭喜解锁新成就！</h3>
              <div className="flex gap-2 mt-1">
                {newAchievements.map((achievement: any) => (
                  <span key={achievement.id} className="text-sm">
                    {achievement.icon} {achievement.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 成就统计 */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-900">成就进度</h3>
            <p className="text-sm text-gray-600 mt-1">
              已解锁 {unlockedAchievements.length} / {achievements.length} 个成就
            </p>
          </div>
          <div className="text-4xl font-bold text-blue-600">
            {Math.round((unlockedAchievements.length / achievements.length) * 100)}%
          </div>
        </div>
        <div className="mt-4 w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-gradient-to-r from-blue-600 to-purple-600 h-3 rounded-full transition-all duration-500"
            style={{ width: `${(unlockedAchievements.length / achievements.length) * 100}%` }}
          ></div>
        </div>
      </div>

      {/* 已解锁成就 */}
      {unlockedAchievements.length > 0 && (
        <div>
          <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Trophy className="h-6 w-6 text-yellow-500" />
            已解锁成就 ({unlockedAchievements.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {unlockedAchievements.map((achievement: any) => (
              <div
                key={achievement.id}
                className="bg-gradient-to-br from-yellow-50 to-orange-50 border-2 border-yellow-300 rounded-lg p-4 hover:shadow-lg transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className="text-4xl">{achievement.icon}</div>
                  <div className="flex-1">
                    <h4 className="font-bold text-gray-900">{achievement.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{achievement.description}</p>
                    {achievement.unlocked_at && (
                      <p className="text-xs text-gray-500 mt-2">
                        解锁时间: {new Date(achievement.unlocked_at).toLocaleDateString('zh-CN')}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 未解锁成就 */}
      {lockedAchievements.length > 0 && (
        <div>
          <h3 className="text-xl font-bold text-gray-900 mb-4">未解锁成就 ({lockedAchievements.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {lockedAchievements.map((achievement: any) => (
              <div
                key={achievement.id}
                className="bg-gray-50 border border-gray-200 rounded-lg p-4 opacity-60"
              >
                <div className="flex items-start gap-3">
                  <div className="text-4xl grayscale">{achievement.icon}</div>
                  <div className="flex-1">
                    <h4 className="font-bold text-gray-700">{achievement.name}</h4>
                    <p className="text-sm text-gray-500 mt-1">{achievement.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AchievementsTab;

