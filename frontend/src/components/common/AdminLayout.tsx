import { ReactNode, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  Shield,
  Building2,
  Users,
  Gauge,
  BarChart3,
  Settings,
  LogOut,
  User,
  Monitor,
  Mail,
  Layers,
  FolderKanban,
  LayoutDashboard
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

interface AdminLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

const adminNavItems = [
  { href: '/admin/organizations', icon: Building2, label: 'Organizations' },
  { href: '/admin/limits', icon: Gauge, label: 'System Limits' },
];

export default function AdminLayout({ children, title, subtitle }: AdminLayoutProps) {
  const router = useRouter();
  const { user, isAuthenticated, logout, hasHydrated } = useAuthStore();

  // Get orgId from route for organization detail pages
  const orgId = router.query.orgId as string | undefined;
  const isOrgDetailPage = router.pathname.startsWith('/admin/organizations/[orgId]');

  // Check if user is admin - must be computed before hooks
  const userRole = user?.role?.toLowerCase();
  const isAdmin = userRole === 'super_admin' || userRole === 'admin';

  // Organization detail nav items (shown when viewing an org)
  const orgDetailNavItems = orgId ? [
    { href: `/admin/organizations/${orgId}`, icon: LayoutDashboard, label: 'Overview', exact: true },
    { href: `/admin/organizations/${orgId}/members`, icon: Users, label: 'Members' },
    { href: `/admin/organizations/${orgId}/batches`, icon: FolderKanban, label: 'Batches' },
    { href: `/admin/organizations/${orgId}/invitations`, icon: Mail, label: 'Invitations' },
    { href: `/admin/organizations/${orgId}/limits`, icon: Gauge, label: 'Limits' },
  ] : [];

  // ALL HOOKS MUST BE CALLED BEFORE ANY EARLY RETURNS (React Rules of Hooks)
  // Redirect non-admins (only after hydration)
  useEffect(() => {
    if (hasHydrated && isAuthenticated && !isAdmin) {
      router.push('/dashboard');
    }
  }, [hasHydrated, isAuthenticated, isAdmin, router]);

  // NOW we can have early returns (after all hooks are called)
  // Wait for router to be ready with orgId on detail pages
  if (isOrgDetailPage && !orgId) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="min-h-screen bg-cyber-darker flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">Access Denied</h1>
          <p className="text-gray-400 mb-4">You need admin privileges to access this page.</p>
          <Link href="/dashboard" className="text-cyber-accent hover:underline">
            Go to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#0a0a0f]">
      {/* Admin Sidebar - Purple theme */}
      <aside className="w-64 bg-[#12121a] border-r border-purple-500/20 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-purple-500/20">
          <Link href="/admin/organizations" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Shield className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <span className="text-lg font-bold text-white">Admin</span>
              <p className="text-xs text-purple-400">Control Panel</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 overflow-y-auto">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-3">
            Management
          </p>
          <ul className="space-y-1">
            {adminNavItems.map((item) => {
              const isActive = router.pathname === item.href || router.pathname.startsWith(item.href + '/');
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                      isActive
                        ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
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

          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mt-6 mb-3 px-3">
            Monitoring
          </p>
          <ul className="space-y-1">
            <li>
              <Link
                href="/admin/performance"
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                  router.pathname === '/admin/performance'
                    ? 'bg-purple-500/20 text-purple-300'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Monitor className="w-5 h-5" />
                <span>Server Performance</span>
              </Link>
            </li>
          </ul>

          {/* Organization detail navigation (shown when viewing an org) */}
          {isOrgDetailPage && orgId && (
            <>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mt-6 mb-3 px-3">
                Organization
              </p>
              <ul className="space-y-1">
                {orgDetailNavItems.map((item) => {
                  const isActive = item.exact
                    ? router.pathname === '/admin/organizations/[orgId]' && router.asPath === item.href
                    : router.pathname.startsWith(item.href.replace(orgId as string, '[orgId]'));
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                          isActive
                            ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
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
            </>
          )}
        </nav>

        {/* Admin User section */}
        <div className="p-4 border-t border-purple-500/20 bg-purple-500/5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
              <User className="w-5 h-5 text-purple-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-white truncate">
                  {user?.username}
                </p>
              </div>
              <p className="text-xs text-purple-400 font-medium">
                {userRole === 'super_admin' ? 'Super Admin' : 'Admin'}
              </p>
            </div>
          </div>
          <button
            onClick={async () => {
              logout();
              // Small delay to ensure state is persisted to localStorage
              await new Promise(resolve => setTimeout(resolve, 50));
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
          <div className="bg-[#12121a] border-b border-purple-500/20 px-8 py-6">
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
