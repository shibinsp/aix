import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Terminal, Monitor, ChevronLeft, ChevronRight, RotateCcw,
  CheckCircle, Circle, Lightbulb, Clock, Loader2, AlertCircle,
  Maximize2, Minimize2, BookOpen, Target
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface LabObjective {
  id: number;
  title: string;
  completed: boolean;
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
}

interface EnvironmentInfo {
  id: string;
  env_type: 'terminal' | 'desktop';
  status: string;
  access_url?: string;
  ssh_port?: number;
  vnc_port?: number;
}

interface SplitScreenLabViewerProps {
  lab: LabData;
  environment?: EnvironmentInfo;
  workspacePath?: string;
  completedObjectives: number[];
  onObjectiveComplete: (index: number) => void;
  onStartEnvironment: () => void;
  onStopEnvironment: () => void;
  onResetEnvironment: () => void;
  isStarting?: boolean;
  isStopping?: boolean;
  error?: string;
  courseTitle?: string;
  lessonTitle?: string;
  onPrevious?: () => void;
  onNext?: () => void;
  hasPrevious?: boolean;
  hasNext?: boolean;
}

export default function SplitScreenLabViewer({
  lab,
  environment,
  workspacePath,
  completedObjectives,
  onObjectiveComplete,
  onStartEnvironment,
  onStopEnvironment,
  onResetEnvironment,
  isStarting,
  isStopping,
  error,
  courseTitle,
  lessonTitle,
  onPrevious,
  onNext,
  hasPrevious,
  hasNext,
}: SplitScreenLabViewerProps) {
  const [splitPosition, setSplitPosition] = useState(40); // percentage
  const [isDragging, setIsDragging] = useState(false);
  const [showHints, setShowHints] = useState(false);
  const [currentHint, setCurrentHint] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [envView, setEnvView] = useState<'terminal' | 'desktop'>('terminal');
  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const isRunning = environment?.status === 'running';
  const isTerminal = environment?.env_type === 'terminal';

  // Handle split drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const newPosition = ((e.clientX - rect.left) / rect.width) * 100;
    setSplitPosition(Math.min(70, Math.max(30, newPosition)));
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Calculate completed vs total objectives
  const totalObjectives = lab.objectives?.length || 0;
  const completedCount = completedObjectives.length;
  const progressPercent = totalObjectives > 0 ? (completedCount / totalObjectives) * 100 : 0;

  const difficultyColors: Record<string, string> = {
    beginner: 'bg-green-500/20 text-green-400',
    intermediate: 'bg-yellow-500/20 text-yellow-400',
    advanced: 'bg-red-500/20 text-red-400',
  };

  return (
    <div
      ref={containerRef}
      className={`flex h-full bg-cyber-darker ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}
    >
      {/* Left Panel - Instructions */}
      <div
        className="flex flex-col border-r border-cyber-accent/20 overflow-hidden"
        style={{ width: `${splitPosition}%` }}
      >
        {/* Header */}
        <div className="p-4 border-b border-cyber-accent/20 bg-cyber-dark">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-cyber-accent" />
              <h2 className="text-lg font-semibold text-white truncate">{lab.title}</h2>
            </div>
            <span className={`text-xs px-2 py-1 rounded-full ${difficultyColors[lab.difficulty] || 'bg-gray-500/20 text-gray-400'}`}>
              {lab.difficulty}
            </span>
          </div>
          {(courseTitle || lessonTitle) && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <BookOpen className="w-4 h-4" />
              <span>{courseTitle}</span>
              {lessonTitle && <span>/ {lessonTitle}</span>}
            </div>
          )}
        </div>

        {/* Objectives */}
        <div className="p-4 border-b border-cyber-accent/20 bg-cyber-dark/50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-400">OBJECTIVES</h3>
            <span className="text-xs text-cyber-accent">
              {completedCount}/{totalObjectives} completed
            </span>
          </div>
          <div className="space-y-2">
            {lab.objectives?.map((objective, index) => {
              const isCompleted = completedObjectives.includes(index);
              return (
                <button
                  key={index}
                  onClick={() => !isCompleted && onObjectiveComplete(index)}
                  className={`w-full flex items-start gap-2 p-2 rounded-lg text-left transition-colors ${
                    isCompleted
                      ? 'bg-green-500/10 border border-green-500/30'
                      : 'bg-cyber-darker hover:bg-cyber-darker/70 border border-transparent'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-5 h-5 text-gray-500 flex-shrink-0 mt-0.5" />
                  )}
                  <span className={`text-sm ${isCompleted ? 'text-green-400 line-through' : 'text-gray-300'}`}>
                    {objective}
                  </span>
                </button>
              );
            })}
          </div>
          {/* Progress bar */}
          <div className="mt-3 h-1.5 bg-cyber-darker rounded-full overflow-hidden">
            <div
              className="h-full bg-cyber-accent rounded-full transition-all"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Instructions */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              components={{
                code: ({ node, inline, className, children, ...props }: any) => {
                  if (inline) {
                    return (
                      <code className="bg-cyber-darker px-1.5 py-0.5 rounded text-cyber-accent font-mono text-sm" {...props}>
                        {children}
                      </code>
                    );
                  }
                  return (
                    <pre className="bg-cyber-darker p-3 rounded-lg overflow-x-auto border border-cyber-accent/20">
                      <code className="text-gray-300 font-mono text-sm" {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                },
                h1: ({ children }) => <h1 className="text-xl font-bold text-white mb-4">{children}</h1>,
                h2: ({ children }) => <h2 className="text-lg font-semibold text-white mt-6 mb-3">{children}</h2>,
                h3: ({ children }) => <h3 className="text-md font-medium text-white mt-4 mb-2">{children}</h3>,
                p: ({ children }) => <p className="text-gray-300 mb-3 leading-relaxed">{children}</p>,
                ul: ({ children }) => <ul className="list-disc list-inside text-gray-300 mb-3 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside text-gray-300 mb-3 space-y-1">{children}</ol>,
                a: ({ href, children }) => (
                  <a href={href} className="text-cyber-accent hover:underline" target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {lab.instructions || '*No instructions provided*'}
            </ReactMarkdown>
          </div>
        </div>

        {/* Footer - Hints & Navigation */}
        <div className="p-4 border-t border-cyber-accent/20 bg-cyber-dark">
          {/* Hints */}
          {lab.hints && lab.hints.length > 0 && (
            <div className="mb-3">
              <button
                onClick={() => setShowHints(!showHints)}
                className="flex items-center gap-2 text-sm text-yellow-400 hover:text-yellow-300"
              >
                <Lightbulb className="w-4 h-4" />
                {showHints ? 'Hide Hints' : `Show Hints (${lab.hints.length})`}
              </button>
              {showHints && (
                <div className="mt-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <p className="text-sm text-yellow-400">{lab.hints[currentHint]}</p>
                  {lab.hints.length > 1 && (
                    <div className="flex justify-between mt-2">
                      <button
                        onClick={() => setCurrentHint(Math.max(0, currentHint - 1))}
                        disabled={currentHint === 0}
                        className="text-xs text-yellow-400 disabled:opacity-50"
                      >
                        Previous
                      </button>
                      <span className="text-xs text-yellow-400/70">
                        {currentHint + 1}/{lab.hints.length}
                      </span>
                      <button
                        onClick={() => setCurrentHint(Math.min(lab.hints.length - 1, currentHint + 1))}
                        disabled={currentHint === lab.hints.length - 1}
                        className="text-xs text-yellow-400 disabled:opacity-50"
                      >
                        Next
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between">
            <button
              onClick={onPrevious}
              disabled={!hasPrevious}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>
            <button
              onClick={onNext}
              disabled={!hasNext}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Resize Handle */}
      <div
        className={`w-1 cursor-col-resize hover:bg-cyber-accent/50 transition-colors ${
          isDragging ? 'bg-cyber-accent' : 'bg-cyber-accent/20'
        }`}
        onMouseDown={handleMouseDown}
      />

      {/* Right Panel - Environment */}
      <div
        className="flex flex-col overflow-hidden"
        style={{ width: `${100 - splitPosition}%` }}
      >
        {/* Environment Header */}
        <div className="p-3 border-b border-cyber-accent/20 bg-cyber-dark flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Environment type tabs */}
            <div className="flex bg-cyber-darker rounded-lg p-0.5">
              <button
                onClick={() => setEnvView('terminal')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  envView === 'terminal'
                    ? 'bg-cyber-accent/20 text-cyber-accent'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <Terminal className="w-4 h-4" />
                Terminal
              </button>
              <button
                onClick={() => setEnvView('desktop')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  envView === 'desktop'
                    ? 'bg-cyber-accent/20 text-cyber-accent'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <Monitor className="w-4 h-4" />
                Desktop
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Status indicator */}
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${
              isRunning
                ? 'bg-green-500/20 text-green-400'
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-400' : 'bg-gray-400'}`} />
              {isRunning ? 'Connected' : 'Disconnected'}
            </div>

            {/* Estimated time */}
            {lab.estimated_time && (
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Clock className="w-3 h-3" />
                {lab.estimated_time} min
              </div>
            )}

            {/* Controls */}
            <button
              onClick={onResetEnvironment}
              className="p-1.5 hover:bg-cyber-darker rounded-lg text-gray-400 hover:text-white transition-colors"
              title="Reset environment"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 hover:bg-cyber-darker rounded-lg text-gray-400 hover:text-white transition-colors"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Environment Content */}
        <div className="flex-1 bg-black relative">
          {error && (
            <div className="absolute top-4 left-4 right-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 z-10">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-sm text-red-400">{error}</span>
            </div>
          )}

          {!isRunning ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="w-20 h-20 rounded-2xl bg-cyber-accent/10 flex items-center justify-center mb-4">
                {envView === 'terminal' ? (
                  <Terminal className="w-10 h-10 text-cyber-accent/50" />
                ) : (
                  <Monitor className="w-10 h-10 text-cyber-accent/50" />
                )}
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Environment Not Running</h3>
              <p className="text-sm text-gray-500 mb-4 text-center max-w-xs">
                Start your {envView} environment to begin the lab exercises.
              </p>
              <button
                onClick={onStartEnvironment}
                disabled={isStarting}
                className="flex items-center gap-2 px-6 py-2.5 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
              >
                {isStarting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    Start Environment
                  </>
                )}
              </button>
              {workspacePath && (
                <p className="text-xs text-gray-600 mt-3">
                  Workspace: <code className="text-cyber-accent/70">{workspacePath}</code>
                </p>
              )}
            </div>
          ) : (
            <>
              {envView === 'terminal' ? (
                <div className="w-full h-full">
                  {environment?.access_url ? (
                    <iframe
                      ref={iframeRef}
                      src={environment.access_url}
                      className="w-full h-full border-0"
                      title="Terminal"
                      sandbox="allow-same-origin allow-scripts allow-forms"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Terminal className="w-12 h-12 mb-3 text-gray-600" />
                      <p>Terminal connected on port {environment?.ssh_port}</p>
                      <code className="mt-2 text-sm text-cyber-accent">
                        ssh alphha@localhost -p {environment?.ssh_port}
                      </code>
                    </div>
                  )}
                </div>
              ) : (
                <div className="w-full h-full">
                  {environment?.access_url ? (
                    <iframe
                      ref={iframeRef}
                      src={environment.access_url}
                      className="w-full h-full border-0"
                      title="Desktop"
                      sandbox="allow-same-origin allow-scripts allow-forms"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Monitor className="w-12 h-12 mb-3 text-gray-600" />
                      <p>Desktop connected on port {environment?.vnc_port}</p>
                      <p className="text-sm mt-2">Open VNC viewer to connect</p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Stop button overlay when running */}
          {isRunning && (
            <button
              onClick={onStopEnvironment}
              disabled={isStopping}
              className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 rounded-lg text-sm transition-colors"
            >
              {isStopping ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Stopping...
                </>
              ) : (
                'Stop Environment'
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
