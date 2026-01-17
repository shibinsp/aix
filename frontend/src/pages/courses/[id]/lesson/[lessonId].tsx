import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Clock,
  Trophy,
  CheckCircle,
  Target,
  FileText,
  Code,
  Video,
  Image as ImageIcon,
  ExternalLink,
  Lightbulb,
  AlertTriangle,
  Info,
  Copy,
  Check,
  Loader2,
  PanelLeftClose,
  PanelLeft,
  FlaskConical,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { coursesApi, labsApi, environmentsApi } from '@/services/api';
import ContentBlockRenderer from '@/components/courses/ContentBlockRenderer';
import SplitScreenLabViewer from '@/components/labs/SplitScreenLabViewer';

interface ContentBlock {
  id: string;
  block_type: string;
  order: number;
  content: string;
  block_metadata: Record<string, any>;
}

interface ExternalResource {
  id: string;
  resource_type: string;
  title: string;
  url: string;
  description: string;
  resource_metadata: Record<string, any>;
}

interface LabData {
  id: string;
  title: string;
  description?: string;
  difficulty: string;
  objectives: string[];
  instructions: string;
  hints: string[];
  estimated_time?: number;
  preset?: string;
  flags?: any[];
}

interface LabSession {
  id: string;
  status: string;
  access_url?: string;
  ssh_port?: number;
  vnc_port?: number;
  completed_objectives: number[];
}

interface Lesson {
  id: string;
  module_id: string;
  title: string;
  content: string;
  lesson_type: string;
  order: number;
  duration: number;
  points: number;
  learning_objectives: string[];
  key_takeaways: string[];
  word_count: number;
  estimated_reading_time: number;
  generation_status: string;
  quiz_data: any;
  content_blocks: ContentBlock[];
  external_resources: ExternalResource[];
  lab_id?: string;
  lab?: LabData;
}

interface Module {
  id: string;
  title: string;
  lessons: { id: string; title: string; order: number; lesson_type?: string }[];
}

interface Course {
  id: string;
  title: string;
  modules: Module[];
}

export default function LessonViewer() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id: courseId, lessonId } = router.query;
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Lab session state
  const [labSession, setLabSession] = useState<LabSession | null>(null);
  const [labError, setLabError] = useState<string | null>(null);
  const [completedObjectives, setCompletedObjectives] = useState<number[]>([]);

  // Fetch course for navigation
  const { data: course } = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => coursesApi.get(courseId as string),
    enabled: !!courseId && isAuthenticated,
  });

  // Fetch full lesson with content blocks
  const { data: lesson, isLoading: lessonLoading } = useQuery({
    queryKey: ['lesson', courseId, lessonId],
    queryFn: () => coursesApi.getFullLesson(courseId as string, lessonId as string),
    enabled: !!courseId && !!lessonId && isAuthenticated,
  });

  // Check if this is a lab lesson (ensure boolean for React Query)
  const isLabLesson = !!(lesson?.lesson_type === 'lab' && lesson?.lab);

  // Environment status polling for lab lessons - poll ALWAYS for lab lessons (independent of labSession)
  const { data: envStatus, isLoading: envLoading } = useQuery({
    queryKey: ['environment-status', 'desktop'],
    queryFn: () => environmentsApi.getStatus('desktop'),
    enabled: !!isAuthenticated && isLabLesson,  // No labSession requirement - detect already-running environments
    refetchInterval: 5000,  // Poll every 5 seconds
  });

  // Build environment object from polled status (for SplitScreenLabViewer)
  // Note: getStatus returns access_url and ports inside connection_info
  const environment = envStatus ? {
    id: envStatus.id || 'env',
    env_type: 'desktop' as const,  // Use const assertion for literal type
    status: envStatus.status,
    access_url: envStatus.connection_info?.access_url,
    ssh_port: envStatus.connection_info?.ssh_port,
    vnc_port: envStatus.connection_info?.vnc_port,
  } : null;


  // Lab session mutations
  const startLabMutation = useMutation({
    mutationFn: async () => {
      if (!lesson?.lab || !courseId || !lessonId) throw new Error('Missing lab data');
      return labsApi.startInCourse({
        course_id: courseId as string,
        lesson_id: lessonId as string,
        lab_id: lesson.lab.id,
      });
    },
    onSuccess: (data) => {
      setLabSession(data);
      setCompletedObjectives(data.completed_objectives || []);
      setLabError(null);
    },
    onError: (error: any) => {
      setLabError(error?.response?.data?.detail || 'Failed to start lab environment');
    },
  });

  const stopLabMutation = useMutation({
    mutationFn: async () => {
      if (!labSession?.id) throw new Error('No active session');
      return labsApi.endSession(labSession.id);
    },
    onSuccess: () => {
      setLabSession(null);
      setLabError(null);
    },
    onError: (error: any) => {
      setLabError(error?.response?.data?.detail || 'Failed to stop lab environment');
    },
  });

  const completeObjectiveMutation = useMutation({
    mutationFn: async (objectiveIndex: number) => {
      if (!labSession?.id) throw new Error('No active session');
      return labsApi.completeObjective(labSession.id, objectiveIndex);
    },
    onSuccess: (data, objectiveIndex) => {
      setCompletedObjectives((prev) => [...prev, objectiveIndex]);
    },
    onError: (error: any) => {
      setLabError(error?.response?.data?.detail || 'Failed to complete objective');
    },
  });

  // Lab handlers
  const handleStartEnvironment = useCallback(async () => {
    setLabError(null);
    try {
      // Start the desktop environment if not already running
      if (envStatus?.status !== 'running') {
        await environmentsApi.start('desktop');
      }
      // Create lab session for tracking objectives
      await startLabMutation.mutateAsync();
      queryClient.invalidateQueries({ queryKey: ['environment-status'] });
    } catch (error: any) {
      setLabError(error?.response?.data?.detail || 'Failed to start environment');
    }
  }, [envStatus?.status, startLabMutation, queryClient]);

  const handleStopEnvironment = useCallback(() => {
    stopLabMutation.mutate();
  }, [stopLabMutation]);

  const handleResetEnvironment = useCallback(() => {
    // Stop then restart
    if (labSession) {
      stopLabMutation.mutate();
    }
    setTimeout(() => {
      startLabMutation.mutate();
    }, 1000);
  }, [labSession, stopLabMutation, startLabMutation]);

  const handleObjectiveComplete = useCallback((index: number) => {
    if (!completedObjectives.includes(index)) {
      completeObjectiveMutation.mutate(index);
    }
  }, [completedObjectives, completeObjectiveMutation]);

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Find current position and navigation
  const navigation = useMemo(() => {
    if (!course || !lessonId) return { prev: null, next: null, currentModule: null };

    let prev = null;
    let next = null;
    let currentModule = null;
    let found = false;

    for (const module of course.modules || []) {
      for (let i = 0; i < (module.lessons?.length || 0); i++) {
        const lessonItem = module.lessons[i];

        if (found && !next) {
          next = { moduleTitle: module.title, lesson: lessonItem };
        }

        if (lessonItem.id === lessonId) {
          found = true;
          currentModule = module;
        }

        if (!found) {
          prev = { moduleTitle: module.title, lesson: lessonItem };
        }
      }
    }

    return { prev, next, currentModule };
  }, [course, lessonId]);

  const handleCopyCode = async (code: string, blockId: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedCode(blockId);
    setTimeout(() => setCopiedCode(null), 2000);
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

  if (lessonLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">Lesson not found</h3>
          <button
            onClick={() => router.push(`/courses/${courseId}`)}
            className="text-cyber-accent hover:underline"
          >
            Back to course
          </button>
        </div>
      </div>
    );
  }

  // Render SplitScreenLabViewer for lab-type lessons
  if (isLabLesson && lesson.lab) {
    return (
      <div className="h-screen">
        <SplitScreenLabViewer
          lab={{
            id: lesson.lab.id,
            title: lesson.lab.title,
            description: lesson.lab.description,
            difficulty: lesson.lab.difficulty,
            objectives: lesson.lab.objectives || [],
            instructions: lesson.lab.instructions || '',
            hints: lesson.lab.hints || [],
            estimated_time: lesson.lab.estimated_time,
          }}
          environment={environment || undefined}
          completedObjectives={completedObjectives}
          onObjectiveComplete={handleObjectiveComplete}
          onStartEnvironment={handleStartEnvironment}
          onStopEnvironment={handleStopEnvironment}
          onResetEnvironment={handleResetEnvironment}
          isStarting={startLabMutation.isPending}
          isStopping={stopLabMutation.isPending}
          error={labError || undefined}
          courseTitle={course?.title}
          lessonTitle={lesson.title}
          onPrevious={
            navigation.prev
              ? () => router.push(`/courses/${courseId}/lesson/${navigation.prev!.lesson.id}`)
              : undefined
          }
          onNext={
            navigation.next
              ? () => router.push(`/courses/${courseId}/lesson/${navigation.next!.lesson.id}`)
              : undefined
          }
          hasPrevious={!!navigation.prev}
          hasNext={!!navigation.next}
        />
      </div>
    );
  }

  // Standard lesson view
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'w-80' : 'w-0'
        } bg-cyber-darker border-r border-cyber-accent/20 flex-shrink-0 overflow-hidden transition-all duration-300 relative`}
      >
        <div className="h-full flex flex-col w-80">
          {/* Sidebar Header */}
          <div className="p-4 border-b border-gray-800">
            <div className="flex items-center justify-between mb-3">
              <button
                onClick={() => router.push(`/courses/${courseId}`)}
                className="text-sm text-gray-400 hover:text-cyber-accent flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" />
                Back to Course
              </button>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 hover:bg-cyber-accent/10 rounded-lg text-gray-400 hover:text-cyber-accent transition-colors"
                title="Collapse sidebar"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>
            <h2 className="text-white font-medium truncate">{course?.title}</h2>
          </div>

          {/* Module List */}
          <div className="flex-1 overflow-y-auto">
            {course?.modules?.map((module: Module) => (
              <div key={module.id} className="border-b border-gray-800">
                <div className="px-4 py-3 bg-cyber-dark/50">
                  <h3 className="text-sm font-medium text-gray-300">{module.title}</h3>
                </div>
                <div className="py-1">
                  {module.lessons?.map((lessonItem) => {
                    const isLab = lessonItem.lesson_type === 'lab';
                    return (
                      <button
                        key={lessonItem.id}
                        onClick={() =>
                          router.push(`/courses/${courseId}/lesson/${lessonItem.id}`)
                        }
                        className={`w-full px-4 py-2 text-left text-sm flex items-center gap-2 hover:bg-cyber-accent/10 transition-colors ${
                          lessonItem.id === lessonId
                            ? 'bg-cyber-accent/20 text-cyber-accent border-l-2 border-cyber-accent'
                            : 'text-gray-400'
                        }`}
                      >
                        {isLab ? (
                          <FlaskConical className="w-4 h-4 flex-shrink-0 text-purple-400" />
                        ) : (
                          <FileText className="w-4 h-4 flex-shrink-0" />
                        )}
                        <span className="truncate">{lessonItem.title}</span>
                        {isLab && (
                          <span className="ml-auto text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded">
                            Lab
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Collapsed sidebar toggle button */}
      {!sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-40 bg-cyber-darker hover:bg-cyber-dark border border-cyber-accent/30 hover:border-cyber-accent/50 rounded-r-lg p-2 text-gray-400 hover:text-cyber-accent transition-all shadow-lg"
          title="Expand sidebar"
        >
          <PanelLeft className="w-5 h-5" />
        </button>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="h-14 bg-cyber-dark border-b border-gray-800 flex items-center justify-between px-4 flex-shrink-0">
          <div className="flex items-center gap-4">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 hover:bg-cyber-accent/10 rounded-lg text-gray-400 hover:text-white"
                title="Show course outline"
              >
                <Menu className="w-5 h-5" />
              </button>
            )}
            <div>
              <h1 className="text-white font-medium">{lesson.title}</h1>
              <div className="text-xs text-gray-500 flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {lesson.estimated_reading_time || lesson.duration} min
                </span>
                <span className="flex items-center gap-1">
                  <Trophy className="w-3 h-3" />
                  {lesson.points} pts
                </span>
                {lesson.word_count > 0 && (
                  <span>{lesson.word_count.toLocaleString()} words</span>
                )}
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={() =>
                navigation.prev &&
                router.push(`/courses/${courseId}/lesson/${navigation.prev.lesson.id}`)
              }
              disabled={!navigation.prev}
              className="p-2 hover:bg-cyber-accent/10 rounded-lg text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={() =>
                navigation.next &&
                router.push(`/courses/${courseId}/lesson/${navigation.next.lesson.id}`)
              }
              disabled={!navigation.next}
              className="p-2 hover:bg-cyber-accent/10 rounded-lg text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Lesson Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-8 py-8">
            {/* Learning Objectives */}
            {lesson.learning_objectives?.length > 0 && (
              <div className="mb-8 p-4 bg-cyber-accent/10 border border-cyber-accent/20 rounded-xl">
                <h3 className="text-sm font-medium text-cyber-accent mb-3 flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Learning Objectives
                </h3>
                <ul className="space-y-2">
                  {lesson.learning_objectives.map((obj: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-gray-300 text-sm">
                      <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                      <span>{obj}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Content Blocks */}
            {lesson.content_blocks?.length > 0 ? (
              <div className="space-y-6">
                {lesson.content_blocks
                  .sort((a: ContentBlock, b: ContentBlock) => a.order - b.order)
                  .map((block: ContentBlock) => (
                    <ContentBlockRenderer
                      key={block.id}
                      block={block}
                      onCopyCode={handleCopyCode}
                      copiedCode={copiedCode}
                    />
                  ))}
              </div>
            ) : lesson.content ? (
              /* Fallback to raw markdown content */
              <div className="prose prose-invert prose-lg max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {lesson.content}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-400">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Content is being generated...</p>
              </div>
            )}

            {/* Key Takeaways */}
            {lesson.key_takeaways?.length > 0 && (
              <div className="mt-8 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
                <h3 className="text-sm font-medium text-green-400 mb-3 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4" />
                  Key Takeaways
                </h3>
                <ul className="space-y-2">
                  {lesson.key_takeaways.map((takeaway: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-gray-300 text-sm">
                      <span className="text-green-400">•</span>
                      <span>{takeaway}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* External Resources */}
            {lesson.external_resources?.length > 0 && (
              <div className="mt-8">
                <h3 className="text-lg font-medium text-white mb-4">External Resources</h3>
                <div className="space-y-3">
                  {lesson.external_resources.map((resource: ExternalResource) => (
                    <a
                      key={resource.id}
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-3 bg-cyber-dark border border-gray-800 rounded-lg hover:border-cyber-accent/50 transition-colors"
                    >
                      <div className="w-10 h-10 rounded-lg bg-cyber-accent/20 flex items-center justify-center text-cyber-accent">
                        <ExternalLink className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-white font-medium">{resource.title}</h4>
                        {resource.description && (
                          <p className="text-gray-400 text-sm line-clamp-1">
                            {resource.description}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 uppercase">
                        {resource.resource_type}
                      </span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Quiz Section */}
            {lesson.quiz_data?.questions?.length > 0 && (
              <div className="mt-8 p-6 bg-cyber-dark border border-cyber-accent/20 rounded-xl">
                <h3 className="text-lg font-medium text-white mb-4">
                  Knowledge Check
                </h3>
                <p className="text-gray-400 mb-4">
                  Test your understanding with {lesson.quiz_data.questions.length} questions.
                </p>
                <button className="px-4 py-2 bg-cyber-accent text-black font-medium rounded-lg hover:bg-cyber-accent/80">
                  Start Quiz
                </button>
              </div>
            )}

            {/* Navigation Footer */}
            <div className="mt-12 pt-8 border-t border-gray-800 flex justify-between">
              {navigation.prev ? (
                <button
                  onClick={() =>
                    router.push(`/courses/${courseId}/lesson/${navigation.prev!.lesson.id}`)
                  }
                  className="flex items-center gap-2 text-gray-400 hover:text-cyber-accent transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                  <div className="text-left">
                    <div className="text-xs text-gray-500">Previous</div>
                    <div>{navigation.prev.lesson.title}</div>
                  </div>
                </button>
              ) : (
                <div />
              )}

              {navigation.next ? (
                <button
                  onClick={() =>
                    router.push(`/courses/${courseId}/lesson/${navigation.next!.lesson.id}`)
                  }
                  className="flex items-center gap-2 text-gray-400 hover:text-cyber-accent transition-colors"
                >
                  <div className="text-right">
                    <div className="text-xs text-gray-500">Next</div>
                    <div>{navigation.next.lesson.title}</div>
                  </div>
                  <ChevronRight className="w-5 h-5" />
                </button>
              ) : (
                <button
                  onClick={() => router.push(`/courses/${courseId}`)}
                  className="flex items-center gap-2 text-cyber-accent hover:text-cyber-accent/80 transition-colors"
                >
                  <CheckCircle className="w-5 h-5" />
                  <span>Complete Course</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
