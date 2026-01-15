import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Users,
  BookOpen,
  Terminal,
  Clock,
  Award,
  Download,
  Calendar
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { analyticsApi } from '@/services/api';

interface AnalyticsData {
  total_members: number;
  members_change: number;
  active_members: number;
  active_change: number;
  avg_progress: number;
  progress_change: number;
  total_completions: number;
  completions_change: number;
  total_time_hours: number;
  courses_completed: number;
  labs_completed: number;
  batch_performance: {
    name: string;
    progress: number;
    members: number;
  }[];
  progress_distribution: {
    range: string;
    count: number;
  }[];
  activity_summary: {
    date: string;
    logins: number;
    courses: number;
    labs: number;
  }[];
}

export default function PortalAnalytics() {
  const router = useRouter();
  const { orgId } = router.query;
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30d');

  useEffect(() => {
    if (orgId) {
      fetchAnalytics();
    }
  }, [orgId, dateRange]);

  const fetchAnalytics = async () => {
    if (typeof orgId !== 'string') return;

    try {
      const data = await analyticsApi.getOrg(orgId);
      setAnalytics(data);
    } catch (error) {
      // Fallback data
      setAnalytics({
        total_members: 0,
        members_change: 0,
        active_members: 0,
        active_change: 0,
        avg_progress: 0,
        progress_change: 0,
        total_completions: 0,
        completions_change: 0,
        total_time_hours: 0,
        courses_completed: 0,
        labs_completed: 0,
        batch_performance: [],
        progress_distribution: [
          { range: '0-25%', count: 0 },
          { range: '26-50%', count: 0 },
          { range: '51-75%', count: 0 },
          { range: '76-100%', count: 0 }
        ],
        activity_summary: []
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    // Export analytics data
    const data = JSON.stringify(analytics, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
  };

  const statCards = [
    {
      label: 'Total Members',
      value: analytics?.total_members || 0,
      change: analytics?.members_change || 0,
      icon: Users,
      color: 'green'
    },
    {
      label: 'Active Members',
      value: analytics?.active_members || 0,
      change: analytics?.active_change || 0,
      icon: TrendingUp,
      color: 'blue'
    },
    {
      label: 'Avg Progress',
      value: `${analytics?.avg_progress || 0}%`,
      change: analytics?.progress_change || 0,
      icon: BarChart3,
      color: 'purple'
    },
    {
      label: 'Completions',
      value: analytics?.total_completions || 0,
      change: analytics?.completions_change || 0,
      icon: Award,
      color: 'yellow'
    }
  ];

  const getColorClass = (color: string) => {
    const colors: Record<string, string> = {
      green: 'bg-cyber-accent/10 text-cyber-accent',
      blue: 'bg-blue-500/10 text-blue-400',
      purple: 'bg-purple-500/10 text-purple-400',
      yellow: 'bg-yellow-500/10 text-yellow-400'
    };
    return colors[color] || colors.green;
  };

  return (
    <PortalLayout title="Analytics" subtitle="Organization performance and insights">
      {/* Date Range & Export */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-gray-400" />
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent transition-colors"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="1y">Last year</option>
          </select>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 border border-cyber-accent/20 text-gray-400 rounded-lg hover:text-white hover:bg-white/5 transition-colors"
        >
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {statCards.map((card) => (
              <div
                key={card.label}
                className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-lg ${getColorClass(card.color)}`}>
                    <card.icon className="w-6 h-6" />
                  </div>
                  {card.change !== 0 && (
                    <div className={`flex items-center gap-1 text-sm ${
                      card.change > 0 ? 'text-cyber-accent' : 'text-red-400'
                    }`}>
                      {card.change > 0 ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : (
                        <TrendingDown className="w-4 h-4" />
                      )}
                      <span>{Math.abs(card.change)}%</span>
                    </div>
                  )}
                </div>
                <p className="text-3xl font-bold text-white mb-1">{card.value}</p>
                <p className="text-sm text-gray-400">{card.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Activity Summary */}
            <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Activity Summary</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-cyber-accent/5">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-cyber-accent/10">
                      <BookOpen className="w-5 h-5 text-cyber-accent" />
                    </div>
                    <span className="text-white">Courses Completed</span>
                  </div>
                  <span className="text-2xl font-bold text-white">{analytics?.courses_completed || 0}</span>
                </div>
                <div className="flex items-center justify-between p-4 rounded-lg bg-blue-500/5">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-500/10">
                      <Terminal className="w-5 h-5 text-blue-400" />
                    </div>
                    <span className="text-white">Labs Completed</span>
                  </div>
                  <span className="text-2xl font-bold text-white">{analytics?.labs_completed || 0}</span>
                </div>
                <div className="flex items-center justify-between p-4 rounded-lg bg-purple-500/5">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-purple-500/10">
                      <Clock className="w-5 h-5 text-purple-400" />
                    </div>
                    <span className="text-white">Total Time Spent</span>
                  </div>
                  <span className="text-2xl font-bold text-white">{analytics?.total_time_hours || 0}h</span>
                </div>
              </div>
            </div>

            {/* Batch Performance */}
            <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Batch Performance</h3>
              {analytics?.batch_performance && analytics.batch_performance.length > 0 ? (
                <div className="space-y-4">
                  {analytics.batch_performance.map((batch, index) => (
                    <div key={index}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-white">{batch.name}</span>
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-gray-500">{batch.members} members</span>
                          <span className="text-cyber-accent font-medium">{batch.progress}%</span>
                        </div>
                      </div>
                      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyber-accent rounded-full transition-all"
                          style={{ width: `${batch.progress}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <BarChart3 className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">No batch data available</p>
                </div>
              )}
            </div>

            {/* Progress Distribution */}
            <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Progress Distribution</h3>
              <div className="space-y-3">
                {analytics?.progress_distribution?.map((item, index) => {
                  const total = analytics.progress_distribution.reduce((sum, i) => sum + i.count, 0) || 1;
                  const percentage = Math.round((item.count / total) * 100);
                  return (
                    <div key={index}>
                      <div className="flex items-center justify-between mb-1.5 text-sm">
                        <span className="text-gray-400">{item.range}</span>
                        <span className="text-white">{item.count} members ({percentage}%)</span>
                      </div>
                      <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            index === 3 ? 'bg-green-500' :
                            index === 2 ? 'bg-blue-500' :
                            index === 1 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Key Metrics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-cyber-accent/5 text-center">
                  <p className="text-3xl font-bold text-cyber-accent">
                    {analytics?.total_members ? Math.round((analytics.active_members / analytics.total_members) * 100) : 0}%
                  </p>
                  <p className="text-sm text-gray-400 mt-1">Engagement Rate</p>
                </div>
                <div className="p-4 rounded-lg bg-blue-500/5 text-center">
                  <p className="text-3xl font-bold text-blue-400">
                    {analytics?.total_members ? Math.round(analytics.total_time_hours / analytics.total_members) : 0}h
                  </p>
                  <p className="text-sm text-gray-400 mt-1">Avg Time/Member</p>
                </div>
                <div className="p-4 rounded-lg bg-purple-500/5 text-center">
                  <p className="text-3xl font-bold text-purple-400">
                    {analytics?.total_members ? Math.round(analytics.courses_completed / analytics.total_members * 10) / 10 : 0}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">Courses/Member</p>
                </div>
                <div className="p-4 rounded-lg bg-yellow-500/5 text-center">
                  <p className="text-3xl font-bold text-yellow-400">
                    {analytics?.total_members ? Math.round(analytics.labs_completed / analytics.total_members * 10) / 10 : 0}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">Labs/Member</p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </PortalLayout>
  );
}
