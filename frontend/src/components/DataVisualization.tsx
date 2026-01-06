import React, { useEffect, useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Activity, PieChart as PieChartIcon, TrendingUp } from 'lucide-react';

interface WeeklyStat {
  date: string;
  day: string;
  count: number;
  duration: number;
}

interface DistributionStat {
  name: string;
  value: number;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const DataVisualization: React.FC = () => {
  const { token } = useAuth();
  const [weeklyData, setWeeklyData] = useState<WeeklyStat[]>([]);
  const [distributionData, setDistributionData] = useState<DistributionStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      try {
        const [weeklyRes, distRes] = await Promise.all([
          api.get('/api/user/stats/weekly', token),
          api.get('/api/user/stats/exercise-distribution', token)
        ]);
        setWeeklyData(weeklyRes);
        setDistributionData(distRes);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  if (loading) {
    return <div className="flex justify-center p-8">加载数据中...</div>;
  }

  return (
    <div className="space-y-8">
      {/* 顶部概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Activity className="text-blue-600" size={20} />
            </div>
            <h3 className="font-semibold text-gray-700">本周运动总数</h3>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {weeklyData.reduce((acc, curr) => acc + curr.count, 0)}
            <span className="text-sm font-normal text-gray-500 ml-2">次</span>
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-green-100 rounded-lg">
              <TrendingUp className="text-green-600" size={20} />
            </div>
            <h3 className="font-semibold text-gray-700">本周运动时长</h3>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {Math.round(weeklyData.reduce((acc, curr) => acc + curr.duration, 0))}
            <span className="text-sm font-normal text-gray-500 ml-2">分钟</span>
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-purple-100 rounded-lg">
              <PieChartIcon className="text-purple-600" size={20} />
            </div>
            <h3 className="font-semibold text-gray-700">最爱运动</h3>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {distributionData.length > 0 
              ? distributionData.sort((a, b) => b.value - a.value)[0].name 
              : '暂无'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* 周运动趋势图 */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-800 mb-6">本周运动趋势</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" />
                <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
                <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                />
                <Legend />
                <Bar yAxisId="left" dataKey="count" name="次数" fill="#8884d8" radius={[4, 4, 0, 0]} />
                <Bar yAxisId="right" dataKey="duration" name="时长(分钟)" fill="#82ca9d" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 运动类型分布图 */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-800 mb-6">运动类型分布</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={distributionData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {distributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataVisualization;
