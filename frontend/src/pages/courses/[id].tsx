import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  Clock,
  Trophy,
  ChevronDown,
  ChevronRight,
  Play,
  CheckCircle,
  Lock,
  Target,
  Users,
  Award,
  ArrowLeft,
  Loader2,
  FileText,
  Video,
  Code,
  HelpCircle,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { coursesApi } from '@/services/api';

interface Lesson {
  id: string;
  title: string;
  lesson_type: string;
  duration: number;
  points: number;
  order: number;
}

interface Module {
  id: string;
  title: string;
  description: string;
  order: number;
  learning_objectives: string[];
  estimated_duration: number;
  lessons: Lesson[];
}

interface Course {
  id: string;
  title: string;
  slug: string;
  description: string;
  short_description: string;
  category: string;
  difficulty: string;
  estimated_hours: number;
  points: number;
  thumbnail_url: string;
  cover_image_url: string;
  learning_outcomes: string[];
  what_youll_learn: string[];
  target_audience: string;
  is_ai_generated: boolean;
  modules: Module[];
}

export default function CourseDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set());

  const { data: course, isLoading, error } = useQuery({
    queryKey: ['course', id],
    queryFn: () => coursesApi.get(id as string),
    enabled: !!id && isAuthenticated,
  });

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Expand first module by default
  useEffect(() => {
    if (course?.modules?.length > 0 && expandedModules.size === 0) {
      setExpandedModules(new Set([course.modules[0].id]));
    }
  }, [course]);

  const toggleModule = (moduleId: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  };

  const getLessonIcon = (type: string) => {
    switch (type) {
      case 'video':
        return <Video className="w-4 h-4" />;
      case 'quiz':
        return <HelpCircle className="w-4 h-4" />;
      case 'lab':
        return <Code className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const difficultyColors: Record<string, string> = {
    beginner: 'bg-green-500/20 text-green-400 border-green-500/30',
    intermediate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    advanced: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    expert: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  if (error || !course) {
    return (
      <div className="p-8">
        <div className="text-center py-12">
          <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">Course not found</h3>
          <p className="text-gray-400 mb-4">
            The course you're looking for doesn't exist or has been removed.
          </p>
          <button
            onClick={() => router.push('/courses')}
            className="px-4 py-2 bg-cyber-accent text-black rounded-lg hover:bg-cyber-accent/80"
          >
            Browse Courses
          </button>
        </div>
      </div>
    );
  }

  const totalLessons = course.modules?.reduce(
    (acc: number, m: Module) => acc + (m.lessons?.length || 0),
    0
  ) || 0;

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-br from-cyber-dark via-cyber-darker to-cyber-dark border-b border-cyber-accent/20">
        <div className="absolute inset-0 bg-grid-pattern opacity-5" />

        <div className="relative px-8 py-12">
          {/* Back Button */}
          <button
            onClick={() => router.push('/courses')}
            className="flex items-center gap-2 text-gray-400 hover:text-cyber-accent mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Courses</span>
          </button>

          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col lg:flex-row gap-8">
              {/* Course Info */}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-4">
                  <span
                    className={`text-sm px-3 py-1 rounded-full border ${
                      difficultyColors[course.difficulty] || difficultyColors.beginner
                    }`}
                  >
                    {course.difficulty}
                  </span>
                  <span className="text-sm text-gray-400">
                    {course.category?.replace(/_/g, ' ')}
                  </span>
                  {course.is_ai_generated && (
                    <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-400 rounded">
                      AI Generated
                    </span>
                  )}
                </div>

                <h1 className="text-4xl font-bold text-white mb-4">{course.title}</h1>
                <p className="text-gray-300 text-lg mb-6">
                  {course.description || course.short_description}
                </p>

                {/* Stats */}
                <div className="flex flex-wrap gap-6 mb-6">
                  <div className="flex items-center gap-2 text-gray-300">
                    <Clock className="w-5 h-5 text-cyber-accent" />
                    <span>{course.estimated_hours} hours</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-300">
                    <BookOpen className="w-5 h-5 text-cyber-accent" />
                    <span>{course.modules?.length || 0} modules</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-300">
                    <FileText className="w-5 h-5 text-cyber-accent" />
                    <span>{totalLessons} lessons</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-300">
                    <Trophy className="w-5 h-5 text-cyber-accent" />
                    <span>{course.points} points</span>
                  </div>
                </div>

                {/* Start Learning Button */}
                {course.modules?.[0]?.lessons?.[0] && (
                  <button
                    onClick={() =>
                      router.push(
                        `/courses/${course.id}/lesson/${course.modules[0].lessons[0].id}`
                      )
                    }
                    className="px-6 py-3 bg-cyber-accent text-black font-semibold rounded-lg hover:bg-cyber-accent/80 transition-colors flex items-center gap-2"
                  >
                    <Play className="w-5 h-5" />
                    Start Learning
                  </button>
                )}
              </div>

              {/* What You'll Learn Card */}
              <div className="lg:w-96">
                <div className="bg-cyber-dark/80 backdrop-blur-sm rounded-xl border border-cyber-accent/20 p-6">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Target className="w-5 h-5 text-cyber-accent" />
                    What You'll Learn
                  </h3>
                  <ul className="space-y-3">
                    {(course.what_youll_learn?.length > 0
                      ? course.what_youll_learn
                      : course.learning_outcomes?.length > 0
                      ? course.learning_outcomes
                      : ['Core concepts and fundamentals', 'Practical hands-on skills', 'Real-world applications']
                    )
                      .slice(0, 5)
                      .map((item: string, index: number) => (
                        <li key={index} className="flex items-start gap-2 text-gray-300">
                          <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                  </ul>

                  {course.target_audience && (
                    <div className="mt-6 pt-4 border-t border-gray-700">
                      <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        Target Audience
                      </h4>
                      <p className="text-gray-300 text-sm">{course.target_audience}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Course Content */}
      <div className="max-w-6xl mx-auto px-8 py-8">
        <h2 className="text-2xl font-bold text-white mb-6">Course Content</h2>

        {/* Modules */}
        <div className="space-y-4">
          {course.modules?.map((module: Module, moduleIndex: number) => (
            <div
              key={module.id}
              className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden"
            >
              {/* Module Header */}
              <button
                onClick={() => toggleModule(module.id)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-cyber-accent/5 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-8 h-8 rounded-lg bg-cyber-accent/20 flex items-center justify-center text-cyber-accent font-semibold">
                    {moduleIndex + 1}
                  </div>
                  <div className="text-left">
                    <h3 className="text-lg font-medium text-white">{module.title}</h3>
                    <p className="text-sm text-gray-400">
                      {module.lessons?.length || 0} lessons
                      {module.estimated_duration > 0 && ` • ${module.estimated_duration} min`}
                    </p>
                  </div>
                </div>
                {expandedModules.has(module.id) ? (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                )}
              </button>

              {/* Module Content */}
              {expandedModules.has(module.id) && (
                <div className="border-t border-gray-800">
                  {/* Module Description */}
                  {module.description && (
                    <div className="px-6 py-3 bg-cyber-darker/50 text-gray-400 text-sm">
                      {module.description}
                    </div>
                  )}

                  {/* Learning Objectives */}
                  {module.learning_objectives?.length > 0 && (
                    <div className="px-6 py-3 border-b border-gray-800">
                      <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                        Learning Objectives
                      </h4>
                      <ul className="flex flex-wrap gap-2">
                        {module.learning_objectives.map((obj: string, i: number) => (
                          <li
                            key={i}
                            className="text-xs px-2 py-1 bg-cyber-accent/10 text-cyber-accent rounded"
                          >
                            {obj}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Lessons */}
                  <div className="divide-y divide-gray-800">
                    {module.lessons?.map((lesson: Lesson, lessonIndex: number) => (
                      <button
                        key={lesson.id}
                        onClick={() =>
                          router.push(`/courses/${course.id}/lesson/${lesson.id}`)
                        }
                        className="w-full px-6 py-3 flex items-center justify-between hover:bg-cyber-accent/5 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-gray-500 text-sm w-6">
                            {lessonIndex + 1}.
                          </span>
                          <span className="text-gray-400">
                            {getLessonIcon(lesson.lesson_type)}
                          </span>
                          <span className="text-gray-300">{lesson.title}</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-gray-500">
                          <span>{lesson.duration} min</span>
                          <span className="text-cyber-accent">{lesson.points} pts</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
