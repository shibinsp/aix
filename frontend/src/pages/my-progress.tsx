import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp, BookOpen, Target, Award, Clock, Calendar,
  Loader2, ChevronRight, Flame, Zap, CheckCircle
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { analyticsApi } from '@/services/api';
import Link from 'next/link';

interface ProgressStats {
  total_courses_enrolled: number;
  total_courses_completed: number;
  total_labs_completed: number;
  total_lessons_completed: number;
  current_streak_days: number;
  longest_streak_days: number;
  total_learning_hours: number;
  this_week_hours: number;
  rank_percentile?: number;
}

interface CourseProgress {
  course_id: string;
  course_title: string;
  course_thumbnail?: string;
  progress_percent: number;
  lessons_completed: number;
  total_lessons: number;
  labs_completed: number;
  total_labs: number;
  last_activity: string;
  is_completed: boolean;
}

interface RecentActivity {
  type: 'lesson_completed' | 'lab_completed' | 'course_completed' | 'skill_earned';
  title: string;
  course_title?: string;
  timestamp: string;
}

export default function MyProgressPage() {
  const router = useRouter();
  const { isAuthenticated, user, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['my-analytics'],
    queryFn: () => analyticsApi.getMy(),
    enabled: isAuthenticated,
  });

  const { data: progressData, isLoading: progressLoading } = useQuery({
    queryKey: ['my-progress'],
    queryFn: () => analyticsApi.getMyProgress(),
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

  if (!isAuthenticated) return null;

  const isLoading = statsLoading || progressLoading;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  const stats: ProgressStats = statsData?.stats || {
    total_courses_enrolled: 0,
    total_courses_completed: 0,
    total_labs_completed: 0,
    total_lessons_completed: 0,
    current_streak_days: 0,
    longest_streak_days: 0,
    total_learning_hours: 0,
    this_week_hours: 0,
  };

  const courseProgress: CourseProgress[] = progressData?.courses || [];
  const recentActivity: RecentActivity[] = statsData?.recent_activity || [];

  const inProgressCourses = courseProgress.filter(c => !c.is_completed);
  const completedCourses = courseProgress.filter(c => c.is_completed);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">My Progress</h1>
        <p className="text-gray-400">Track your learning journey and achievements</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={BookOpen}
          label="Courses"
          value={stats.total_courses_completed}
          subValue={`/ ${stats.total_courses_enrolled} enrolled`}
          color="text-blue-400"
          bgColor="bg-blue-500/20"
        />
        <StatCard
          icon={Target}
          label="Labs Completed"
          value={stats.total_labs_completed}
          subValue="hands-on practice"
          color="text-purple-400"
          bgColor="bg-purple-500/20"
        />
        <StatCard
          icon={Flame}
          label="Current Streak"
          value={stats.current_streak_days}
          subValue={`days (best: ${stats.longest_streak_days})`}
          color="text-orange-400"
          bgColor="bg-orange-500/20"
        />
        <StatCard
          icon={Clock}
          label="Learning Time"
          value={Math.round(stats.total_learning_hours)}
          subValue={`hrs (${Math.round(stats.this_week_hours)} this week)`}
          color="text-green-400"
          bgColor="bg-green-500/20"
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* In Progress Courses */}
        <div className="lg:col-span-2 bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">In Progress</h2>
            <Link
              href="/courses"
              className="text-sm text-cyber-accent hover:underline flex items-center gap-1"
            >
              Browse Courses <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {inProgressCourses.length > 0 ? (
            <div className="space-y-4">
              {inProgressCourses.map(course => (
                <CourseProgressCard key={course.course_id} course={course} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No courses in progress</p>
              <Link
                href="/courses"
                className="inline-block mt-3 text-cyber-accent hover:underline"
              >
                Start learning
              </Link>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>

          {recentActivity.length > 0 ? (
            <div className="space-y-3">
              {recentActivity.slice(0, 8).map((activity, i) => (
                <ActivityItem key={i} activity={activity} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Zap className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No recent activity</p>
            </div>
          )}
        </div>
      </div>

      {/* Completed Courses */}
      {completedCourses.length > 0 && (
        <div className="mt-6 bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            <span className="inline-flex items-center gap-2">
              <Award className="w-5 h-5 text-yellow-400" />
              Completed Courses ({completedCourses.length})
            </span>
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {completedCourses.map(course => (
              <CompletedCourseCard key={course.course_id} course={course} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  color,
  bgColor,
}: {
  icon: any;
  label: string;
  value: number;
  subValue: string;
  color: string;
  bgColor: string;
}) {
  return (
    <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-8 h-8 rounded-lg ${bgColor} flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{subValue}</p>
    </div>
  );
}

function CourseProgressCard({ course }: { course: CourseProgress }) {
  const progress = Math.round(course.progress_percent);

  return (
    <Link
      href={`/courses/${course.course_id}`}
      className="flex items-center gap-4 p-4 bg-cyber-darker rounded-lg hover:bg-cyber-darker/70 transition-colors group"
    >
      {course.course_thumbnail ? (
        <img
          src={course.course_thumbnail}
          alt={course.course_title}
          className="w-20 h-14 rounded-lg object-cover flex-shrink-0"
        />
      ) : (
        <div className="w-20 h-14 rounded-lg bg-cyber-accent/10 flex items-center justify-center flex-shrink-0">
          <BookOpen className="w-6 h-6 text-cyber-accent/50" />
        </div>
      )}

      <div className="flex-1 min-w-0">
        <h3 className="text-white font-medium truncate group-hover:text-cyber-accent transition-colors">
          {course.course_title}
        </h3>
        <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
          <span>{course.lessons_completed}/{course.total_lessons} lessons</span>
          <span>{course.labs_completed}/{course.total_labs} labs</span>
        </div>
        <div className="flex items-center gap-3 mt-2">
          <div className="flex-1 h-2 bg-cyber-dark rounded-full overflow-hidden">
            <div
              className="h-full bg-cyber-accent rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-sm text-cyber-accent font-medium">{progress}%</span>
        </div>
      </div>

      <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-cyber-accent transition-colors" />
    </Link>
  );
}

function CompletedCourseCard({ course }: { course: CourseProgress }) {
  return (
    <Link
      href={`/courses/${course.course_id}`}
      className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg hover:bg-cyber-darker/70 transition-colors group"
    >
      <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
        <CheckCircle className="w-5 h-5 text-green-400" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-white font-medium truncate text-sm group-hover:text-cyber-accent transition-colors">
          {course.course_title}
        </h3>
        <p className="text-xs text-gray-500">
          Completed {new Date(course.last_activity).toLocaleDateString()}
        </p>
      </div>
    </Link>
  );
}

function ActivityItem({ activity }: { activity: RecentActivity }) {
  const config: Record<string, { icon: any; color: string; bgColor: string }> = {
    lesson_completed: { icon: BookOpen, color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
    lab_completed: { icon: Target, color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
    course_completed: { icon: Award, color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' },
    skill_earned: { icon: Zap, color: 'text-cyber-accent', bgColor: 'bg-cyber-accent/20' },
  };

  const { icon: Icon, color, bgColor } = config[activity.type] || config.lesson_completed;

  return (
    <div className="flex items-start gap-3 p-2 rounded-lg hover:bg-cyber-darker/50">
      <div className={`w-8 h-8 rounded-lg ${bgColor} flex items-center justify-center flex-shrink-0`}>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white truncate">{activity.title}</p>
        {activity.course_title && (
          <p className="text-xs text-gray-500 truncate">{activity.course_title}</p>
        )}
      </div>
      <span className="text-xs text-gray-500 flex-shrink-0">
        {formatRelativeTime(activity.timestamp)}
      </span>
    </div>
  );
}

function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}
