import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  BookOpen,
  Search,
  Clock,
  Users,
  TrendingUp,
  ChevronDown,
  ExternalLink,
  BarChart3
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { api } from '@/services/api';

interface Course {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  duration_hours: number;
  modules_count: number;
  enrolled_members: number;
  completion_rate: number;
  avg_progress: number;
}

export default function PortalCourses() {
  const router = useRouter();
  const { orgId } = router.query;
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('all');
  const [sortBy, setSortBy] = useState<'enrolled' | 'progress' | 'title'>('enrolled');

  useEffect(() => {
    if (orgId) {
      fetchCourses();
    }
  }, [orgId]);

  const fetchCourses = async () => {
    try {
      const res = await api.get(`/organizations/${orgId}/courses`);
      setCourses(res.data);
    } catch (error) {
      // Fallback - fetch all courses
      try {
        const res = await api.get('/courses');
        setCourses(res.data.map((c: any) => ({
          ...c,
          enrolled_members: 0,
          completion_rate: 0,
          avg_progress: 0
        })));
      } catch {
        setCourses([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredCourses = courses
    .filter(course => {
      const matchesSearch = course.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        course.description?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesDifficulty = difficultyFilter === 'all' ||
        course.difficulty.toLowerCase() === difficultyFilter;
      return matchesSearch && matchesDifficulty;
    })
    .sort((a, b) => {
      if (sortBy === 'enrolled') return b.enrolled_members - a.enrolled_members;
      if (sortBy === 'progress') return b.avg_progress - a.avg_progress;
      return a.title.localeCompare(b.title);
    });

  const getDifficultyColor = (difficulty: string) => {
    const colors: Record<string, string> = {
      beginner: 'bg-cyber-accent/20 text-cyber-accent border-cyber-accent/30',
      intermediate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      advanced: 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    return colors[difficulty.toLowerCase()] || colors.beginner;
  };

  const totalEnrolled = courses.reduce((sum, c) => sum + c.enrolled_members, 0);
  const avgCompletion = courses.length > 0
    ? Math.round(courses.reduce((sum, c) => sum + c.completion_rate, 0) / courses.length)
    : 0;

  return (
    <PortalLayout title="Courses" subtitle="View course enrollment and progress">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <BookOpen className="w-4 h-4" />
            Total Courses
          </div>
          <p className="text-2xl font-bold text-white">{courses.length}</p>
        </div>
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Users className="w-4 h-4" />
            Total Enrollments
          </div>
          <p className="text-2xl font-bold text-white">{totalEnrolled}</p>
        </div>
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <TrendingUp className="w-4 h-4" />
            Avg Completion
          </div>
          <p className="text-2xl font-bold text-white">{avgCompletion}%</p>
        </div>
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Clock className="w-4 h-4" />
            Total Hours
          </div>
          <p className="text-2xl font-bold text-white">
            {courses.reduce((sum, c) => sum + c.duration_hours, 0)}h
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search courses..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent transition-colors"
          />
        </div>

        <div className="relative">
          <select
            value={difficultyFilter}
            onChange={(e) => setDifficultyFilter(e.target.value)}
            className="appearance-none px-4 py-2.5 pr-10 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent transition-colors cursor-pointer"
          >
            <option value="all">All Levels</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
        </div>

        <div className="relative">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="appearance-none px-4 py-2.5 pr-10 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent transition-colors cursor-pointer"
          >
            <option value="enrolled">Most Enrolled</option>
            <option value="progress">Best Progress</option>
            <option value="title">Alphabetical</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Courses Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
        </div>
      ) : filteredCourses.length === 0 ? (
        <div className="text-center py-12 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No courses found</p>
          <p className="text-sm text-gray-500 mt-1">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCourses.map((course) => (
            <div
              key={course.id}
              className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20 hover:border-cyber-accent/40 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 rounded-lg bg-cyber-accent/10">
                  <BookOpen className="w-6 h-6 text-cyber-accent" />
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getDifficultyColor(course.difficulty)}`}>
                  {course.difficulty}
                </span>
              </div>

              <h3 className="text-lg font-semibold text-white mb-2">{course.title}</h3>
              <p className="text-sm text-gray-400 mb-4 line-clamp-2">
                {course.description || 'No description available'}
              </p>

              <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4" />
                  <span>{course.duration_hours}h</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Users className="w-4 h-4" />
                  <span>{course.enrolled_members} enrolled</span>
                </div>
              </div>

              {/* Progress Stats */}
              <div className="space-y-3 pt-4 border-t border-cyber-accent/10">
                <div>
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-gray-500">Avg Progress</span>
                    <span className="text-cyber-accent">{course.avg_progress}%</span>
                  </div>
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyber-accent rounded-full"
                      style={{ width: `${course.avg_progress}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-gray-500">Completion Rate</span>
                    <span className="text-blue-400">{course.completion_rate}%</span>
                  </div>
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${course.completion_rate}%` }}
                    />
                  </div>
                </div>
              </div>

              <button
                onClick={() => router.push(`/courses/${course.id}`)}
                className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 border border-cyber-accent/20 text-gray-400 rounded-lg hover:text-cyber-accent hover:border-cyber-accent/40 transition-colors text-sm"
              >
                View Course
                <ExternalLink className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </PortalLayout>
  );
}
