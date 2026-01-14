import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Users, FolderKanban, TrendingUp, Award, Target, Mail,
  Loader2, BookOpen, UserPlus
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi, analyticsApi } from '@/services/api';
import OrgLayout from '@/components/common/OrgLayout';

export default function OrgDashboard() {
  const router = useRouter();
  const { orgId } = router.query;
  const { isAuthenticated, user } = useAuthStore();

  const { data: orgData, isLoading: orgLoading } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsApi.get(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  const { data: analyticsData, isLoading: analyticsLoading } = useQuery({
    queryKey: ['organization-analytics', orgId],
    queryFn: () => analyticsApi.getOrg(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  if (orgLoading || analyticsLoading) {
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

  return (
    <OrgLayout title="Dashboard" subtitle={org?.name || 'Organization Overview'}>
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-xl border border-blue-500/30 p-6 mb-8">
        <h2 className="text-xl font-bold text-white mb-2">
          Welcome back, <span className="text-blue-400">{user?.username}</span>
        </h2>
        <p className="text-gray-400">
          Manage your organization's members, batches, and track learning progress.
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <QuickActionCard
          href={`/org/${orgId}/members`}
          icon={Users}
          label="Members"
          description="View all members"
          color="blue"
        />
        <QuickActionCard
          href={`/org/${orgId}/batches`}
          icon={FolderKanban}
          label="Batches"
          description="Manage groups"
          color="purple"
        />
        <QuickActionCard
          href={`/org/${orgId}/invitations`}
          icon={Mail}
          label="Invitations"
          description="Send invites"
          color="green"
        />
        <QuickActionCard
          href={`/org/${orgId}/analytics`}
          icon={TrendingUp}
          label="Analytics"
          description="View progress"
          color="orange"
        />
      </div>

      {/* Stats Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Users}
          label="Total Members"
          value={stats.total_members || 0}
          subValue={`${stats.active_members || 0} active`}
          color="text-blue-400"
        />
        <StatCard
          icon={FolderKanban}
          label="Batches"
          value={stats.total_batches || 0}
          subValue={`${stats.active_batches || 0} active`}
          color="text-purple-400"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Progress"
          value={`${Math.round(stats.avg_progress || 0)}%`}
          subValue="across all members"
          color="text-green-400"
        />
        <StatCard
          icon={Award}
          label="Completions"
          value={stats.total_completions || 0}
          subValue="courses completed"
          color="text-orange-400"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Organization Details */}
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Organization Details</h2>
          <div className="space-y-4">
            {org?.description && (
              <div>
                <p className="text-sm text-gray-500 mb-1">Description</p>
                <p className="text-gray-300">{org.description}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500 mb-1">Type</p>
                <p className="text-gray-300 capitalize">{org?.org_type || 'Educational'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Status</p>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  org?.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {org?.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Created</p>
                <p className="text-gray-300">
                  {org?.created_at ? new Date(org.created_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Your Role</p>
                <span className="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-400 capitalize">
                  {user?.org_role || 'member'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Quick Stats</h2>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-blue-500/5 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <UserPlus className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-white font-medium">Pending Invitations</p>
                  <p className="text-sm text-gray-500">Awaiting response</p>
                </div>
              </div>
              <span className="text-xl font-bold text-blue-400">{stats.pending_invitations || 0}</span>
            </div>

            <div className="flex items-center justify-between p-3 bg-purple-500/5 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-white font-medium">Total Courses</p>
                  <p className="text-sm text-gray-500">In curriculum</p>
                </div>
              </div>
              <span className="text-xl font-bold text-purple-400">{stats.total_courses || 0}</span>
            </div>

            <div className="flex items-center justify-between p-3 bg-green-500/5 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <Target className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <p className="text-white font-medium">Labs Completed</p>
                  <p className="text-sm text-gray-500">This month</p>
                </div>
              </div>
              <span className="text-xl font-bold text-green-400">{stats.labs_completed_month || 0}</span>
            </div>
          </div>
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
  color,
}: {
  href: string;
  icon: any;
  label: string;
  description: string;
  color: 'blue' | 'purple' | 'green' | 'orange';
}) {
  const colorClasses = {
    blue: 'bg-blue-500/10 group-hover:bg-blue-500/20 text-blue-400',
    purple: 'bg-purple-500/10 group-hover:bg-purple-500/20 text-purple-400',
    green: 'bg-green-500/10 group-hover:bg-green-500/20 text-green-400',
    orange: 'bg-orange-500/10 group-hover:bg-orange-500/20 text-orange-400',
  };

  return (
    <Link
      href={href}
      className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-4 hover:border-blue-500/40 transition-colors group"
    >
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
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
