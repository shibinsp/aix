import { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { Map, Trophy, Target, Loader2 } from 'lucide-react';
import { useLearningPath } from '@/hooks/useLearningPath';
import { useAuthStore } from '@/store/authStore';
import BoardGamePath from '@/components/progress/BoardGamePath';
import MilestoneDetailPanel from '@/components/progress/MilestoneDetailPanel';

export default function LearningPathPage() {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const { milestones, overallProgress, currentMilestone, completedCount, isLoading } = useLearningPath();
  const [selectedMilestoneId, setSelectedMilestoneId] = useState<string | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (hasHydrated && !isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Set initial selected milestone to current
  useEffect(() => {
    if (currentMilestone && !selectedMilestoneId) {
      setSelectedMilestoneId(currentMilestone.id);
    }
  }, [currentMilestone, selectedMilestoneId]);

  const selectedMilestone = milestones.find(m => m.id === selectedMilestoneId) || null;

  if (!hasHydrated || isLoading) {
    return (
      <div className="min-h-screen bg-cyber-darker flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Learning Path | CyberAIx</title>
        <meta name="description" content="Track your cybersecurity learning journey" />
      </Head>

      <div className="min-h-screen bg-cyber-darker">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-cyber-dark/95 backdrop-blur-sm border-b border-cyber-accent/20">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-cyber-accent/10 border border-cyber-accent/20">
                  <Map className="w-6 h-6 text-cyber-accent" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">Your Learning Journey</h1>
                  <p className="text-sm text-gray-400">
                    Progress from beginner to cybersecurity expert
                  </p>
                </div>
              </div>

              {/* Overall progress */}
              <div className="flex items-center gap-6">
                {/* Stats */}
                <div className="hidden md:flex items-center gap-6">
                  <div className="text-center">
                    <div className="flex items-center gap-2">
                      <Trophy className="w-5 h-5 text-yellow-400" />
                      <span className="text-2xl font-bold text-white">{completedCount}</span>
                    </div>
                    <p className="text-xs text-gray-500">Domains Mastered</p>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center gap-2">
                      <Target className="w-5 h-5 text-cyber-accent" />
                      <span className="text-2xl font-bold text-white">{milestones.length - completedCount}</span>
                    </div>
                    <p className="text-xs text-gray-500">Remaining</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-48">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-400">Overall Progress</span>
                    <span className="text-sm font-bold text-cyber-accent">{overallProgress}%</span>
                  </div>
                  <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyber-accent to-cyber-blue rounded-full transition-all duration-500"
                      style={{ width: `${overallProgress}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex h-[calc(100vh-85px)]">
          {/* Left: Board game path */}
          <div className="flex-1 overflow-y-auto p-8">
            <div className="max-w-4xl mx-auto">
              {/* Instructions */}
              <div className="mb-6 p-4 rounded-lg bg-cyber-dark/50 border border-cyber-accent/10">
                <p className="text-sm text-gray-400 text-center">
                  Click on any milestone to view details. Complete all objectives in a domain to unlock the next level.
                </p>
              </div>

              {/* Board game visualization */}
              <BoardGamePath
                milestones={milestones}
                selectedId={selectedMilestoneId || undefined}
                onMilestoneClick={setSelectedMilestoneId}
              />
            </div>
          </div>

          {/* Right: Detail panel */}
          <div className="w-96 border-l border-cyber-accent/20 bg-cyber-dark/50 hidden lg:block">
            <MilestoneDetailPanel milestone={selectedMilestone} />
          </div>
        </div>

        {/* Mobile detail panel (bottom sheet style) */}
        {selectedMilestone && (
          <div className="lg:hidden fixed bottom-0 left-0 right-0 max-h-[60vh] bg-cyber-dark border-t border-cyber-accent/20 rounded-t-2xl overflow-hidden z-20">
            <div className="h-1 w-12 bg-gray-600 rounded-full mx-auto my-3" />
            <div className="overflow-y-auto max-h-[calc(60vh-24px)]">
              <MilestoneDetailPanel milestone={selectedMilestone} />
            </div>
          </div>
        )}
      </div>
    </>
  );
}
