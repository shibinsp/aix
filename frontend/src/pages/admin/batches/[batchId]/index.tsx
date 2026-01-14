import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import {
  FolderKanban, Users, BookOpen, TrendingUp, ArrowLeft, Loader2,
  Calendar, Settings, UserPlus, Clock, Award, Target
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { batchesApi, analyticsApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';
import Link from 'next/link';

interface BatchDashboard {
  batch: {
    id: string;
    name: string;
    description?: string;
    status: string;
    start_date?: string;
    end_date?: string;
    max_users: number;
    organization_id: string;
    organization?: {
      id: string;
      name: string;
    };
    curriculum_courses: string[];
    created_at: string;
  };
  stats: {
    total_members: number;
    active_members: number;
    avg_progress: number;
    courses_completed: number;
    labs_completed: number;
  };
}

const statusColors: Record<string, string> = {
  active: 'bg-green-500/20 text-green-400 border-green-500/30',
  inactive: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  archived: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
};

export default function BatchDashboard() {
  const router = useRouter();
  const { batchId } = router.query;
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

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

  if (!isAuthenticated) return null;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  if (error || !batchData) {
    return (
      <div className="p-8">
        <div className="text-center py-12">
          <p className="text-red-400">Failed to load batch</p>
          <button
            onClick={() => router.back()}
            className="mt-4 text-cyber-accent hover:underline"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const batch = batchData.batch || batchData;
  const stats = batchData.stats || analyticsData?.stats || {};

  return (
    <AdminLayout title={batch.name} subtitle={batch.organization?.name || 'Batch Dashboard'}>
      {/* Header Actions */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColors[batch.status]}`}>
            {batch.status}
          </span>
        </div>
        <Link
          href={`/admin/batches/${batchId}/curriculum`}
          className="flex items-center gap-2 px-4 py-2 border border-purple-500/30 text-gray-300 rounded-lg hover:bg-purple-500/10 transition-colors"
        >
          <BookOpen className="w-4 h-4" />
          Curriculum
        </Link>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <QuickActionCard
          href={`/admin/batches/${batchId}/members`}
          icon={Users}
          label="Members"
          description="View and manage batch members"
        />
        <QuickActionCard
          href={`/admin/batches/${batchId}/curriculum`}
          icon={BookOpen}
          label="Curriculum"
          description="Assign courses to batch"
        />
        <QuickActionCard
          href={`/admin/organizations/${batch.organization_id}/invitations`}
          icon={UserPlus}
          label="Invite"
          description="Send invitations"
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
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
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
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Top Performers</h2>
            <Link
              href={`/admin/batches/${batchId}/members`}
              className="text-sm text-cyber-accent hover:underline"
            >
              View All
            </Link>
          </div>
          {leaderboardData?.items?.length > 0 ? (
            <div className="space-y-3">
              {leaderboardData.items.slice(0, 5).map((member: any, i: number) => (
                <div
                  key={member.user_id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-cyber-darker/50"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    i === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                    i === 1 ? 'bg-gray-400/20 text-gray-300' :
                    i === 2 ? 'bg-orange-500/20 text-orange-400' :
                    'bg-cyber-darker text-gray-400'
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
                    <p className="text-cyber-accent font-semibold">{Math.round(member.progress_percent || 0)}%</p>
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
    </AdminLayout>
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
      className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-4 hover:border-cyber-accent/40 transition-colors group"
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-cyber-accent/10 flex items-center justify-center group-hover:bg-cyber-accent/20 transition-colors">
          <Icon className="w-5 h-5 text-cyber-accent" />
        </div>
        <div>
          <h3 className="text-white font-medium group-hover:text-cyber-accent transition-colors">
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
    <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg bg-cyber-darker flex items-center justify-center">
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{subValue}</p>
    </div>
  );
}
