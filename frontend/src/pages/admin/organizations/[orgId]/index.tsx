import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import {
  Building2, Users, BookOpen, Clock, TrendingUp, Settings,
  ArrowLeft, Calendar, Mail, Globe, Shield, Loader2,
  UserPlus, FolderKanban, Gauge, Send
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi, analyticsApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';
import Link from 'next/link';

interface OrgDashboard {
  organization: {
    id: string;
    name: string;
    slug: string;
    org_type: string;
    description?: string;
    is_active: boolean;
    contact_email?: string;
    logo_url?: string;
    subscription_tier?: string;
    created_at: string;
  };
  stats: {
    total_members: number;
    active_members: number;
    total_batches: number;
    active_batches: number;
    total_courses_completed: number;
    total_labs_completed: number;
    avg_progress: number;
  };
}

const orgTypeLabels: Record<string, string> = {
  enterprise: 'Enterprise',
  educational: 'Educational',
  government: 'Government',
  non_profit: 'Non-Profit',
};

const orgTypeColors: Record<string, string> = {
  enterprise: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  educational: 'bg-green-500/20 text-green-400 border-green-500/30',
  government: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  non_profit: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
};

export default function OrganizationDashboard() {
  const router = useRouter();
  const { orgId } = router.query;
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const { data: dashboardData, isLoading, error } = useQuery({
    queryKey: ['organization-dashboard', orgId],
    queryFn: () => organizationsApi.getDashboard(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  const { data: analyticsData } = useQuery({
    queryKey: ['organization-analytics', orgId],
    queryFn: () => analyticsApi.getOrg(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  if (!isAuthenticated) return null;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  if (error || !dashboardData) {
    return (
      <div className="p-8">
        <div className="text-center py-12">
          <p className="text-red-400">Failed to load organization</p>
          <button
            onClick={() => router.push('/admin/organizations')}
            className="mt-4 text-cyber-accent hover:underline"
          >
            Back to Organizations
          </button>
        </div>
      </div>
    );
  }

  const { organization: org, stats } = dashboardData;

  return (
    <AdminLayout title={org.name} subtitle="Organization Dashboard">
      {/* Header Actions */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full border ${orgTypeColors[org.org_type] || 'bg-gray-500/20 text-gray-400'}`}>
            {orgTypeLabels[org.org_type] || org.org_type}
          </span>
          {org.subscription_tier && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
              {org.subscription_tier}
            </span>
          )}
          {!org.is_active && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400">
              Inactive
            </span>
          )}
        </div>
        <Link
          href={`/admin/organizations/${orgId}/limits`}
          className="flex items-center gap-2 px-4 py-2 border border-purple-500/30 text-gray-300 rounded-lg hover:bg-purple-500/10 transition-colors"
        >
          <Settings className="w-4 h-4" />
          Limits
        </Link>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <QuickActionCard
          href={`/admin/organizations/${orgId}/members`}
          icon={Users}
          label="Members"
          description="Manage organization members"
        />
        <QuickActionCard
          href={`/admin/organizations/${orgId}/batches`}
          icon={FolderKanban}
          label="Batches"
          description="Manage learning batches"
        />
        <QuickActionCard
          href={`/admin/organizations/${orgId}/invitations`}
          icon={Send}
          label="Invitations"
          description="Send and manage invites"
        />
        <QuickActionCard
          href={`/admin/organizations/${orgId}/limits`}
          icon={Gauge}
          label="Resource Limits"
          description="Configure usage limits"
        />
      </div>

      {/* Stats Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Users}
          label="Total Members"
          value={stats?.total_members || 0}
          subValue={`${stats?.active_members || 0} active`}
          color="text-blue-400"
        />
        <StatCard
          icon={FolderKanban}
          label="Batches"
          value={stats?.total_batches || 0}
          subValue={`${stats?.active_batches || 0} active`}
          color="text-green-400"
        />
        <StatCard
          icon={BookOpen}
          label="Courses Completed"
          value={stats?.total_courses_completed || 0}
          subValue={`${stats?.total_labs_completed || 0} labs`}
          color="text-purple-400"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Progress"
          value={`${Math.round(stats?.avg_progress || 0)}%`}
          subValue="across all members"
          color="text-cyber-accent"
        />
      </div>

      {/* Organization Details */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Info Card */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Organization Details</h2>
          <div className="space-y-4">
            {org.description && (
              <div>
                <p className="text-sm text-gray-500 mb-1">Description</p>
                <p className="text-gray-300">{org.description}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                  <Globe className="w-3 h-3" /> Slug
                </p>
                <p className="text-gray-300 font-mono text-sm">{org.slug}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                  <Mail className="w-3 h-3" /> Contact
                </p>
                <p className="text-gray-300 text-sm">{org.contact_email || 'Not set'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                  <Shield className="w-3 h-3" /> Type
                </p>
                <p className="text-gray-300">{orgTypeLabels[org.org_type] || org.org_type}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3" /> Created
                </p>
                <p className="text-gray-300">{new Date(org.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
          {analyticsData?.recent_activity?.length > 0 ? (
            <div className="space-y-3">
              {analyticsData.recent_activity.slice(0, 5).map((activity: any, i: number) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-cyber-darker/50">
                  <div className="w-8 h-8 rounded-full bg-cyber-accent/20 flex items-center justify-center">
                    <Clock className="w-4 h-4 text-cyber-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300 truncate">{activity.description}</p>
                    <p className="text-xs text-gray-500">{activity.user_name}</p>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(activity.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Clock className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No recent activity</p>
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
        <div className={`w-10 h-10 rounded-lg bg-cyber-darker flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{subValue}</p>
    </div>
  );
}
