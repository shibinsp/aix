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
  LayoutDashboard,
  BookOpen,
  Settings,
  Shield
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

interface PortalLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  orgId?: string;
}

export default function PortalLayout({ children, title, subtitle, orgId }: PortalLayoutProps) {
  const router = useRouter();
  const { user, isAuthenticated, logout, hasHydrated } = useAuthStore();
  const routeOrgId = orgId || (router.query.orgId as string);

  // Check if user is org admin (owner, admin, or instructor)
  // These must be computed before hooks to avoid conditional hook calls
  const orgRole = user?.org_role?.toLowerCase();
  const isOrgAdmin = orgRole && ['owner', 'admin', 'instructor'].includes(orgRole);
  const hasOrgAccess = isOrgAdmin && user?.organization_id === routeOrgId;

  // ALL HOOKS MUST BE CALLED BEFORE ANY EARLY RETURNS (React Rules of Hooks)
  // Redirect if no access (only after hydration)
  useEffect(() => {
    if (hasHydrated && isAuthenticated && !hasOrgAccess && routeOrgId) {
      router.push('/dashboard');
    }
  }, [hasHydrated, isAuthenticated, hasOrgAccess, router, routeOrgId]);

  // NOW we can have early returns (after all hooks are called)
  // Wait for router to be ready with orgId
  if (!routeOrgId) {
    return (
      <div className="min-h-screen bg-cyber-darker flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="min-h-screen bg-cyber-darker flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
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
          <Link href="/org-login" className="text-cyber-accent hover:underline">
            Go to Organization Login
          </Link>
        </div>
      </div>
    );
  }

  const portalNavItems = [
    { href: `/portal/${routeOrgId}`, icon: LayoutDashboard, label: 'Dashboard', exact: true },
    { href: `/portal/${routeOrgId}/members`, icon: Users, label: 'Members' },
    { href: `/portal/${routeOrgId}/batches`, icon: FolderKanban, label: 'Batches' },
    { href: `/portal/${routeOrgId}/courses`, icon: BookOpen, label: 'Courses' },
    { href: `/portal/${routeOrgId}/invitations`, icon: Mail, label: 'Invitations' },
    { href: `/portal/${routeOrgId}/analytics`, icon: BarChart3, label: 'Analytics' },
    { href: `/portal/${routeOrgId}/settings`, icon: Settings, label: 'Settings' },
  ];

  const roleLabel = orgRole === 'owner' ? 'Owner' : orgRole === 'admin' ? 'Admin' : 'Instructor';

  return (
    <div className="flex h-screen bg-cyber-darker">
      {/* Portal Sidebar */}
      <aside className="w-64 bg-cyber-dark border-r border-cyber-accent/20 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-cyber-accent/20">
          <Link href={`/portal/${routeOrgId}`} className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-cyber-accent" />
            <span className="text-xl font-bold text-white">
              Cyber<span className="text-cyber-accent">AIx</span>
            </span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 overflow-y-auto">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-3">
            Organization
          </p>
          <ul className="space-y-1">
            {portalNavItems.map((item) => {
              const isActive = item.exact
                ? router.pathname === `/portal/[orgId]` && router.asPath === item.href
                : routeOrgId ? router.pathname.startsWith(item.href.replace(routeOrgId, '[orgId]')) : false;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                      isActive
                        ? 'bg-cyber-accent/20 text-cyber-accent cyber-border'
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
        <div className="p-4 border-t border-cyber-accent/20">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center">
              <User className="w-5 h-5 text-cyber-accent" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-white truncate">
                  {user?.username}
                </p>
              </div>
              <p className="text-xs text-cyber-accent font-medium">
                {roleLabel}
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
          <div className="bg-cyber-dark border-b border-cyber-accent/20 px-8 py-6">
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
