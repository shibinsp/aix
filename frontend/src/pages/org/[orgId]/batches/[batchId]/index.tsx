import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  FolderKanban, Users, BookOpen, TrendingUp, ArrowLeft, Loader2,
  Calendar, UserPlus, Award, Target
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { batchesApi, analyticsApi } from '@/services/api';
import OrgLayout from '@/components/common/OrgLayout';

const statusColors: Record<string, string> = {
  active: 'bg-green-500/20 text-green-400 border-green-500/30',
  inactive: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  archived: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
};

export default function OrgBatchDashboard() {
  const router = useRouter();
  const { orgId, batchId } = router.query;
  const { isAuthenticated } = useAuthStore();

  const { data: batchData, isLoading, error } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => batchesApi.get(batchId as string),
    enabled: isAuthenticated && !!batchId,
  });

  const { data: analyticsData } = useQuery({
    queryKey: ['batch-analytics', batchId],
    queryFn: () => analyticsApi.getBatch(batchId as string),
    enabled: isAuthenticated && !!batchId,
  });

  const { data: leaderboardData } = useQuery({
    queryKey: ['batch-leaderboard', batchId],
    queryFn: () => batchesApi.getLeaderboard(batchId as string),
    enabled: isAuthenticated && !!batchId,
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

  if (error || !batchData) {
    return (
      <OrgLayout>
        <div className="text-center py-12">
          <p className="text-red-400">Failed to load batch</p>
          <button
            onClick={() => router.back()}
            className="mt-4 text-blue-400 hover:underline"
          >
            Go Back
          </button>
        </div>
      </OrgLayout>
    );
  }

  const batch = batchData.batch || batchData;
  const stats = batchData.stats || analyticsData?.stats || {};

  return (
    <OrgLayout title={batch.name} subtitle="Batch Dashboard">
      {/* Back Link & Status */}
      <div className="flex items-center justify-between mb-8">
        <Link
          href={`/org/${orgId}/batches`}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Batches
        </Link>
        <span className={`text-xs px-2 py-1 rounded-full border ${statusColors[batch.status]}`}>
          {batch.status}
        </span>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <QuickActionCard
          href={`/org/${orgId}/batches/${batchId}/members`}
          icon={Users}
          label="Members"
          description="View and manage members"
        />
        <QuickActionCard
          href={`/org/${orgId}/batches/${batchId}/curriculum`}
          icon={BookOpen}
          label="Curriculum"
          description="Assign courses"
        />
        <QuickActionCard
          href={`/org/${orgId}/invitations`}
          icon={UserPlus}
          label="Invite"
          description="Add new members"
        />
      </div>

      {/* Stats Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Users}
          label="Members"
          value={stats.total_members || 0}
          subValue={`${stats.active_members || 0} active`}
          color="text-blue-400"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Progress"
          value={`${Math.round(stats.avg_progress || 0)}%`}
          subValue="across all courses"
          color="text-green-400"
        />
        <StatCard
          icon={Award}
          label="Courses Completed"
          value={stats.courses_completed || 0}
          subValue="total completions"
          color="text-purple-400"
        />
        <StatCard
          icon={Target}
          label="Labs Completed"
          value={stats.labs_completed || 0}
          subValue="hands-on practice"
          color="text-orange-400"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Batch Info */}
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Batch Details</h2>
          <div className="space-y-4">
            {batch.description && (
              <div>
                <p className="text-sm text-gray-500 mb-1">Description</p>
                <p className="text-gray-300">{batch.description}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                  <Users className="w-3 h-3" /> Capacity
                </p>
                <p className="text-gray-300">{stats.total_members || 0} / {batch.max_users}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                  <BookOpen className="w-3 h-3" /> Courses
                </p>
                <p className="text-gray-300">{batch.curriculum_courses?.length || 0} assigned</p>
              </div>
              {batch.start_date && (
                <div>
                  <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> Start Date
                  </p>
                  <p className="text-gray-300">{new Date(batch.start_date).toLocaleDateString()}</p>
                </div>
              )}
              {batch.end_date && (
                <div>
                  <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> End Date
                  </p>
                  <p className="text-gray-300">{new Date(batch.end_date).toLocaleDateString()}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Leaderboard */}
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Top Performers</h2>
            <Link
              href={`/org/${orgId}/batches/${batchId}/members`}
              className="text-sm text-blue-400 hover:underline"
            >
              View All
            </Link>
          </div>
          {leaderboardData?.items?.length > 0 ? (
            <div className="space-y-3">
              {leaderboardData.items.slice(0, 5).map((member: any, i: number) => (
                <div
                  key={member.user_id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-blue-500/5"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    i === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                    i === 1 ? 'bg-gray-400/20 text-gray-300' :
                    i === 2 ? 'bg-orange-500/20 text-orange-400' :
                    'bg-[#0a0a0f] text-gray-400'
                  }`}>
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">
                      {member.user?.full_name || member.user?.email || 'Unknown'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {member.courses_completed?.length || 0} courses, {member.labs_completed?.length || 0} labs
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-blue-400 font-semibold">{Math.round(member.progress_percent || 0)}%</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Award className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No progress data yet</p>
            </div>
          )}
        </div>
      </div>
    </OrgLayout>
  );
}

function QuickActionCard({
  href,
  icon: Icon,
  label,
  description,
}: {
  href: string;
  icon: any;
  label: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-4 hover:border-blue-500/40 transition-colors group"
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
          <Icon className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h3 className="text-white font-medium group-hover:text-blue-400 transition-colors">
            {label}
          </h3>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
      </div>
    </Link>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  color,
}: {
  icon: any;
  label: string;
  value: number | string;
  subValue: string;
  color: string;
}) {
  return (
    <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg bg-[#0a0a0f] flex items-center justify-center">
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{subValue}</p>
    </div>
  );
}
