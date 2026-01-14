import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
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
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { coursesApi } from '@/services/api';
import ContentBlockRenderer from '@/components/courses/ContentBlockRenderer';

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
}

interface Module {
  id: string;
  title: string;
  lessons: { id: string; title: string; order: number }[];
}

interface Course {
  id: string;
  title: string;
  modules: Module[];
}

export default function LessonViewer() {
  const router = useRouter();
  const { id: courseId, lessonId } = router.query;
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

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
                  {module.lessons?.map((lessonItem) => (
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
                      <FileText className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{lessonItem.title}</span>
                    </button>
                  ))}
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
