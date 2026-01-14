import { ReactNode, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  Building2,
  Users,
  FolderKanban,
  Mail,
  BarChart3,
  LogOut,
  User,
  ChevronLeft,
  LayoutDashboard
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

interface OrgLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  orgId?: string;
}

export default function OrgLayout({ children, title, subtitle, orgId }: OrgLayoutProps) {
  const router = useRouter();
  const { user, isAuthenticated, logout, hasHydrated } = useAuthStore();
  const routeOrgId = orgId || router.query.orgId as string;

  // Check if user is org admin (owner, admin, or instructor)
  const orgRole = user?.org_role?.toLowerCase();
  const isOrgAdmin = orgRole && ['owner', 'admin', 'instructor'].includes(orgRole);
  const hasOrgAccess = isOrgAdmin && user?.organization_id === routeOrgId;

  // Redirect if no access (only after hydration)
  useEffect(() => {
    if (hasHydrated && isAuthenticated && !hasOrgAccess && routeOrgId) {
      router.push('/dashboard');
    }
  }, [hasHydrated, isAuthenticated, hasOrgAccess, router, routeOrgId]);

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !hasOrgAccess) {
    return (
      <div className="min-h-screen bg-cyber-darker flex items-center justify-center">
        <div className="text-center">
          <Building2 className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">Access Denied</h1>
          <p className="text-gray-400 mb-4">You don't have access to this organization portal.</p>
          <Link href="/dashboard" className="text-blue-400 hover:underline">
            Go to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const orgNavItems = [
    { href: `/org/${routeOrgId}`, icon: LayoutDashboard, label: 'Dashboard', exact: true },
    { href: `/org/${routeOrgId}/members`, icon: Users, label: 'Members' },
    { href: `/org/${routeOrgId}/batches`, icon: FolderKanban, label: 'Batches' },
    { href: `/org/${routeOrgId}/invitations`, icon: Mail, label: 'Invitations' },
    { href: `/org/${routeOrgId}/analytics`, icon: BarChart3, label: 'Analytics' },
  ];

  const roleLabel = orgRole === 'owner' ? 'Owner' : orgRole === 'admin' ? 'Admin' : 'Instructor';

  return (
    <div className="flex h-screen bg-[#0a0a0f]">
      {/* Org Sidebar - Blue theme */}
      <aside className="w-64 bg-[#0d1520] border-r border-blue-500/20 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-blue-500/20">
          <Link href={`/org/${routeOrgId}`} className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Building2 className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <span className="text-lg font-bold text-white">Organization</span>
              <p className="text-xs text-blue-400">Management Portal</p>
            </div>
          </Link>
        </div>

        {/* Back to Learning */}
        <div className="p-4 border-b border-blue-500/10">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Back to Learning
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 overflow-y-auto">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-3">
            Management
          </p>
          <ul className="space-y-1">
            {orgNavItems.map((item) => {
              const isActive = item.exact
                ? router.pathname === `/org/[orgId]` && router.asPath === item.href
                : router.pathname.startsWith(item.href.replace(routeOrgId, '[orgId]'));
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                      isActive
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-blue-500/20 bg-blue-500/5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
              <User className="w-5 h-5 text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-white truncate">
                  {user?.username}
                </p>
              </div>
              <p className="text-xs text-blue-400 font-medium">
                {roleLabel}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              logout();
              router.push('/');
            }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {/* Top header bar */}
        {(title || subtitle) && (
          <div className="bg-[#0d1520] border-b border-blue-500/20 px-8 py-6">
            {title && <h1 className="text-2xl font-bold text-white">{title}</h1>}
            {subtitle && <p className="text-gray-400 mt-1">{subtitle}</p>}
          </div>
        )}
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
