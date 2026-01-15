import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Users,
  FolderKanban,
  Mail,
  BarChart3,
  TrendingUp,
  Award,
  ArrowRight,
  Activity,
  Clock
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi } from '@/services/api';

interface OrgStats {
  total_members: number;
  total_batches: number;
  active_batches: number;
  pending_invitations: number;
  avg_progress: number;
  total_completions: number;
}

interface RecentActivity {
  id: string;
  type: string;
  description: string;
  timestamp: string;
}

export default function PortalDashboard() {
  const router = useRouter();
  const { orgId } = router.query;
  const { user } = useAuthStore();
  const [stats, setStats] = useState<OrgStats | null>(null);
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (orgId) {
      fetchDashboardData();
    }
  }, [orgId]);

  const fetchDashboardData = async () => {
    if (typeof orgId !== 'string') return;

    try {
      // Fetch organization dashboard data
      const dashboardData = await organizationsApi.getDashboard(orgId);
      setStats({
        total_members: dashboardData.total_members || 0,
        total_batches: dashboardData.total_batches || 0,
        active_batches: dashboardData.active_batches || 0,
        pending_invitations: dashboardData.pending_invitations || 0,
        avg_progress: dashboardData.avg_progress || 0,
        total_completions: dashboardData.total_completions || 0
      });
    } catch (error) {
      // Use fallback data if API not available
      setStats({
        total_members: 0,
        total_batches: 0,
        active_batches: 0,
        pending_invitations: 0,
        avg_progress: 0,
        total_completions: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      label: 'Total Members',
      value: stats?.total_members || 0,
      icon: Users,
      color: 'green',
      href: `/portal/${orgId}/members`
    },
    {
      label: 'Active Batches',
      value: stats?.active_batches || 0,
      icon: FolderKanban,
      color: 'blue',
      href: `/portal/${orgId}/batches`
    },
    {
      label: 'Avg Progress',
      value: `${stats?.avg_progress || 0}%`,
      icon: TrendingUp,
      color: 'purple',
      href: `/portal/${orgId}/analytics`
    },
    {
      label: 'Completions',
      value: stats?.total_completions || 0,
      icon: Award,
      color: 'yellow',
      href: `/portal/${orgId}/analytics`
    }
  ];

  const quickActions = [
    { label: 'Manage Members', icon: Users, href: `/portal/${orgId}/members` },
    { label: 'View Batches', icon: FolderKanban, href: `/portal/${orgId}/batches` },
    { label: 'Send Invitations', icon: Mail, href: `/portal/${orgId}/invitations` },
    { label: 'View Analytics', icon: BarChart3, href: `/portal/${orgId}/analytics` }
  ];

  const getColorClass = (color: string) => {
    const colors: Record<string, string> = {
      green: 'bg-cyber-accent/20 text-cyber-accent border-cyber-accent/30',
      blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    };
    return colors[color] || colors.green;
  };

  return (
    <PortalLayout title="Dashboard" subtitle="Organization overview and management">
      {/* Welcome Banner */}
      <div className="mb-8 p-6 rounded-xl bg-gradient-to-r from-cyber-accent/20 to-cyber-accent/10 border border-cyber-accent/20">
        <h2 className="text-xl font-bold text-white mb-2">
          Welcome back, {user?.username}!
        </h2>
        <p className="text-gray-400">
          Manage your organization members, batches, and track learning progress.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => (
          <Link
            key={card.label}
            href={card.href}
            className={`p-6 rounded-xl bg-cyber-dark border border-cyber-accent/20 hover:border-cyber-accent/40 transition-all group`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-lg ${getColorClass(card.color)}`}>
                <card.icon className="w-6 h-6" />
              </div>
              <ArrowRight className="w-5 h-5 text-gray-600 group-hover:text-cyber-accent transition-colors" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">{card.value}</p>
            <p className="text-sm text-gray-400">{card.label}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Quick Actions */}
        <div className="lg:col-span-2">
          <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-4">
            {quickActions.map((action) => (
              <Link
                key={action.label}
                href={action.href}
                className="flex items-center gap-4 p-4 rounded-xl bg-cyber-dark border border-cyber-accent/20 hover:border-cyber-accent/40 transition-all group"
              >
                <div className="p-3 rounded-lg bg-cyber-accent/10 group-hover:bg-cyber-accent/20 transition-colors">
                  <action.icon className="w-5 h-5 text-cyber-accent" />
                </div>
                <span className="text-white font-medium">{action.label}</span>
              </Link>
            ))}
          </div>

          {/* Recent Activity */}
          <h3 className="text-lg font-semibold text-white mt-8 mb-4">Recent Activity</h3>
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            {activities.length > 0 ? (
              <ul className="space-y-4">
                {activities.map((activity) => (
                  <li key={activity.id} className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-cyber-accent/10">
                      <Activity className="w-4 h-4 text-cyber-accent" />
                    </div>
                    <div className="flex-1">
                      <p className="text-white text-sm">{activity.description}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {activity.timestamp}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-center py-8">
                <Activity className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No recent activity</p>
                <p className="text-sm text-gray-500 mt-1">
                  Activity will appear here as members engage with courses
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Organization Info */}
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">Organization</h3>
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="space-y-4">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Name</p>
                <p className="text-white font-medium mt-1">
                  {user?.organization_id ? 'CyyberAIx Academy' : 'Organization'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Your Role</p>
                <p className="text-cyber-accent font-medium mt-1 capitalize">
                  {user?.org_role || 'Member'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Members</p>
                <p className="text-white font-medium mt-1">
                  {stats?.total_members || 0} members
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Active Batches</p>
                <p className="text-white font-medium mt-1">
                  {stats?.active_batches || 0} of {stats?.total_batches || 0}
                </p>
              </div>
            </div>
            <Link
              href={`/portal/${orgId}/settings`}
              className="mt-6 w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-cyber-accent/30 text-cyber-accent hover:bg-cyber-accent/10 transition-colors text-sm"
            >
              Organization Settings
            </Link>
          </div>
        </div>
      </div>
    </PortalLayout>
  );
}
