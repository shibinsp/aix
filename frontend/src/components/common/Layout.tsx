import { ReactNode, useState, useEffect } from 'react';
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
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Map,
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
  { href: '/learning-path', icon: Map, label: 'Learning Path' },
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('sidebar-collapsed');
    if (saved) setSidebarCollapsed(JSON.parse(saved));
  }, []);

  const toggleSidebar = () => {
    const newState = !sidebarCollapsed;
    setSidebarCollapsed(newState);
    localStorage.setItem('sidebar-collapsed', JSON.stringify(newState));
  };

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
      <aside className={`${sidebarCollapsed ? 'w-20' : 'w-64'} bg-cyber-dark border-r border-cyber-accent/20 flex flex-col transition-all duration-300`}>
        {/* Logo */}
        <div className={`${sidebarCollapsed ? 'p-4' : 'p-6'} border-b border-cyber-accent/20`}>
          <div className="flex items-center justify-between">
            <Link href="/" className={`flex items-center ${sidebarCollapsed ? 'justify-center w-full' : 'gap-3'}`}>
              <Shield className="w-8 h-8 text-cyber-accent flex-shrink-0" />
              {!sidebarCollapsed && (
                <span className="text-xl font-bold text-white">
                  Cyber<span className="text-cyber-accent">AIx</span>
                </span>
              )}
            </Link>
            {!sidebarCollapsed && (
              <button
                onClick={toggleSidebar}
                className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                title="Collapse sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}
          </div>
          {sidebarCollapsed && (
            <button
              onClick={toggleSidebar}
              className="w-full mt-3 p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center justify-center"
              title="Expand sidebar"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
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
                    className={`flex items-center ${sidebarCollapsed ? 'justify-center px-3' : 'gap-3 px-4'} py-3 rounded-lg transition-all ${
                      isActive
                        ? 'bg-cyber-accent/20 text-cyber-accent cyber-border'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                    title={sidebarCollapsed ? item.label : undefined}
                  >
                    <item.icon className="w-5 h-5 flex-shrink-0" />
                    {!sidebarCollapsed && <span>{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>

          {/* Admin Section */}
          {isAdmin && (
            <>
              {!sidebarCollapsed && (
                <div className="mt-6 mb-2 px-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Admin</p>
                </div>
              )}
              {sidebarCollapsed && <div className="mt-4 border-t border-gray-700/50" />}
              <ul className="space-y-2 mt-2">
                {adminNavItems.map((item) => {
                  const isActive = router.pathname === item.href || router.pathname.startsWith(item.href + '/');
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={`flex items-center ${sidebarCollapsed ? 'justify-center px-3' : 'gap-3 px-4'} py-3 rounded-lg transition-all ${
                          isActive
                            ? 'bg-cyber-accent/20 text-cyber-accent cyber-border'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                        }`}
                        title={sidebarCollapsed ? item.label : undefined}
                      >
                        <item.icon className="w-5 h-5 flex-shrink-0" />
                        {!sidebarCollapsed && <span>{item.label}</span>}
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
              {!sidebarCollapsed && (
                <div className="mt-6 mb-2 px-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Organization</p>
                </div>
              )}
              {sidebarCollapsed && <div className="mt-4 border-t border-gray-700/50" />}
              <ul className="space-y-2 mt-2">
                <li>
                  <Link
                    href={`/org/${user.organization_id}`}
                    className={`flex items-center ${sidebarCollapsed ? 'justify-center px-3' : 'gap-3 px-4'} py-3 rounded-lg transition-all ${
                      router.pathname.startsWith('/org/')
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                    title={sidebarCollapsed ? 'My Organization' : undefined}
                  >
                    <Building2 className="w-5 h-5 flex-shrink-0" />
                    {!sidebarCollapsed && <span>My Organization</span>}
                  </Link>
                </li>
              </ul>
            </>
          )}
        </nav>

        {/* User section */}
        {isAuthenticated && user && (
          <div className={`${sidebarCollapsed ? 'p-2' : 'p-4'} border-t border-cyber-accent/20`}>
            {sidebarCollapsed ? (
              // Collapsed: just avatar and vertical icons
              <div className="flex flex-col items-center gap-2">
                <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center" title={user.username}>
                  <User className="w-5 h-5 text-cyber-accent" />
                </div>
                <Link
                  href="/settings"
                  className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
                  title="Settings"
                >
                  <Settings className="w-4 h-4" />
                </Link>
                <button
                  onClick={async () => {
                    logout();
                    await new Promise(resolve => setTimeout(resolve, 50));
                    router.push('/');
                  }}
                  className="p-2 text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              // Expanded: full user info
              <>
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
                      await new Promise(resolve => setTimeout(resolve, 50));
                      router.push('/');
                    }}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </>
            )}
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
