import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, Search, UserPlus, ArrowLeft, Loader2, MoreVertical,
  Trash2, X, TrendingUp, BookOpen, Target, Award, ArrowUp, ArrowDown
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { batchesApi, organizationsApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';

interface BatchMember {
  id: string;
  user_id: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    avatar_url?: string;
  };
  enrolled_at: string;
  completed_at?: string;
  progress_percent: number;
  courses_completed: string[];
  labs_completed: string[];
}

type SortField = 'name' | 'progress' | 'courses' | 'labs' | 'enrolled';
type SortDirection = 'asc' | 'desc';

export default function BatchMembers() {
  const router = useRouter();
  const { batchId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState<SortField>('progress');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

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
    },
  });

  if (!isAuthenticated) return null;

  const batch = batchData?.batch || batchData;
  const members = membersData?.items || membersData || [];

  // Sort members
  const sortedMembers = [...members].sort((a: BatchMember, b: BatchMember) => {
    let aVal: any, bVal: any;
    switch (sortField) {
      case 'name':
        aVal = a.user?.full_name || a.user?.email || '';
        bVal = b.user?.full_name || b.user?.email || '';
        break;
      case 'progress':
        aVal = a.progress_percent;
        bVal = b.progress_percent;
        break;
      case 'courses':
        aVal = a.courses_completed?.length || 0;
        bVal = b.courses_completed?.length || 0;
        break;
      case 'labs':
        aVal = a.labs_completed?.length || 0;
        bVal = b.labs_completed?.length || 0;
        break;
      case 'enrolled':
        aVal = new Date(a.enrolled_at).getTime();
        bVal = new Date(b.enrolled_at).getTime();
        break;
      default:
        return 0;
    }
    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1;
    }
    return aVal < bVal ? 1 : -1;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ?
      <ArrowUp className="w-3 h-3" /> :
      <ArrowDown className="w-3 h-3" />;
  };

  return (
    <AdminLayout title="Batch Members" subtitle={batch?.name}>
      {/* Header Actions */}
      <div className="flex justify-end mb-8">
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-500/90 transition-colors font-medium"
        >
          <UserPlus className="w-5 h-5" />
          Add Members
        </button>
      </div>

      {/* Search */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search members..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent/50"
          />
        </div>
      </div>

      {/* Members Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
        </div>
      ) : sortedMembers.length > 0 ? (
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cyber-accent/10">
                <th
                  className="text-left px-6 py-4 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                  onClick={() => handleSort('name')}
                >
                  <div className="flex items-center gap-1">
                    Member <SortIcon field="name" />
                  </div>
                </th>
                <th
                  className="text-left px-6 py-4 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                  onClick={() => handleSort('progress')}
                >
                  <div className="flex items-center gap-1">
                    Progress <SortIcon field="progress" />
                  </div>
                </th>
                <th
                  className="text-left px-6 py-4 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                  onClick={() => handleSort('courses')}
                >
                  <div className="flex items-center gap-1">
                    Courses <SortIcon field="courses" />
                  </div>
                </th>
                <th
                  className="text-left px-6 py-4 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                  onClick={() => handleSort('labs')}
                >
                  <div className="flex items-center gap-1">
                    Labs <SortIcon field="labs" />
                  </div>
                </th>
                <th
                  className="text-left px-6 py-4 text-sm font-medium text-gray-400 cursor-pointer hover:text-white"
                  onClick={() => handleSort('enrolled')}
                >
                  <div className="flex items-center gap-1">
                    Enrolled <SortIcon field="enrolled" />
                  </div>
                </th>
                <th className="text-right px-6 py-4 text-sm font-medium text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedMembers.map((member: BatchMember, i: number) => (
                <MemberRow
                  key={member.id}
                  member={member}
                  rank={i + 1}
                  onRemove={() => {
                    const userName = member.user?.full_name || member.user?.email || 'this member';
                    if (confirm(`Remove ${userName} from this batch?`)) {
                      removeMemberMutation.mutate(member.user_id);
                    }
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No members found</h3>
          <p className="text-gray-400 mb-4">Add members to this batch to get started.</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
          >
            Add Members
          </button>
        </div>
      )}

      {/* Add Members Modal */}
      {showAddModal && (
        <AddMembersModal
          batchId={batchId as string}
          organizationId={batch?.organization_id}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            queryClient.invalidateQueries({ queryKey: ['batch-members', batchId] });
          }}
        />
      )}
    </AdminLayout>
  );
}

function MemberRow({
  member,
  rank,
  onRemove,
}: {
  member: BatchMember;
  rank: number;
  onRemove: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const progress = Math.round(member.progress_percent || 0);

  // Handle cases where user data might not be populated
  const user = member.user || { id: '', email: 'Unknown', full_name: '' };
  const displayName = user.full_name || user.email || 'Unknown';
  const initial = displayName[0]?.toUpperCase() || 'U';

  return (
    <tr className="border-b border-cyber-accent/10 hover:bg-cyber-darker/50">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
            rank === 1 ? 'bg-yellow-500/20 text-yellow-400' :
            rank === 2 ? 'bg-gray-400/20 text-gray-300' :
            rank === 3 ? 'bg-orange-500/20 text-orange-400' :
            'bg-cyber-darker text-gray-500'
          }`}>
            {rank}
          </div>
          <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-10 h-10 rounded-full" />
            ) : (
              <span className="text-cyber-accent font-medium">
                {initial}
              </span>
            )}
          </div>
          <div>
            <p className="text-white font-medium">{user.full_name || 'Unnamed'}</p>
            <p className="text-sm text-gray-500">{user.email}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-24 h-2 bg-cyber-darker rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                progress >= 80 ? 'bg-green-500' :
                progress >= 50 ? 'bg-yellow-500' :
                'bg-cyber-accent'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-white font-medium">{progress}%</span>
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-1 text-gray-300">
          <BookOpen className="w-4 h-4 text-gray-500" />
          <span>{member.courses_completed?.length || 0}</span>
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-1 text-gray-300">
          <Target className="w-4 h-4 text-gray-500" />
          <span>{member.labs_completed?.length || 0}</span>
        </div>
      </td>
      <td className="px-6 py-4 text-sm text-gray-400">
        {new Date(member.enrolled_at).toLocaleDateString()}
      </td>
      <td className="px-6 py-4 text-right">
        <div className="relative inline-block">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 hover:bg-cyber-darker rounded-lg transition-colors"
          >
            <MoreVertical className="w-5 h-5 text-gray-400" />
          </button>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 top-8 z-20 bg-cyber-darker border border-cyber-accent/20 rounded-lg py-1 min-w-[120px] shadow-xl">
                <button
                  onClick={() => { setShowMenu(false); onRemove(); }}
                  className="w-full px-3 py-2 text-left text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" /> Remove
                </button>
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

function AddMembersModal({
  batchId,
  organizationId,
  onClose,
  onSuccess,
}: {
  batchId: string;
  organizationId?: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');

  const { data: orgMembersData, isLoading } = useQuery({
    queryKey: ['organization-members', organizationId, { search }],
    queryFn: () => organizationsApi.getMembers(organizationId as string, { search: search || undefined }),
    enabled: !!organizationId,
  });

  const { data: batchMembersData } = useQuery({
    queryKey: ['batch-members', batchId],
    queryFn: () => batchesApi.getMembers(batchId),
    enabled: !!batchId,
  });

  const addMembersMutation = useMutation({
    mutationFn: (userIds: string[]) => batchesApi.addMembers(batchId, { user_ids: userIds }),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to add members');
    },
  });

  const orgMembers = orgMembersData?.items || orgMembersData || [];
  const batchMemberIds = new Set((batchMembersData?.items || batchMembersData || []).map((m: any) => m.user_id));
  const availableMembers = orgMembers.filter((m: any) => !batchMemberIds.has(m.user_id));

  const toggleUser = (userId: string) => {
    setSelectedUsers(prev =>
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleSubmit = () => {
    if (selectedUsers.length === 0) {
      setError('Please select at least one member');
      return;
    }
    addMembersMutation.mutate(selectedUsers);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-6 max-w-lg w-full mx-4 shadow-xl max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-white">Add Members to Batch</h2>
          <button onClick={onClose} className="p-1 hover:bg-cyber-darker rounded-lg">
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
            className="w-full pl-10 pr-4 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent/50"
          />
        </div>

        <div className="flex-1 overflow-y-auto mb-4">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-cyber-accent animate-spin" />
            </div>
          ) : availableMembers.length > 0 ? (
            <div className="space-y-2">
              {availableMembers.map((member: any) => (
                <label
                  key={member.user_id}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedUsers.includes(member.user_id)
                      ? 'border-cyber-accent bg-cyber-accent/10'
                      : 'border-cyber-accent/20 hover:border-cyber-accent/40'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedUsers.includes(member.user_id)}
                    onChange={() => toggleUser(member.user_id)}
                    className="sr-only"
                  />
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    selectedUsers.includes(member.user_id)
                      ? 'border-cyber-accent bg-cyber-accent'
                      : 'border-gray-500'
                  }`}>
                    {selectedUsers.includes(member.user_id) && (
                      <svg className="w-3 h-3 text-cyber-dark" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <div className="w-8 h-8 rounded-full bg-cyber-accent/20 flex items-center justify-center">
                    <span className="text-cyber-accent text-sm font-medium">
                      {(member.user?.full_name || member.user?.email || 'U')[0].toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{member.user?.full_name || 'Unnamed'}</p>
                    <p className="text-sm text-gray-500 truncate">{member.user?.email || 'Unknown'}</p>
                  </div>
                </label>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No available members to add</p>
            </div>
          )}
        </div>

        {error && (
          <p className="text-red-400 text-sm mb-4">{error}</p>
        )}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-cyber-accent/30 text-gray-300 rounded-lg hover:bg-cyber-darker transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={selectedUsers.length === 0 || addMembersMutation.isPending}
            className="flex-1 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
          >
            {addMembersMutation.isPending ? 'Adding...' : `Add ${selectedUsers.length} Member${selectedUsers.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}
