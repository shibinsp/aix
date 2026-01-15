import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  Mail,
  Send,
  Search,
  Clock,
  CheckCircle,
  XCircle,
  Copy,
  RefreshCw,
  Trash2,
  X,
  Plus
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { invitationsApi } from '@/services/api';

interface Invitation {
  id: string;
  email: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  role: string;
  sent_at: string;
  expires_at: string;
  invite_code: string;
}

export default function PortalInvitations() {
  const router = useRouter();
  const { orgId } = router.query;
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'member', message: '' });
  const [sending, setSending] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (orgId) {
      fetchInvitations();
    }
  }, [orgId]);

  const fetchInvitations = async () => {
    if (typeof orgId !== 'string') return;

    try {
      const res = await invitationsApi.list(orgId);
      setInvitations(res.invitations || res || []);
    } catch (error) {
      setInvitations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSendInvitation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (typeof orgId !== 'string') return;

    setSending(true);
    try {
      await invitationsApi.create(orgId, {
        email: inviteForm.email,
        role: inviteForm.role,
        message: inviteForm.message
      });
      setShowInviteModal(false);
      setInviteForm({ email: '', role: 'member', message: '' });
      fetchInvitations();
    } catch (error) {
      console.error('Failed to send invitation:', error);
    } finally {
      setSending(false);
    }
  };

  const handleResend = async (invitationId: string) => {
    try {
      await invitationsApi.resend(invitationId);
      fetchInvitations();
    } catch (error) {
      console.error('Failed to resend invitation:', error);
    }
  };

  const handleCancel = async (invitationId: string) => {
    try {
      await invitationsApi.cancel(invitationId);
      fetchInvitations();
    } catch (error) {
      console.error('Failed to cancel invitation:', error);
    }
  };

  const copyInviteLink = (code: string, id: string) => {
    const link = `${window.location.origin}/invite/${code}`;
    navigator.clipboard.writeText(link);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredInvitations = invitations.filter(inv => {
    const matchesSearch = inv.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { color: string; icon: any }> = {
      pending: { color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', icon: Clock },
      accepted: { color: 'bg-cyber-accent/20 text-cyber-accent border-cyber-accent/30', icon: CheckCircle },
      expired: { color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: XCircle },
      cancelled: { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle }
    };
    return badges[status] || badges.pending;
  };

  return (
    <PortalLayout title="Invitations" subtitle="Manage organization invitations">
      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent transition-colors"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2.5 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent transition-colors"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="accepted">Accepted</option>
          <option value="expired">Expired</option>
          <option value="cancelled">Cancelled</option>
        </select>

        <button
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors"
        >
          <Send className="w-5 h-5" />
          Send Invitation
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <p className="text-2xl font-bold text-white">
            {invitations.filter(i => i.status === 'pending').length}
          </p>
          <p className="text-sm text-gray-400">Pending</p>
        </div>
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <p className="text-2xl font-bold text-white">
            {invitations.filter(i => i.status === 'accepted').length}
          </p>
          <p className="text-sm text-gray-400">Accepted</p>
        </div>
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <p className="text-2xl font-bold text-white">
            {invitations.filter(i => i.status === 'expired').length}
          </p>
          <p className="text-sm text-gray-400">Expired</p>
        </div>
        <div className="p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <p className="text-2xl font-bold text-white">{invitations.length}</p>
          <p className="text-sm text-gray-400">Total Sent</p>
        </div>
      </div>

      {/* Invitations Table */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cyber-accent/10">
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Email</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Role</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Sent</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Expires</th>
                <th className="text-right px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-accent/10">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex items-center justify-center gap-3">
                      <div className="w-6 h-6 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
                      <span className="text-gray-400">Loading invitations...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredInvitations.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <Mail className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No invitations found</p>
                    <button
                      onClick={() => setShowInviteModal(true)}
                      className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-cyber-accent/10 text-cyber-accent rounded-lg hover:bg-cyber-accent/20 transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                      Send Invitation
                    </button>
                  </td>
                </tr>
              ) : (
                filteredInvitations.map((invitation) => {
                  const statusBadge = getStatusBadge(invitation.status);
                  const StatusIcon = statusBadge.icon;
                  return (
                    <tr key={invitation.id} className="hover:bg-cyber-accent/5 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center">
                            <Mail className="w-5 h-5 text-cyber-accent" />
                          </div>
                          <span className="text-white">{invitation.email}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="capitalize text-gray-400">{invitation.role}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${statusBadge.color}`}>
                          <StatusIcon className="w-3 h-3" />
                          {invitation.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-400 text-sm">
                        {new Date(invitation.sent_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-gray-400 text-sm">
                        {new Date(invitation.expires_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end gap-2">
                          {invitation.status === 'pending' && (
                            <>
                              <button
                                onClick={() => copyInviteLink(invitation.invite_code, invitation.id)}
                                className="p-2 text-gray-400 hover:text-cyber-accent rounded-lg hover:bg-white/5 transition-colors"
                                title="Copy invite link"
                              >
                                {copiedId === invitation.id ? (
                                  <CheckCircle className="w-4 h-4 text-cyber-accent" />
                                ) : (
                                  <Copy className="w-4 h-4" />
                                )}
                              </button>
                              <button
                                onClick={() => handleResend(invitation.id)}
                                className="p-2 text-gray-400 hover:text-blue-400 rounded-lg hover:bg-white/5 transition-colors"
                                title="Resend invitation"
                              >
                                <RefreshCw className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleCancel(invitation.id)}
                                className="p-2 text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
                                title="Cancel invitation"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Send Invitation Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="w-full max-w-md bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Send Invitation</h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSendInvitation} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent"
                  placeholder="user@example.com"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Role
                </label>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent"
                >
                  <option value="member">Member</option>
                  <option value="instructor">Instructor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Personal Message (Optional)
                </label>
                <textarea
                  value={inviteForm.message}
                  onChange={(e) => setInviteForm({ ...inviteForm, message: e.target.value })}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent resize-none"
                  rows={3}
                  placeholder="Add a personal message to the invitation..."
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 px-4 py-2.5 border border-cyber-accent/20 text-gray-400 rounded-lg hover:bg-white/5 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sending}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors disabled:opacity-50"
                >
                  {sending ? (
                    <>
                      <div className="w-4 h-4 border-2 border-[#0a1510]/30 border-t-[#0a1510] rounded-full animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Send Invitation
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PortalLayout>
  );
}
