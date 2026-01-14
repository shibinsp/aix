import { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Send, Loader2, Search, UserPlus, X, Trash2,
  Clock, CheckCircle, XCircle, Mail, RefreshCw, AlertCircle, Copy
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi, invitationsApi } from '@/services/api';
import OrgLayout from '@/components/common/OrgLayout';

interface Invitation {
  id: string;
  email: string;
  org_role: string;
  status: string;
  token: string;
  expires_at: string;
  created_at: string;
  invited_by?: {
    email: string;
    full_name: string;
  };
}

const statusConfig: Record<string, { color: string; icon: any; label: string }> = {
  pending: { color: 'bg-yellow-500/20 text-yellow-400', icon: Clock, label: 'Pending' },
  accepted: { color: 'bg-green-500/20 text-green-400', icon: CheckCircle, label: 'Accepted' },
  declined: { color: 'bg-red-500/20 text-red-400', icon: XCircle, label: 'Declined' },
  expired: { color: 'bg-gray-500/20 text-gray-400', icon: Clock, label: 'Expired' },
};

const roleColors: Record<string, string> = {
  admin: 'bg-blue-500/20 text-blue-400',
  instructor: 'bg-purple-500/20 text-purple-400',
  member: 'bg-gray-500/20 text-gray-400',
};

export default function OrgInvitations() {
  const router = useRouter();
  const { orgId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showInviteModal, setShowInviteModal] = useState(false);

  const { data: orgData } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsApi.get(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  const { data: invitationsData, isLoading } = useQuery({
    queryKey: ['organization-invitations', orgId, { search, status: statusFilter }],
    queryFn: () => invitationsApi.list(orgId as string, {
      search: search || undefined,
      status_filter: statusFilter !== 'all' ? statusFilter : undefined,
    }),
    enabled: isAuthenticated && !!orgId,
  });

  const cancelMutation = useMutation({
    mutationFn: invitationsApi.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-invitations', orgId] });
    },
  });

  const resendMutation = useMutation({
    mutationFn: (inviteId: string) => invitationsApi.resend(inviteId, { send_email: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-invitations', orgId] });
    },
  });

  const org = orgData?.organization || orgData;
  const invitations = invitationsData?.items || invitationsData || [];
  const currentUserRole = user?.org_role?.toLowerCase();
  const canSendInvites = currentUserRole === 'owner' || currentUserRole === 'admin';

  return (
    <OrgLayout title="Invitations" subtitle={org?.name}>
      {/* Header Actions */}
      {canSendInvites && (
        <div className="flex justify-end mb-8">
          <button
            onClick={() => setShowInviteModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
          >
            <UserPlus className="w-5 h-5" />
            Send Invitations
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="accepted">Accepted</option>
            <option value="declined">Declined</option>
            <option value="expired">Expired</option>
          </select>
        </div>
      </div>

      {/* Invitations Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
        </div>
      ) : invitations.length > 0 ? (
        <div className="bg-[#0d1520] rounded-xl border border-blue-500/20 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-blue-500/10">
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Email</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Role</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Status</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Expires</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Sent By</th>
                {canSendInvites && (
                  <th className="text-right px-6 py-4 text-sm font-medium text-gray-400">Actions</th>
                )}
              </tr>
            </thead>
            <tbody>
              {invitations.map((inv: Invitation) => (
                <InvitationRow
                  key={inv.id}
                  invitation={inv}
                  canManage={canSendInvites}
                  onCancel={() => {
                    if (confirm('Cancel this invitation?')) {
                      cancelMutation.mutate(inv.id);
                    }
                  }}
                  onResend={() => resendMutation.mutate(inv.id)}
                  isResending={resendMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 bg-[#0d1520] rounded-xl border border-blue-500/20">
          <Send className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No invitations found</h3>
          <p className="text-gray-400 mb-4">Send invitations to add members to your organization.</p>
          {canSendInvites && (
            <button
              onClick={() => setShowInviteModal(true)}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
            >
              Send Invitations
            </button>
          )}
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <InviteModal
          orgId={orgId as string}
          onClose={() => setShowInviteModal(false)}
          onSuccess={() => {
            setShowInviteModal(false);
            queryClient.invalidateQueries({ queryKey: ['organization-invitations', orgId] });
          }}
        />
      )}
    </OrgLayout>
  );
}

function InvitationRow({
  invitation,
  canManage,
  onCancel,
  onResend,
  isResending,
}: {
  invitation: Invitation;
  canManage: boolean;
  onCancel: () => void;
  onResend: () => void;
  isResending: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const status = statusConfig[invitation.status] || statusConfig.pending;
  const StatusIcon = status.icon;
  const isExpired = new Date(invitation.expires_at) < new Date();
  const isPending = invitation.status === 'pending' && !isExpired;

  const copyInviteLink = () => {
    const link = `${window.location.origin}/invite/${invitation.token}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <tr className="border-b border-blue-500/10 hover:bg-blue-500/5">
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-gray-500" />
          <span className="text-white">{invitation.email}</span>
        </div>
      </td>
      <td className="px-6 py-4">
        <span className={`text-xs px-2 py-1 rounded-full ${roleColors[invitation.org_role]}`}>
          {invitation.org_role}
        </span>
      </td>
      <td className="px-6 py-4">
        <span className={`text-xs px-2 py-1 rounded-full inline-flex items-center gap-1 ${status.color}`}>
          <StatusIcon className="w-3 h-3" />
          {isExpired && invitation.status === 'pending' ? 'Expired' : status.label}
        </span>
      </td>
      <td className="px-6 py-4 text-sm text-gray-400">
        {new Date(invitation.expires_at).toLocaleDateString()}
      </td>
      <td className="px-6 py-4 text-sm text-gray-400">
        {invitation.invited_by?.full_name || invitation.invited_by?.email || 'System'}
      </td>
      {canManage && (
        <td className="px-6 py-4 text-right">
          <div className="flex items-center justify-end gap-2">
            {isPending && (
              <>
                <button
                  onClick={copyInviteLink}
                  className="p-2 hover:bg-blue-500/10 rounded-lg transition-colors text-gray-400 hover:text-blue-400"
                  title="Copy invite link"
                >
                  {copied ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                </button>
                <button
                  onClick={onResend}
                  disabled={isResending}
                  className="p-2 hover:bg-blue-500/10 rounded-lg transition-colors text-gray-400 hover:text-blue-400 disabled:opacity-50"
                  title="Resend invitation"
                >
                  <RefreshCw className={`w-4 h-4 ${isResending ? 'animate-spin' : ''}`} />
                </button>
                <button
                  onClick={onCancel}
                  className="p-2 hover:bg-red-500/10 rounded-lg transition-colors text-gray-400 hover:text-red-400"
                  title="Cancel invitation"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </td>
      )}
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

  const roleOptions = [
    { value: 'admin', label: 'Admin', description: 'Full management access' },
    { value: 'instructor', label: 'Instructor', description: 'Manage courses and students' },
    { value: 'member', label: 'Member', description: 'Access assigned courses' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#0d1520] rounded-2xl border border-blue-500/30 p-6 max-w-lg w-full mx-4 shadow-xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Send Invitations</h2>
          <button onClick={onClose} className="p-1 hover:bg-blue-500/10 rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email Addresses *</label>
            <textarea
              value={emails}
              onChange={(e) => { setEmails(e.target.value); setError(''); }}
              className="w-full px-3 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50 resize-none font-mono text-sm"
              rows={5}
              placeholder="john@example.com&#10;jane@example.com&#10;bob@example.com"
            />
            <p className="text-xs text-gray-500 mt-1">Enter one email per line or separate with commas</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Role</label>
            <div className="space-y-2">
              {roleOptions.map(opt => (
                <label
                  key={opt.value}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    role === opt.value
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-blue-500/20 hover:border-blue-500/40'
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
                    role === opt.value ? 'border-blue-500' : 'border-gray-500'
                  }`}>
                    {role === opt.value && <div className="w-2 h-2 rounded-full bg-blue-500" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-white font-medium">{opt.label}</p>
                    <p className="text-xs text-gray-500">{opt.description}</p>
                  </div>
                </label>
              ))}
            </div>
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
              className="flex-1 px-4 py-2 border border-blue-500/30 text-gray-300 rounded-lg hover:bg-blue-500/10 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={inviteMutation.isPending}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {inviteMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Send Invitations
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
