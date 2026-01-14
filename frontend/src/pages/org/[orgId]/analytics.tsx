import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp, Users, BookOpen, Award, Target, Loader2,
  ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi, analyticsApi } from '@/services/api';
import OrgLayout from '@/components/common/OrgLayout';

export default function OrgAnalytics() {
  const router = useRouter();
  const { orgId } = router.query;
  const { isAuthenticated } = useAuthStore();

  const { data: orgData } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsApi.get(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  const { data: analyticsData, isLoading } = useQuery({
    queryKey: ['organization-analytics', orgId],
    queryFn: () => analyticsApi.getOrg(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  if (isLoading) {
    return (
      <OrgLayout>
        <div className="flex justify-center items-center min-h-[400px]">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
        </div>
      </OrgLayout>
    );
  }

  const org = orgData?.organization || orgData;
  const stats = analyticsData?.stats || {};
  const trends = analyticsData?.trends || {};

  return (
    <OrgLayout title="Analytics" subtitle={org?.name}>
      {/* Overview Stats */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Users}
          label="Total Members"
          value={stats.total_members || 0}
          trend={trends.members_change}
          color="blue"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Progress"
          value={`${Math.round(stats.avg_progress || 0)}%`}
          trend={trends.progress_change}
          color="green"
        />
        <StatCard
          icon={BookOpen}
          label="Courses Completed"
          value={stats.total_completions || 0}
          trend={trends.completions_change}
          color="purple"
        />
        <StatCard
          icon={Target}
          label="Labs Completed"
          value={stats.labs_completed || 0}
          trend={trends.labs_change}
          color="orange"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        {/* Activity Summary */}
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-6">Activity Summary</h2>
          <div className="space-y-4">
            <ActivityMetric
              label="Active this week"
              value={stats.active_this_week || 0}
              total={stats.total_members || 0}
              color="blue"
            />
            <ActivityMetric
              label="Active this month"
              value={stats.active_this_month || 0}
              total={stats.total_members || 0}
              color="green"
            />
            <ActivityMetric
              label="Completed at least 1 course"
              value={stats.members_with_completions || 0}
              total={stats.total_members || 0}
              color="purple"
            />
            <ActivityMetric
              label="Completed at least 1 lab"
              value={stats.members_with_labs || 0}
              total={stats.total_members || 0}
              color="orange"
            />
          </div>
        </div>

        {/* Batch Performance */}
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-6">Batch Performance</h2>
          {analyticsData?.batches?.length > 0 ? (
            <div className="space-y-4">
              {analyticsData.batches.slice(0, 5).map((batch: any) => (
                <div key={batch.id} className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{batch.name}</p>
                    <p className="text-xs text-gray-500">{batch.member_count || 0} members</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-[#0a0a0f] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${batch.avg_progress || 0}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-400 w-12 text-right">
                      {Math.round(batch.avg_progress || 0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Award className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No batch data available</p>
            </div>
          )}
        </div>
      </div>

      {/* Course Completion Stats */}
      <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-6">
        <h2 className="text-lg font-semibold text-white mb-6">Learning Progress Distribution</h2>
        <div className="grid md:grid-cols-4 gap-6">
          <ProgressBucket
            label="Not Started"
            count={stats.not_started_count || 0}
            total={stats.total_members || 0}
            color="gray"
          />
          <ProgressBucket
            label="In Progress (1-50%)"
            count={stats.in_progress_low_count || 0}
            total={stats.total_members || 0}
            color="yellow"
          />
          <ProgressBucket
            label="Almost Done (51-99%)"
            count={stats.in_progress_high_count || 0}
            total={stats.total_members || 0}
            color="blue"
          />
          <ProgressBucket
            label="Completed"
            count={stats.completed_count || 0}
            total={stats.total_members || 0}
            color="green"
          />
        </div>
      </div>
    </OrgLayout>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  color,
}: {
  icon: any;
  label: string;
  value: number | string;
  trend?: number;
  color: 'blue' | 'green' | 'purple' | 'orange';
}) {
  const colorClasses = {
    blue: 'text-blue-400 bg-blue-500/20',
    green: 'text-green-400 bg-green-500/20',
    purple: 'text-purple-400 bg-purple-500/20',
    orange: 'text-orange-400 bg-orange-500/20',
  };

  return (
    <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        {trend !== undefined && (
          <div className={`flex items-center gap-1 text-sm ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {trend >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
}

function ActivityMetric({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: 'blue' | 'green' | 'purple' | 'orange';
}) {
  const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    orange: 'bg-orange-500',
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-gray-400 text-sm">{label}</span>
        <span className="text-white font-medium">{value} / {total}</span>
      </div>
      <div className="h-2 bg-[#0a0a0f] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${colorClasses[color]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function ProgressBucket({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: 'gray' | 'yellow' | 'blue' | 'green';
}) {
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
  const colorClasses = {
    gray: 'text-gray-400 bg-gray-500/20',
    yellow: 'text-yellow-400 bg-yellow-500/20',
    blue: 'text-blue-400 bg-blue-500/20',
    green: 'text-green-400 bg-green-500/20',
  };

  return (
    <div className="text-center p-4 bg-[#0a0a0f] rounded-lg">
      <div className={`text-3xl font-bold mb-1 ${colorClasses[color].split(' ')[0]}`}>
        {count}
      </div>
      <div className="text-sm text-gray-400 mb-2">{label}</div>
      <div className={`text-xs px-2 py-1 rounded-full inline-block ${colorClasses[color]}`}>
        {percentage}%
      </div>
    </div>
  );
}
