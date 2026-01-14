import { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Users, Search, Loader2, ArrowLeft, UserPlus, X,
  BookOpen, Award, TrendingUp, Trash2
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { batchesApi, organizationsApi } from '@/services/api';
import OrgLayout from '@/components/common/OrgLayout';

interface BatchMember {
  id: string;
  user_id: string;
  user: {
    id: string;
    email: string;
    full_name?: string;
    username?: string;
  };
  enrolled_at: string;
  progress_percent: number;
  courses_completed: string[];
  labs_completed: string[];
}

export default function OrgBatchMembers() {
  const router = useRouter();
  const { orgId, batchId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  const { data: batchData } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => batchesApi.get(batchId as string),
    enabled: isAuthenticated && !!batchId,
  });

  const { data: membersData, isLoading } = useQuery({
    queryKey: ['batch-members', batchId, { search }],
    queryFn: () => batchesApi.getMembers(batchId as string, { search: search || undefined }),
    enabled: isAuthenticated && !!batchId,
  });

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) => batchesApi.removeMember(batchId as string, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch-members', batchId] });
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
    },
  });

  const batch = batchData?.batch || batchData;
  const members = membersData?.items || membersData || [];
  const currentUserRole = user?.org_role?.toLowerCase();
  const canManageMembers = currentUserRole === 'owner' || currentUserRole === 'admin';

  return (
    <OrgLayout title="Batch Members" subtitle={batch?.name}>
      {/* Back Link */}
      <div className="mb-6">
        <Link
          href={`/org/${orgId}/batches/${batchId}`}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Batch Dashboard
        </Link>
      </div>

      {/* Header Actions */}
      <div className="flex flex-col md:flex-row justify-between gap-4 mb-8">
        <div className="flex-1 max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search members..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#0d1520] border border-blue-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>
        {canManageMembers && (
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
          >
            <UserPlus className="w-5 h-5" />
            Add Members
          </button>
        )}
      </div>

      {/* Members Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
        </div>
      ) : members.length > 0 ? (
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-blue-500/10">
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Member</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Progress</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Courses</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Labs</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Enrolled</th>
                {canManageMembers && (
                  <th className="text-right px-6 py-4 text-sm font-medium text-gray-400">Actions</th>
                )}
              </tr>
            </thead>
            <tbody>
              {members.map((member: BatchMember) => (
                <tr key={member.id} className="border-b border-blue-500/10 hover:bg-blue-500/5">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <span className="text-blue-400 font-medium">
                          {(member.user?.full_name || member.user?.email || 'U')[0].toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-white font-medium">
                          {member.user?.full_name || member.user?.username || 'Unknown'}
                        </p>
                        <p className="text-sm text-gray-500">{member.user?.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 max-w-[100px] h-2 bg-[#0a0a0f] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${member.progress_percent || 0}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-400">{member.progress_percent || 0}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-gray-400">
                      <BookOpen className="w-4 h-4" />
                      <span>{member.courses_completed?.length || 0}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 text-gray-400">
                      <Award className="w-4 h-4" />
                      <span>{member.labs_completed?.length || 0}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-400">
                    {new Date(member.enrolled_at).toLocaleDateString()}
                  </td>
                  {canManageMembers && (
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => {
                          if (confirm('Remove this member from the batch?')) {
                            removeMemberMutation.mutate(member.user_id);
                          }
                        }}
                        className="p-2 hover:bg-red-500/10 rounded-lg transition-colors text-gray-400 hover:text-red-400"
                        title="Remove from batch"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 bg-[#0d1520] rounded-xl border border-blue-500/20">
          <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No members in this batch</h3>
          <p className="text-gray-400 mb-4">
            {search ? 'No members match your search' : 'Add organization members to this batch'}
          </p>
          {canManageMembers && (
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
            >
              <UserPlus className="w-4 h-4" />
              Add Members
            </button>
          )}
        </div>
      )}

      {/* Add Members Modal */}
      {showAddModal && (
        <AddMembersModal
          orgId={orgId as string}
          batchId={batchId as string}
          existingMemberIds={members.map((m: BatchMember) => m.user_id)}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            queryClient.invalidateQueries({ queryKey: ['batch-members', batchId] });
            queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
          }}
        />
      )}
    </OrgLayout>
  );
}

function AddMembersModal({
  orgId,
  batchId,
  existingMemberIds,
  onClose,
  onSuccess,
}: {
  orgId: string;
  batchId: string;
  existingMemberIds: string[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { isAuthenticated } = useAuthStore();
  const [selected, setSelected] = useState<string[]>([]);
  const [search, setSearch] = useState('');

  const { data: orgMembersData, isLoading } = useQuery({
    queryKey: ['organization-members', orgId],
    queryFn: () => organizationsApi.getMembers(orgId),
    enabled: isAuthenticated,
  });

  const addMembersMutation = useMutation({
    mutationFn: (userIds: string[]) => batchesApi.addMembers(batchId, { user_ids: userIds }),
    onSuccess: () => onSuccess(),
  });

  const orgMembers = (orgMembersData?.items || orgMembersData || [])
    .filter((m: any) => !existingMemberIds.includes(m.user_id));

  const filteredMembers = orgMembers.filter((m: any) => {
    const searchLower = search.toLowerCase();
    return (
      m.user?.full_name?.toLowerCase().includes(searchLower) ||
      m.user?.email?.toLowerCase().includes(searchLower) ||
      m.user?.username?.toLowerCase().includes(searchLower)
    );
  });

  const toggleMember = (userId: string) => {
    setSelected((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#0d1520] rounded-2xl border border-blue-500/30 p-6 max-w-lg w-full mx-4 shadow-xl max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-white">Add Members to Batch</h2>
          <button onClick={onClose} className="p-1 hover:bg-blue-500/10 rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search organization members..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>

        <div className="flex-1 overflow-y-auto mb-4">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
            </div>
          ) : filteredMembers.length > 0 ? (
            <div className="space-y-2">
              {filteredMembers.map((member: any) => (
                <label
                  key={member.user_id}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selected.includes(member.user_id)
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-blue-500/20 hover:border-blue-500/40'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(member.user_id)}
                    onChange={() => toggleMember(member.user_id)}
                    className="sr-only"
                  />
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                    selected.includes(member.user_id)
                      ? 'border-blue-500 bg-blue-500'
                      : 'border-gray-500'
                  }`}>
                    {selected.includes(member.user_id) && (
                      <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-blue-400 text-sm font-medium">
                      {(member.user?.full_name || member.user?.email || 'U')[0].toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">
                      {member.user?.full_name || member.user?.username || 'Unknown'}
                    </p>
                    <p className="text-xs text-gray-500 truncate">{member.user?.email}</p>
                  </div>
                </label>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">
                {orgMembers.length === 0
                  ? 'All organization members are already in this batch'
                  : 'No members match your search'}
              </p>
            </div>
          )}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-blue-500/30 text-gray-300 rounded-lg hover:bg-blue-500/10 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => addMembersMutation.mutate(selected)}
            disabled={selected.length === 0 || addMembersMutation.isPending}
            className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium disabled:opacity-50"
          >
            Add {selected.length} Member{selected.length !== 1 ? 's' : ''}
          </button>
        </div>
      </div>
    </div>
  );
}
