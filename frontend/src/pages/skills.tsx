import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import { Shield, TrendingUp, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { skillsApi } from '@/services/api';

export default function Skills() {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();

  const { data: skills, isLoading: skillsLoading } = useQuery({
    queryKey: ['userSkills'],
    queryFn: skillsApi.getMySkills,
    enabled: isAuthenticated,
  });

  const { data: skillTree } = useQuery({
    queryKey: ['skillTree'],
    queryFn: skillsApi.getSkillTree,
    enabled: isAuthenticated,
  });

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations'],
    queryFn: skillsApi.getRecommendations,
    enabled: isAuthenticated,
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
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (skillsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Your Skills</h1>
        <p className="text-gray-400">
          Track your progress across different cybersecurity domains
        </p>
      </div>

      {/* Overall Progress */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Overall Progress</h2>
            <p className="text-gray-400">Your current skill level across all domains</p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-cyber-accent">
              {skills?.overall_level || 'Novice'}
            </p>
            <p className="text-sm text-gray-400">
              {((skills?.overall_proficiency || 0) / 5 * 100).toFixed(0)}% Complete
            </p>
          </div>
        </div>
        <div className="h-4 bg-cyber-darker rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyber-accent to-cyber-blue rounded-full transition-all duration-500"
            style={{ width: `${((skills?.overall_proficiency || 0) / 5) * 100}%` }}
          />
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Skill Domains */}
        <div className="lg:col-span-2">
          <h2 className="text-xl font-semibold text-white mb-4">Skill Domains</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {skillTree && Object.entries(skillTree).map(([key, domain]: [string, any]) => (
              <SkillDomainCard
                key={key}
                domain={domain}
                userSkills={skills?.skills || {}}
              />
            ))}
          </div>
        </div>

        {/* Recommendations Sidebar */}
        <div>
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-cyber-accent" />
              Focus Areas
            </h2>
            <p className="text-sm text-gray-400 mb-4">
              Based on your {recommendations?.career_goal?.replace(/_/g, ' ') || 'career'} goal
            </p>

            {recommendations?.recommendations?.length > 0 ? (
              <div className="space-y-3">
                {recommendations.recommendations.map((rec: any) => (
                  <div
                    key={rec.skill}
                    className="p-3 bg-cyber-darker rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white text-sm font-medium">
                        {rec.skill.replace(/_/g, ' ')}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        rec.recommended_focus
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {rec.recommended_focus ? 'Priority' : 'Improve'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <span>Current: {rec.current_level.toFixed(1)}</span>
                      <span>→</span>
                      <span>Target: {rec.target_level.toFixed(1)}</span>
                    </div>
                    <div className="mt-2 h-1.5 bg-cyber-dark rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyber-accent rounded-full"
                        style={{ width: `${(rec.current_level / rec.target_level) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">
                Complete some assessments to get personalized recommendations.
              </p>
            )}
          </div>

          {/* Skill Levels Legend */}
          <div className="mt-6 bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <h3 className="font-medium text-white mb-3">Skill Levels</h3>
            <div className="space-y-2 text-sm">
              {[
                { level: 0, label: 'Novice', color: 'bg-gray-500' },
                { level: 1, label: 'Beginner', color: 'bg-green-500' },
                { level: 2, label: 'Intermediate', color: 'bg-yellow-500' },
                { level: 3, label: 'Advanced', color: 'bg-orange-500' },
                { level: 4, label: 'Expert', color: 'bg-red-500' },
                { level: 5, label: 'Master', color: 'bg-purple-500' },
              ].map((item) => (
                <div key={item.level} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${item.color}`} />
                  <span className="text-gray-400">{item.label}</span>
                  <span className="text-gray-600">({item.level})</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SkillDomainCard({ domain, userSkills }: { domain: any; userSkills: Record<string, any> }) {
  // Calculate average proficiency for this domain
  const domainSkills = domain.skills || [];
  const userDomainSkills = domainSkills
    .map((skill: string) => userSkills[skill]?.proficiency_level || 0);
  const avgProficiency = userDomainSkills.length > 0
    ? userDomainSkills.reduce((a: number, b: number) => a + b, 0) / userDomainSkills.length
    : 0;

  return (
    <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-5 hover:border-cyber-accent/40 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-white">{domain.name}</h3>
          <p className="text-sm text-gray-400">{domainSkills.length} skills</p>
        </div>
        <Shield className="w-8 h-8 text-cyber-accent/50" />
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-gray-400">Progress</span>
          <span className="text-cyber-accent">{((avgProficiency / 5) * 100).toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
          <div
            className="h-full bg-cyber-accent rounded-full"
            style={{ width: `${(avgProficiency / 5) * 100}%` }}
          />
        </div>
      </div>

      {/* Individual Skills */}
      <div className="space-y-2">
        {domainSkills.slice(0, 4).map((skill: string) => {
          const userSkill = userSkills[skill];
          const proficiency = userSkill?.proficiency_level || 0;

          return (
            <div key={skill} className="flex items-center justify-between">
              <span className="text-sm text-gray-400 truncate">
                {skill.replace(/_/g, ' ')}
              </span>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((level) => (
                  <div
                    key={level}
                    className={`w-2 h-2 rounded-full ${
                      proficiency >= level ? 'bg-cyber-accent' : 'bg-cyber-darker'
                    }`}
                  />
                ))}
              </div>
            </div>
          );
        })}
        {domainSkills.length > 4 && (
          <p className="text-xs text-gray-500">+{domainSkills.length - 4} more skills</p>
        )}
      </div>
    </div>
  );
}
