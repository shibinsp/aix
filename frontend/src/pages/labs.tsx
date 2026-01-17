import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Terminal,
  Monitor,
  Clock,
  Trophy,
  Play,
  Square,
  Flag,
  Loader2,
  ChevronLeft,
  BookOpen,
  Circle,
  Lightbulb,
  Send,
  ExternalLink
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { labsApi } from '@/services/api';
import ReactMarkdown from 'react-markdown';

const LAB_TYPES = ['tutorial', 'challenge', 'ctf', 'simulation'];
const DIFFICULTIES = ['beginner', 'intermediate', 'advanced', 'expert'];

export default function Labs() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [labType, setLabType] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [selectedLab, setSelectedLab] = useState<any>(null);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [flagInput, setFlagInput] = useState('');
  const [flagResult, setFlagResult] = useState<any>(null);
  const [desktopLoading, setDesktopLoading] = useState(true);

  const { data: labs, isLoading } = useQuery({
    queryKey: ['labs', { labType, difficulty }],
    queryFn: () => labsApi.list({ lab_type: labType, difficulty }),
    enabled: isAuthenticated,
  });

  const startLabMutation = useMutation({
    mutationFn: (labId: string) => {
      console.log('Starting lab with ID:', labId);
      return labsApi.startSession(labId);
    },
    onSuccess: (data) => {
      console.log('Lab started successfully:', data);
      setActiveSession(data);
    },
    onError: (error: any) => {
      console.error('Failed to start lab:', error);
      alert(`Failed to start lab: ${error?.response?.data?.detail || error.message || 'Unknown error'}`);
    },
  });

  const submitFlagMutation = useMutation({
    mutationFn: ({ sessionId, flag }: { sessionId: string; flag: string }) =>
      labsApi.submitFlag(sessionId, flag),
    onSuccess: (data) => {
      setFlagResult(data);
      if (data.correct) {
        queryClient.invalidateQueries({ queryKey: ['labSession'] });
      }
    },
  });

  const stopLabMutation = useMutation({
    mutationFn: (sessionId: string) => labsApi.stopSession(sessionId),
    onSuccess: () => {
      setActiveSession(null);
    },
  });

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const handleStartLab = async (lab: any) => {
    console.log('handleStartLab called with lab:', lab);
    if (!lab || !lab.id) {
      console.error('Invalid lab object:', lab);
      alert('Error: Invalid lab selected');
      return;
    }

    try {
      setSelectedLab(lab);
      setDesktopLoading(true);

      const result = await labsApi.startSession(lab.id);
      console.log('Lab started:', result);
      setActiveSession(result);
    } catch (error: any) {
      console.error('Failed to start lab:', error);
      alert('Failed to start lab: ' + (error?.response?.data?.detail || error.message || 'Unknown error'));
    }
  };

  const handleBackToList = () => {
    if (activeSession) {
      stopLabMutation.mutate(activeSession.id);
    }
    setSelectedLab(null);
    setActiveSession(null);
    setFlagResult(null);
    setFlagInput('');
    setDesktopLoading(true);
  };

  const handleSubmitFlag = () => {
    if (!flagInput.trim() || !activeSession?.id) return;
    submitFlagMutation.mutate({
      sessionId: activeSession.id,
      flag: flagInput,
    });
    setFlagInput('');
  };

  // Lab Workspace View (when lab is active)
  if (selectedLab && activeSession) {
    return (
      <div className="flex h-full bg-cyber-darker">
        {/* Left Panel - Instructions */}
        <div className="w-[450px] flex flex-col border-r border-cyber-accent/20 bg-cyber-dark">
          {/* Header */}
          <div className="p-4 border-b border-cyber-accent/20">
            <button
              onClick={handleBackToList}
              className="flex items-center gap-2 text-gray-400 hover:text-white mb-3 text-sm"
            >
              <ChevronLeft className="w-4 h-4" />
              Back to Labs
            </button>
            <h1 className="text-xl font-bold text-white">{selectedLab.title}</h1>
            <div className="flex items-center gap-3 mt-2 text-sm">
              <span className={`px-2 py-0.5 rounded ${getDifficultyColor(selectedLab.difficulty)}`}>
                {selectedLab.difficulty}
              </span>
              <span className="text-gray-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> {selectedLab.estimated_time} min
              </span>
              <span className="text-gray-500 flex items-center gap-1">
                <Trophy className="w-3 h-3" /> {selectedLab.points} pts
              </span>
            </div>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto">
            {/* Status */}
            <div className="p-4 border-b border-cyber-accent/10">
              <div className="flex items-center gap-2 text-green-400 text-sm">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                Lab Running
              </div>
            </div>

            {/* Objectives */}
            {selectedLab.objectives?.length > 0 && (
              <div className="p-4 border-b border-cyber-accent/10">
                <h3 className="text-sm font-semibold text-cyber-accent mb-3 flex items-center gap-2">
                  <BookOpen className="w-4 h-4" />
                  OBJECTIVES
                </h3>
                <ul className="space-y-2">
                  {selectedLab.objectives.map((obj: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <Circle className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-300">{obj}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Instructions */}
            <div className="p-4 border-b border-cyber-accent/10">
              <h3 className="text-sm font-semibold text-cyber-accent mb-3">INSTRUCTIONS</h3>
              <div className="prose prose-invert prose-sm max-w-none text-gray-300">
                {selectedLab.instructions ? (
                  <ReactMarkdown>{selectedLab.instructions}</ReactMarkdown>
                ) : (
                  <p>Complete the objectives above to capture the flags.</p>
                )}
              </div>
            </div>

            {/* Hints */}
            {selectedLab.hints?.length > 0 && (
              <div className="p-4 border-b border-cyber-accent/10">
                <h3 className="text-sm font-semibold text-cyber-accent mb-3 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4" />
                  HINTS
                </h3>
                <div className="space-y-2">
                  {selectedLab.hints.map((hint: string, i: number) => (
                    <details key={i} className="bg-cyber-darker rounded">
                      <summary className="px-3 py-2 cursor-pointer text-sm text-gray-400 hover:text-white">
                        Hint {i + 1}
                      </summary>
                      <p className="px-3 pb-2 text-sm text-gray-300">{hint}</p>
                    </details>
                  ))}
                </div>
              </div>
            )}

            {/* Flag Submission */}
            <div className="p-4">
              <h3 className="text-sm font-semibold text-cyber-accent mb-3 flex items-center gap-2">
                <Flag className="w-4 h-4" />
                SUBMIT FLAG
              </h3>
              
              {flagResult && (
                <div className={`mb-3 p-2 rounded text-sm ${
                  flagResult.correct 
                    ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
                    : 'bg-red-500/10 border border-red-500/20 text-red-400'
                }`}>
                  {flagResult.message}
                </div>
              )}

              <div className="flex gap-2">
                <input
                  type="text"
                  value={flagInput}
                  onChange={(e) => setFlagInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmitFlag()}
                  placeholder="FLAG{...}"
                  className="flex-1 px-3 py-2 bg-cyber-darker border border-gray-700 rounded text-white text-sm font-mono placeholder-gray-500 focus:outline-none focus:border-cyber-accent"
                />
                <button
                  onClick={handleSubmitFlag}
                  disabled={!flagInput.trim() || submitFlagMutation.isPending}
                  className="px-3 py-2 bg-cyber-accent text-cyber-dark rounded hover:bg-cyber-accent/90 disabled:opacity-50"
                >
                  {submitFlagMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>

              {activeSession?.flags_captured?.length > 0 && (
                <div className="mt-3 text-xs text-green-400">
                  ✓ Captured: {activeSession.flags_captured.join(', ')}
                </div>
              )}
            </div>
          </div>

          {/* Stop Button */}
          <div className="p-4 border-t border-cyber-accent/20">
            <button
              onClick={() => stopLabMutation.mutate(activeSession.id)}
              disabled={stopLabMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
            >
              {stopLabMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Square className="w-4 h-4" />
              )}
              Stop Lab
            </button>
          </div>
        </div>

        {/* Right Panel - Desktop Environment */}
        <div className="flex-1 flex flex-col">
          {/* Desktop Header */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-700">
            <div className="flex items-center gap-2 text-sm">
              <Monitor className="w-4 h-4 text-cyan-400" />
              <span className="text-gray-300">Desktop Environment</span>
            </div>
            {activeSession?.access_url && (
              <a
                href={activeSession.access_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300"
              >
                <ExternalLink className="w-3 h-3" />
                Open in new tab
              </a>
            )}
          </div>

          {/* Desktop iframe */}
          <div className="flex-1 relative bg-[#0d1117]">
            {desktopLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-[#0d1117] z-10">
                <div className="text-center">
                  <Loader2 className="w-10 h-10 text-cyan-400 animate-spin mx-auto mb-3" />
                  <p className="text-gray-400 text-sm">Loading desktop environment...</p>
                </div>
              </div>
            )}
            {activeSession?.access_url ? (
              <iframe
                src={activeSession.access_url}
                className="w-full h-full border-0"
                onLoad={() => setDesktopLoading(false)}
                allow="clipboard-read; clipboard-write"
                title="Lab Desktop Environment"
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Terminal className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">Desktop environment not available</p>
                  <p className="text-gray-500 text-sm mt-1">Please try restarting the lab</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Lab List View
  return (
    <div className="flex h-full">
      {/* Lab List */}
      <div className="w-96 bg-cyber-dark border-r border-cyber-accent/20 flex flex-col">
        <div className="p-4 border-b border-cyber-accent/20">
          <h2 className="text-xl font-semibold text-white mb-4">Practice Labs</h2>
          <div className="space-y-3">
            <select
              value={labType}
              onChange={(e) => setLabType(e.target.value)}
              className="w-full px-3 py-2 bg-cyber-darker border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-cyber-accent"
            >
              <option value="">All Types</option>
              {LAB_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="w-full px-3 py-2 bg-cyber-darker border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-cyber-accent"
            >
              <option value="">All Difficulties</option>
              {DIFFICULTIES.map((diff) => (
                <option key={diff} value={diff}>
                  {diff.charAt(0).toUpperCase() + diff.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
            </div>
          ) : labs?.length > 0 ? (
            <div className="space-y-2">
              {labs.map((lab: any) => (
                <LabCard
                  key={lab.id}
                  lab={lab}
                  isSelected={selectedLab?.id === lab.id}
                  onSelect={() => setSelectedLab(lab)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">No labs available</div>
          )}
        </div>
      </div>

      {/* Lab Preview */}
      <div className="flex-1 flex flex-col">
        {selectedLab ? (
          <>
            <div className="p-6 border-b border-cyber-accent/20 bg-cyber-dark">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-1 rounded ${getDifficultyColor(selectedLab.difficulty)}`}>
                      {selectedLab.difficulty}
                    </span>
                    <span className="text-xs text-gray-500">{selectedLab.lab_type}</span>
                  </div>
                  <h1 className="text-2xl font-bold text-white mb-2">{selectedLab.title}</h1>
                  <p className="text-gray-400">{selectedLab.description}</p>
                </div>
                <button
                  onClick={() => handleStartLab(selectedLab)}
                  disabled={startLabMutation.isPending}
                  className="flex items-center gap-2 px-6 py-3 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
                >
                  {startLabMutation.isPending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Play className="w-5 h-5" />
                  )}
                  Start Lab
                </button>
              </div>
              <div className="flex items-center gap-6 mt-4 text-sm text-gray-400">
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  <span>{selectedLab.estimated_time} min</span>
                </div>
                <div className="flex items-center gap-1">
                  <Trophy className="w-4 h-4" />
                  <span>{selectedLab.points} pts</span>
                </div>
                <div className="flex items-center gap-1">
                  <Flag className="w-4 h-4" />
                  <span>{selectedLab.flags?.length || 0} flags</span>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {selectedLab.objectives?.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Objectives</h3>
                  <ul className="space-y-2">
                    {selectedLab.objectives.map((obj: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-gray-300">
                        <span className="text-cyber-accent">•</span>
                        {obj}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {selectedLab.instructions && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Instructions</h3>
                  <div className="prose prose-invert prose-sm max-w-none bg-cyber-darker p-4 rounded-lg">
                    <ReactMarkdown>{selectedLab.instructions}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Terminal className="w-16 h-16 text-cyber-accent mx-auto mb-4" />
              <h2 className="text-xl font-medium text-white mb-2">Select a Lab</h2>
              <p className="text-gray-400">Choose a lab from the list to view details and start practicing.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function LabCard({ lab, isSelected, onSelect }: { lab: any; isSelected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full p-3 rounded-lg text-left transition-colors ${
        isSelected
          ? 'bg-cyber-accent/20 border border-cyber-accent/40'
          : 'bg-cyber-darker hover:bg-cyber-darker/80 border border-transparent'
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <Terminal className="w-4 h-4 text-green-400" />
        <span className={`text-xs px-1.5 py-0.5 rounded ${getDifficultyColor(lab.difficulty)}`}>
          {lab.difficulty}
        </span>
      </div>
      <h3 className="font-medium text-white text-sm truncate">{lab.title}</h3>
      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
        <span>{lab.estimated_time} min</span>
        <span>{lab.points} pts</span>
      </div>
    </button>
  );
}

function getDifficultyColor(difficulty: string) {
  const colors: Record<string, string> = {
    beginner: 'bg-green-500/20 text-green-400',
    intermediate: 'bg-yellow-500/20 text-yellow-400',
    advanced: 'bg-orange-500/20 text-orange-400',
    expert: 'bg-red-500/20 text-red-400',
  };
  return colors[difficulty] || colors.beginner;
}
