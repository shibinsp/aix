import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  TrendingUp,
  ArrowLeft,
  Users,
  BookOpen,
  Trophy,
  Clock,
  ChevronDown
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { api } from '@/services/api';

interface MemberProgress {
  id: string;
  username: string;
  email: string;
  overall_progress: number;
  courses_completed: number;
  total_courses: number;
  labs_completed: number;
  total_labs: number;
  time_spent_hours: number;
  last_activity: string;
}

interface BatchProgress {
  avg_progress: number;
  total_completions: number;
  total_members: number;
  active_members: number;
  members: MemberProgress[];
}

export default function BatchProgress() {
  const router = useRouter();
  const { orgId, batchId } = router.query;
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<'progress' | 'name' | 'activity'>('progress');

  useEffect(() => {
    if (orgId && batchId) {
      fetchProgress();
    }
  }, [orgId, batchId]);

  const fetchProgress = async () => {
    try {
      const res = await api.get(`/organizations/${orgId}/batches/${batchId}/progress`);
      setProgress(res.data);
    } catch (error) {
      setProgress({
        avg_progress: 0,
        total_completions: 0,
        total_members: 0,
        active_members: 0,
        members: []
      });
    } finally {
      setLoading(false);
    }
  };

  const sortedMembers = progress?.members.slice().sort((a, b) => {
    if (sortBy === 'progress') return b.overall_progress - a.overall_progress;
    if (sortBy === 'name') return a.username.localeCompare(b.username);
    return new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime();
  }) || [];

  return (
    <PortalLayout>
      <Link
        href={`/portal/${orgId}/batches/${batchId}`}
        className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Batch
      </Link>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Progress Tracking</h1>
          <p className="text-gray-400 mt-1">Monitor member progress and achievements</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-cyber-accent/10">
                  <TrendingUp className="w-5 h-5 text-cyber-accent" />
                </div>
                <span className="text-gray-400 text-sm">Avg Progress</span>
              </div>
              <p className="text-3xl font-bold text-white">{progress?.avg_progress || 0}%</p>
            </div>

            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <Users className="w-5 h-5 text-blue-400" />
                </div>
                <span className="text-gray-400 text-sm">Active Members</span>
              </div>
              <p className="text-3xl font-bold text-white">
                {progress?.active_members || 0}/{progress?.total_members || 0}
              </p>
            </div>

            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-yellow-500/10">
                  <Trophy className="w-5 h-5 text-yellow-400" />
                </div>
                <span className="text-gray-400 text-sm">Completions</span>
              </div>
              <p className="text-3xl font-bold text-white">{progress?.total_completions || 0}</p>
            </div>

            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                </div>
                <span className="text-gray-400 text-sm">Course Completion</span>
              </div>
              <p className="text-3xl font-bold text-white">
                {sortedMembers.length > 0
                  ? Math.round(
                      sortedMembers.reduce((sum, m) => sum + (m.courses_completed / Math.max(m.total_courses, 1)) * 100, 0) /
                        sortedMembers.length
                    )
                  : 0}%
              </p>
            </div>
          </div>

          {/* Sort Controls */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-gray-400 text-sm">
              {sortedMembers.length} members
            </p>
            <div className="relative">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="appearance-none px-4 py-2 pr-10 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white text-sm focus:outline-none focus:border-cyber-accent cursor-pointer"
              >
                <option value="progress">Sort by Progress</option>
                <option value="name">Sort by Name</option>
                <option value="activity">Sort by Activity</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>
          </div>

          {/* Progress Table */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden">
            {sortedMembers.length === 0 ? (
              <div className="text-center py-12">
                <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No members to track</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-cyber-accent/10">
                      <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Member</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Overall Progress</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Courses</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Labs</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Time Spent</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Last Activity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyber-accent/10">
                    {sortedMembers.map((member, index) => (
                      <tr key={member.id} className="hover:bg-cyber-accent/5 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-cyber-accent/20 flex items-center justify-center text-sm">
                              {index < 3 ? (
                                <span className={
                                  index === 0 ? 'text-yellow-400' :
                                  index === 1 ? 'text-gray-400' :
                                  'text-amber-600'
                                }>
                                  {index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉'}
                                </span>
                              ) : (
                                <span className="text-cyber-accent font-medium">
                                  {member.username.charAt(0).toUpperCase()}
                                </span>
                              )}
                            </div>
                            <div>
                              <p className="text-white font-medium">{member.username}</p>
                              <p className="text-xs text-gray-500">{member.email}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  member.overall_progress >= 80 ? 'bg-green-500' :
                                  member.overall_progress >= 50 ? 'bg-yellow-500' :
                                  'bg-red-500'
                                }`}
                                style={{ width: `${member.overall_progress}%` }}
                              />
                            </div>
                            <span className="text-white font-medium">{member.overall_progress}%</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-white">
                            {member.courses_completed}/{member.total_courses}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-white">
                            {member.labs_completed}/{member.total_labs}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-1.5 text-gray-400">
                            <Clock className="w-4 h-4" />
                            <span>{member.time_spent_hours}h</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-gray-400 text-sm">
                          {member.last_activity
                            ? new Date(member.last_activity).toLocaleDateString()
                            : 'Never'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </PortalLayout>
  );
}
