import { useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  Trophy,
  Flame,
  Target,
  BookOpen,
  Terminal,
  ArrowRight,
  TrendingUp
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { usersApi, skillsApi, coursesApi, labsApi } from '@/services/api';

export default function Dashboard() {
  const router = useRouter();
  const { user, isAuthenticated, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    } else if (user) {
      // Redirect admin users to admin panel
      const userRole = user.role?.toLowerCase();
      if (userRole === 'super_admin' || userRole === 'admin') {
        router.replace('/admin/organizations');
      }
    }
  }, [hasHydrated, isAuthenticated, user, router]);

  const { data: stats } = useQuery({
    queryKey: ['userStats'],
    queryFn: usersApi.getStats,
    enabled: isAuthenticated,
  });

  const { data: skills } = useQuery({
    queryKey: ['userSkills'],
    queryFn: skillsApi.getMySkills,
    enabled: isAuthenticated,
  });

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations'],
    queryFn: skillsApi.getRecommendations,
    enabled: isAuthenticated,
  });

  const { data: courses } = useQuery({
    queryKey: ['courses'],
    queryFn: () => coursesApi.list({ limit: 4 }),
    enabled: isAuthenticated,
  });

  const { data: labs } = useQuery({
    queryKey: ['labs'],
    queryFn: () => labsApi.list({ limit: 4 }),
    enabled: isAuthenticated,
  });

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  return (
    <div className="p-8">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">
          Welcome back, <span className="text-cyber-accent">{user.username}</span>
        </h1>
        <p className="text-gray-400">
          Continue your cybersecurity journey. You're on a {stats?.current_streak || 0} day streak!
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Trophy}
          label="Total Points"
          value={stats?.total_points || 0}
          color="text-yellow-400"
        />
        <StatCard
          icon={Flame}
          label="Day Streak"
          value={stats?.current_streak || 0}
          color="text-orange-400"
        />
        <StatCard
          icon={BookOpen}
          label="Courses Completed"
          value={stats?.courses_completed || 0}
          color="text-blue-400"
        />
        <StatCard
          icon={Terminal}
          label="Labs Completed"
          value={stats?.labs_completed || 0}
          color="text-green-400"
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Quick Actions */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-4">
              <Link
                href="/chat"
                className="flex items-center gap-3 p-4 bg-cyber-darker rounded-lg border border-gray-700 hover:border-cyber-accent/50 transition-colors group"
              >
                <div className="w-10 h-10 rounded-lg bg-cyber-accent/20 flex items-center justify-center">
                  <Target className="w-5 h-5 text-cyber-accent" />
                </div>
                <div>
                  <h3 className="font-medium text-white group-hover:text-cyber-accent transition-colors">
                    Ask Alphha Tutor
                  </h3>
                  <p className="text-sm text-gray-400">Get help instantly</p>
                </div>
              </Link>
              <Link
                href="/labs"
                className="flex items-center gap-3 p-4 bg-cyber-darker rounded-lg border border-gray-700 hover:border-cyber-accent/50 transition-colors group"
              >
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <Terminal className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h3 className="font-medium text-white group-hover:text-cyber-accent transition-colors">
                    Start a Lab
                  </h3>
                  <p className="text-sm text-gray-400">Practice hands-on</p>
                </div>
              </Link>
            </div>
          </div>

          {/* Recommended Courses */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Continue Learning</h2>
              <Link href="/courses" className="text-cyber-accent text-sm hover:underline flex items-center gap-1">
                View all <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="space-y-4">
              {courses?.slice(0, 3).map((course: any) => (
                <CourseCard key={course.id} course={course} />
              ))}
              {(!courses || courses.length === 0) && (
                <p className="text-gray-400 text-center py-4">No courses available yet</p>
              )}
            </div>
          </div>

          {/* Available Labs */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Practice Labs</h2>
              <Link href="/labs" className="text-cyber-accent text-sm hover:underline flex items-center gap-1">
                View all <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {labs?.slice(0, 4).map((lab: any) => (
                <LabCard key={lab.id} lab={lab} />
              ))}
              {(!labs || labs.length === 0) && (
                <p className="text-gray-400 text-center py-4 col-span-2">No labs available yet</p>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Skill Progress */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Your Skills</h2>
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Overall Level</span>
                <span className="text-cyber-accent font-medium">
                  {skills?.overall_level || 'Novice'}
                </span>
              </div>
              <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
                <div
                  className="h-full bg-cyber-accent rounded-full"
                  style={{ width: `${((skills?.overall_proficiency || 0) / 5) * 100}%` }}
                />
              </div>
            </div>
            <Link
              href="/skills"
              className="block text-center text-sm text-cyber-accent hover:underline"
            >
              View all skills
            </Link>
          </div>

          {/* Recommendations */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">
              <TrendingUp className="inline w-5 h-5 mr-2 text-cyber-accent" />
              Focus Areas
            </h2>
            <div className="space-y-3">
              {recommendations?.recommendations?.slice(0, 5).map((rec: any) => (
                <div key={rec.skill} className="flex items-center justify-between">
                  <span className="text-gray-300 text-sm">{rec.skill.replace(/_/g, ' ')}</span>
                  <span className={`text-xs px-2 py-1 rounded ${rec.recommended_focus ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                    {rec.recommended_focus ? 'Priority' : 'Improve'}
                  </span>
                </div>
              ))}
              {(!recommendations?.recommendations || recommendations.recommendations.length === 0) && (
                <p className="text-gray-400 text-sm">Complete some assessments to get recommendations</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) {
  return (
    <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-lg bg-cyber-darker flex items-center justify-center ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <p className="text-gray-400 text-sm">{label}</p>
          <p className="text-2xl font-bold text-white">{value.toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}

function CourseCard({ course }: { course: any }) {
  return (
    <Link
      href={`/courses/${course.id}`}
      className="flex items-center gap-4 p-4 bg-cyber-darker rounded-lg hover:bg-cyber-darker/80 transition-colors"
    >
      <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
        <BookOpen className="w-6 h-6 text-blue-400" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-white truncate">{course.title}</h3>
        <p className="text-sm text-gray-400">
          {course.difficulty} • {course.estimated_hours}h
        </p>
      </div>
      <ArrowRight className="w-5 h-5 text-gray-500" />
    </Link>
  );
}

function LabCard({ lab }: { lab: any }) {
  return (
    <Link
      href={`/labs/${lab.id}`}
      className="p-4 bg-cyber-darker rounded-lg hover:bg-cyber-darker/80 transition-colors"
    >
      <div className="flex items-center gap-2 mb-2">
        <Terminal className="w-4 h-4 text-green-400" />
        <span className={`text-xs px-2 py-0.5 rounded ${
          lab.difficulty === 'beginner' ? 'bg-green-500/20 text-green-400' :
          lab.difficulty === 'intermediate' ? 'bg-yellow-500/20 text-yellow-400' :
          'bg-red-500/20 text-red-400'
        }`}>
          {lab.difficulty}
        </span>
      </div>
      <h3 className="font-medium text-white text-sm truncate">{lab.title}</h3>
      <p className="text-xs text-gray-400 mt-1">{lab.estimated_time} min</p>
    </Link>
  );
}
