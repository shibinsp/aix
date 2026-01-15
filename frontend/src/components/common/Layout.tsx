import { ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  Shield,
  MessageSquare,
  BookOpen,
  Terminal,
  BarChart3,
  Settings,
  LogOut,
  User,
  Newspaper,
  Sparkles,
  Monitor,
  Building2,
  Gauge,
  TrendingUp
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { href: '/dashboard', icon: BarChart3, label: 'Dashboard' },
  { href: '/chat', icon: MessageSquare, label: 'Alphha Tutor' },
  { href: '/learning', icon: Sparkles, label: 'Course Creation' },
  { href: '/courses', icon: BookOpen, label: 'Courses' },
  { href: '/labs', icon: Terminal, label: 'Labs' },
  { href: '/environment', icon: Monitor, label: 'My Environment' },
  { href: '/my-progress', icon: TrendingUp, label: 'My Progress' },
  { href: '/skills', icon: Shield, label: 'Skills' },
  { href: '/news', icon: Newspaper, label: 'Cyber News' },
];

const adminNavItems = [
  { href: '/admin/organizations', icon: Building2, label: 'Organizations' },
  { href: '/admin/limits', icon: Gauge, label: 'System Limits' },
];

export default function Layout({ children }: LayoutProps) {
  const router = useRouter();
  const { user, isAuthenticated, logout, hasHydrated } = useAuthStore();

  // Don't show layout on landing page, auth pages, invite pages, admin pages, and portal pages
  const noLayoutPages = ['/', '/login', '/register', '/org-login'];
  const noLayoutPrefixes = ['/invite/', '/admin', '/org', '/portal'];
  if (noLayoutPages.includes(router.pathname) || noLayoutPrefixes.some(p => router.pathname.startsWith(p))) {
    return <>{children}</>;
  }

  // Check if user is admin (super_admin or admin role) - handle both cases
  const userRole = user?.role?.toLowerCase();
  const isAdmin = userRole === 'super_admin' || userRole === 'admin';

  // Check if user is org admin (owner, admin, or instructor in an organization)
  const orgRole = user?.org_role?.toLowerCase();
  const isOrgAdmin = orgRole && ['owner', 'admin', 'instructor'].includes(orgRole) && user?.organization_id;

  return (
    <div className="flex h-screen bg-cyber-darker">
      {/* Sidebar */}
      <aside className="w-64 bg-cyber-dark border-r border-cyber-accent/20 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-cyber-accent/20">
          <Link href="/" className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-cyber-accent" />
            <span className="text-xl font-bold text-white">
              Cyber<span className="text-cyber-accent">AIx</span>
            </span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 overflow-y-auto">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const isActive = router.pathname === item.href || router.pathname.startsWith(item.href + '/');
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
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

          {/* Admin Section */}
          {isAdmin && (
            <>
              <div className="mt-6 mb-2 px-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Admin</p>
              </div>
              <ul className="space-y-2">
                {adminNavItems.map((item) => {
                  const isActive = router.pathname === item.href || router.pathname.startsWith(item.href + '/');
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
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
            </>
          )}

          {/* Organization Section (for org admins who are not system admins) */}
          {isOrgAdmin && !isAdmin && (
            <>
              <div className="mt-6 mb-2 px-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Organization</p>
              </div>
              <ul className="space-y-2">
                <li>
                  <Link
                    href={`/org/${user.organization_id}`}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                      router.pathname.startsWith('/org/')
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    <Building2 className="w-5 h-5" />
                    <span>My Organization</span>
                  </Link>
                </li>
              </ul>
            </>
          )}
        </nav>

        {/* User section */}
        {isAuthenticated && user && (
          <div className="p-4 border-t border-cyber-accent/20">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center">
                <User className="w-5 h-5 text-cyber-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-white truncate">
                    {user.username}
                  </p>
                  {isAdmin && (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase bg-purple-500/20 text-purple-400 rounded">
                      {userRole === 'super_admin' ? 'Super Admin' : 'Admin'}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-400 truncate">
                  {user.skill_level}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Link
                href="/settings"
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
              >
                <Settings className="w-4 h-4" />
              </Link>
              <button
                onClick={async () => {
                  logout();
                  // Small delay to ensure state is persisted to localStorage
                  await new Promise(resolve => setTimeout(resolve, 50));
                  router.push('/');
                }}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
