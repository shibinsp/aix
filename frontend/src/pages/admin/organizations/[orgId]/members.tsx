import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, Search, UserPlus, ArrowLeft, Loader2, MoreVertical,
  Mail, Shield, Trash2, Edit, X, Check, AlertCircle
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi, invitationsApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';
import Link from 'next/link';

interface Member {
  id: string;
  user_id: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    avatar_url?: string;
    is_active: boolean;
  };
  org_role: string;
  is_active: boolean;
  joined_at: string;
}

const roleOptions = [
  { value: 'owner', label: 'Owner', description: 'Full control over the organization' },
  { value: 'admin', label: 'Admin', description: 'Manage members and batches' },
  { value: 'instructor', label: 'Instructor', description: 'Manage courses and students' },
  { value: 'member', label: 'Member', description: 'Access assigned courses' },
];

const roleColors: Record<string, string> = {
  owner: 'bg-yellow-500/20 text-yellow-400',
  admin: 'bg-blue-500/20 text-blue-400',
  instructor: 'bg-purple-500/20 text-purple-400',
  member: 'bg-gray-500/20 text-gray-400',
};

export default function OrganizationMembers() {
  const router = useRouter();
  const { orgId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const [search, setSearch] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [editingMember, setEditingMember] = useState<Member | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const { data: orgData } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsApi.get(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  const { data: membersData, isLoading } = useQuery({
    queryKey: ['organization-members', orgId, { search }],
    queryFn: () => organizationsApi.getMembers(orgId as string, { search: search || undefined }),
    enabled: isAuthenticated && !!orgId,
  });

  const updateMemberMutation = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: any }) =>
      organizationsApi.updateMember(orgId as string, userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-members', orgId] });
      setEditingMember(null);
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) => organizationsApi.removeMember(orgId as string, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-members', orgId] });
    },
  });

  if (!isAuthenticated) return null;

  const members = membersData?.items || membersData || [];

  return (
    <AdminLayout title="Members" subtitle={orgData?.name}>
      {/* Header Actions */}
      <div className="flex justify-end mb-8">
        <button
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-500/90 transition-colors font-medium"
        >
          <UserPlus className="w-5 h-5" />
          Invite Members
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
      ) : members.length > 0 ? (
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cyber-accent/10">
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Member</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Role</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Status</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Joined</th>
                <th className="text-right px-6 py-4 text-sm font-medium text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member: Member) => (
                <MemberRow
                  key={member.id}
                  member={member}
                  onEdit={() => setEditingMember(member)}
                  onRemove={() => {
                    if (confirm(`Remove ${member.user.full_name || member.user.email} from the organization?`)) {
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
          <p className="text-gray-400 mb-4">Invite members to get started.</p>
          <button
            onClick={() => setShowInviteModal(true)}
            className="px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
          >
            Invite Members
          </button>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <InviteModal
          orgId={orgId as string}
          onClose={() => setShowInviteModal(false)}
          onSuccess={() => {
            setShowInviteModal(false);
            queryClient.invalidateQueries({ queryKey: ['organization-members', orgId] });
          }}
        />
      )}

      {/* Edit Role Modal */}
      {editingMember && (
        <EditRoleModal
          member={editingMember}
          onClose={() => setEditingMember(null)}
          onSave={(role) => {
            updateMemberMutation.mutate({
              userId: editingMember.user_id,
              data: { org_role: role },
            });
          }}
          isLoading={updateMemberMutation.isPending}
        />
      )}
    </AdminLayout>
  );
}

function MemberRow({
  member,
  onEdit,
  onRemove,
}: {
  member: Member;
  onEdit: () => void;
  onRemove: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <tr className="border-b border-cyber-accent/10 hover:bg-cyber-darker/50">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center">
            {member.user.avatar_url ? (
              <img src={member.user.avatar_url} alt="" className="w-10 h-10 rounded-full" />
            ) : (
              <span className="text-cyber-accent font-medium">
                {(member.user?.full_name || member.user?.email || 'U')[0].toUpperCase()}
              </span>
            )}
          </div>
          <div>
            <p className="text-white font-medium">{member.user.full_name || 'Unnamed'}</p>
            <p className="text-sm text-gray-500">{member.user.email}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <span className={`text-xs px-2 py-1 rounded-full ${roleColors[member.org_role]}`}>
          {member.org_role}
        </span>
      </td>
      <td className="px-6 py-4">
        {member.is_active && member.user.is_active ? (
          <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400">
            Active
          </span>
        ) : (
          <span className="text-xs px-2 py-1 rounded-full bg-red-500/20 text-red-400">
            Inactive
          </span>
        )}
      </td>
      <td className="px-6 py-4 text-sm text-gray-400">
        {new Date(member.joined_at).toLocaleDateString()}
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
              <div className="absolute right-0 top-8 z-20 bg-cyber-darker border border-cyber-accent/20 rounded-lg py-1 min-w-[140px] shadow-xl">
                <button
                  onClick={() => { setShowMenu(false); onEdit(); }}
                  className="w-full px-3 py-2 text-left text-gray-300 hover:bg-cyber-accent/10 flex items-center gap-2"
                >
                  <Edit className="w-4 h-4" /> Edit Role
                </button>
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

function InviteModal({
  orgId,
  onClose,
  onSuccess,
}: {
  orgId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [emails, setEmails] = useState('');
  const [role, setRole] = useState('member');
  const [error, setError] = useState('');

  const inviteMutation = useMutation({
    mutationFn: (data: { emails: string[]; org_role: string }) =>
      invitationsApi.createBulk(orgId, {
        invitations: data.emails.map(email => ({ email, role: data.org_role }))
      }),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to send invitations');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const emailList = emails
      .split(/[\n,]/)
      .map(e => e.trim())
      .filter(e => e && e.includes('@'));

    if (emailList.length === 0) {
      setError('Please enter at least one valid email address');
      return;
    }

    inviteMutation.mutate({ emails: emailList, org_role: role });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-6 max-w-md w-full mx-4 shadow-xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Invite Members</h2>
          <button onClick={onClose} className="p-1 hover:bg-cyber-darker rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email Addresses *</label>
            <textarea
              value={emails}
              onChange={(e) => setEmails(e.target.value)}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50 resize-none"
              rows={4}
              placeholder="Enter emails (one per line or comma-separated)"
            />
            <p className="text-xs text-gray-500 mt-1">Enter multiple emails separated by commas or new lines</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
            >
              {roleOptions.filter(r => r.value !== 'owner').map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-cyber-accent/30 text-gray-300 rounded-lg hover:bg-cyber-darker transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={inviteMutation.isPending}
              className="flex-1 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
            >
              {inviteMutation.isPending ? 'Sending...' : 'Send Invitations'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditRoleModal({
  member,
  onClose,
  onSave,
  isLoading,
}: {
  member: Member;
  onClose: () => void;
  onSave: (role: string) => void;
  isLoading: boolean;
}) {
  const [role, setRole] = useState(member.org_role);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-6 max-w-sm w-full mx-4 shadow-xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Edit Role</h2>
          <button onClick={onClose} className="p-1 hover:bg-cyber-darker rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <p className="text-gray-400 mb-4">
          Change role for <span className="text-white">{member.user.full_name || member.user.email}</span>
        </p>

        <div className="space-y-2 mb-6">
          {roleOptions.map(opt => (
            <label
              key={opt.value}
              className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                role === opt.value
                  ? 'border-cyber-accent bg-cyber-accent/10'
                  : 'border-cyber-accent/20 hover:border-cyber-accent/40'
              }`}
            >
              <input
                type="radio"
                name="role"
                value={opt.value}
                checked={role === opt.value}
                onChange={(e) => setRole(e.target.value)}
                className="sr-only"
              />
              <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                role === opt.value ? 'border-cyber-accent' : 'border-gray-500'
              }`}>
                {role === opt.value && <div className="w-2 h-2 rounded-full bg-cyber-accent" />}
              </div>
              <div>
                <p className="text-white font-medium">{opt.label}</p>
                <p className="text-xs text-gray-500">{opt.description}</p>
              </div>
            </label>
          ))}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-cyber-accent/30 text-gray-300 rounded-lg hover:bg-cyber-darker transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(role)}
            disabled={isLoading || role === member.org_role}
            className="flex-1 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
          >
            {isLoading ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
