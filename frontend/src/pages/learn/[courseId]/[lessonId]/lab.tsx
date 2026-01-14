import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, ArrowLeft, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { coursesApi, labsApi, environmentsApi } from '@/services/api';
import SplitScreenLabViewer from '@/components/labs/SplitScreenLabViewer';
import Link from 'next/link';

interface LabSession {
  lab_session_id: string;
  environment: {
    id: string;
    env_type: 'terminal' | 'desktop';
    status: string;
    access_url?: string;
    ssh_port?: number;
    vnc_port?: number;
  };
  workspace_path: string;
  lab: {
    id: string;
    title: string;
    description?: string;
    difficulty: string;
    objectives: string[];
    instructions: string;
    hints: string[];
    estimated_time?: number;
  };
  course: {
    id: string;
    title: string;
  };
  lesson: {
    id: string;
    title: string;
  };
}

export default function LabLessonPage() {
  const router = useRouter();
  const { courseId, lessonId, labId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [completedObjectives, setCompletedObjectives] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Start lab session query
  const { data: labSession, isLoading: isLoadingSession, error: sessionError } = useQuery({
    queryKey: ['lab-session', courseId, lessonId, labId],
    queryFn: async () => {
      // This would call an endpoint like /api/v1/labs/start-in-course
      const response = await labsApi.startInCourse({
        course_id: courseId as string,
        lesson_id: lessonId as string,
        lab_id: labId as string,
      });
      return response as LabSession;
    },
    enabled: isAuthenticated && !!courseId && !!lessonId && !!labId,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  // Get course lessons for navigation
  const { data: courseData } = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => coursesApi.get(courseId as string),
    enabled: isAuthenticated && !!courseId,
  });

  // Environment status polling
  const { data: envStatus } = useQuery({
    queryKey: ['environment-status', labSession?.environment?.env_type],
    queryFn: () => environmentsApi.getStatus(labSession?.environment?.env_type || 'terminal'),
    enabled: isAuthenticated && !!labSession?.environment,
    refetchInterval: labSession?.environment?.status === 'starting' ? 2000 : 10000,
  });

  // Start environment mutation
  const startEnvMutation = useMutation({
    mutationFn: () => environmentsApi.start(labSession?.environment?.env_type || 'terminal'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lab-session'] });
      queryClient.invalidateQueries({ queryKey: ['environment-status'] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to start environment');
    },
  });

  // Stop environment mutation
  const stopEnvMutation = useMutation({
    mutationFn: () => environmentsApi.stop(labSession?.environment?.env_type || 'terminal'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lab-session'] });
      queryClient.invalidateQueries({ queryKey: ['environment-status'] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to stop environment');
    },
  });

  // Reset environment mutation
  const resetEnvMutation = useMutation({
    mutationFn: () => environmentsApi.reset(labSession?.environment?.env_type || 'terminal'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lab-session'] });
      queryClient.invalidateQueries({ queryKey: ['environment-status'] });
    },
  });

  // Complete objective mutation
  const completeObjectiveMutation = useMutation({
    mutationFn: (objectiveIndex: number) =>
      labsApi.completeObjective(labSession?.lab_session_id || '', objectiveIndex),
    onSuccess: (data) => {
      if (data.completed_objectives) {
        setCompletedObjectives(data.completed_objectives);
      }
    },
  });

  // Handle objective completion
  const handleObjectiveComplete = (index: number) => {
    if (!completedObjectives.includes(index)) {
      setCompletedObjectives(prev => [...prev, index]);
      completeObjectiveMutation.mutate(index);
    }
  };

  // Get adjacent lessons for navigation
  const lessons = courseData?.lessons || [];
  const currentLessonIndex = lessons.findIndex((l: any) => l.id === lessonId);
  const previousLesson = currentLessonIndex > 0 ? lessons[currentLessonIndex - 1] : null;
  const nextLesson = currentLessonIndex < lessons.length - 1 ? lessons[currentLessonIndex + 1] : null;

  // Handle navigation
  const handlePrevious = () => {
    if (previousLesson) {
      router.push(`/learn/${courseId}/${previousLesson.id}`);
    }
  };

  const handleNext = () => {
    if (nextLesson) {
      router.push(`/learn/${courseId}/${nextLesson.id}`);
    }
  };

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="h-screen flex items-center justify-center bg-cyber-darker">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  if (isLoadingSession) {
    return (
      <div className="h-screen flex items-center justify-center bg-cyber-darker">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-cyber-accent animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading lab environment...</p>
        </div>
      </div>
    );
  }

  if (sessionError || !labSession) {
    return (
      <div className="h-screen flex items-center justify-center bg-cyber-darker">
        <div className="text-center max-w-md">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Failed to Load Lab</h2>
          <p className="text-gray-400 mb-6">
            {(sessionError as any)?.response?.data?.detail || 'Unable to start lab session. Please try again.'}
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href={`/courses/${courseId}`}
              className="px-4 py-2 border border-cyber-accent/30 text-gray-300 rounded-lg hover:bg-cyber-dark transition-colors"
            >
              Back to Course
            </Link>
            <button
              onClick={() => router.reload()}
              className="px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Merge environment status from polling with session data
  const currentEnv = envStatus || labSession.environment;

  return (
    <div className="h-screen flex flex-col bg-cyber-darker">
      {/* Top Bar */}
      <div className="h-12 flex items-center justify-between px-4 border-b border-cyber-accent/20 bg-cyber-dark">
        <div className="flex items-center gap-4">
          <Link
            href={`/courses/${courseId}`}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Back to Course</span>
          </Link>
          <div className="h-4 w-px bg-cyber-accent/20" />
          <span className="text-sm text-gray-500">
            {labSession.course.title} / {labSession.lesson.title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Lab Session</span>
          <code className="text-xs text-cyber-accent/70 bg-cyber-darker px-2 py-0.5 rounded">
            {labSession.lab_session_id?.slice(0, 8)}
          </code>
        </div>
      </div>

      {/* Split Screen Lab Viewer */}
      <div className="flex-1 overflow-hidden">
        <SplitScreenLabViewer
          lab={labSession.lab}
          environment={currentEnv}
          workspacePath={labSession.workspace_path}
          completedObjectives={completedObjectives}
          onObjectiveComplete={handleObjectiveComplete}
          onStartEnvironment={() => startEnvMutation.mutate()}
          onStopEnvironment={() => stopEnvMutation.mutate()}
          onResetEnvironment={() => {
            if (confirm('This will delete all your data in the environment. Continue?')) {
              resetEnvMutation.mutate();
            }
          }}
          isStarting={startEnvMutation.isPending || currentEnv?.status === 'starting'}
          isStopping={stopEnvMutation.isPending}
          error={error || undefined}
          courseTitle={labSession.course.title}
          lessonTitle={labSession.lesson.title}
          onPrevious={handlePrevious}
          onNext={handleNext}
          hasPrevious={!!previousLesson}
          hasNext={!!nextLesson}
        />
      </div>
    </div>
  );
}
