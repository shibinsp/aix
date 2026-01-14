import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Users,
  Search,
  UserPlus,
  ArrowLeft,
  TrendingUp,
  BookOpen,
  Terminal,
  X,
  Check
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { api } from '@/services/api';

interface BatchMember {
  id: string;
  username: string;
  email: string;
  progress: number;
  courses_completed: number;
  labs_completed: number;
  joined_at: string;
}

interface OrgMember {
  id: string;
  username: string;
  email: string;
}

export default function BatchMembers() {
  const router = useRouter();
  const { orgId, batchId } = router.query;
  const [members, setMembers] = useState<BatchMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [availableMembers, setAvailableMembers] = useState<OrgMember[]>([]);
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);

  useEffect(() => {
    if (orgId && batchId) {
      fetchMembers();
    }
  }, [orgId, batchId]);

  const fetchMembers = async () => {
    try {
      const res = await api.get(`/organizations/${orgId}/batches/${batchId}/members`);
      setMembers(res.data);
    } catch (error) {
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableMembers = async () => {
    try {
      const res = await api.get(`/organizations/${orgId}/members`);
      const batchMemberIds = members.map(m => m.id);
      setAvailableMembers(res.data.filter((m: OrgMember) => !batchMemberIds.includes(m.id)));
    } catch (error) {
      setAvailableMembers([]);
    }
  };

  const handleAddMembers = async () => {
    try {
      await api.post(`/organizations/${orgId}/batches/${batchId}/members`, {
        member_ids: selectedMembers
      });
      setShowAddModal(false);
      setSelectedMembers([]);
      fetchMembers();
    } catch (error) {
      console.error('Failed to add members:', error);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    try {
      await api.delete(`/organizations/${orgId}/batches/${batchId}/members/${memberId}`);
      fetchMembers();
    } catch (error) {
      console.error('Failed to remove member:', error);
    }
  };

  const filteredMembers = members.filter(member =>
    member.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    member.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
          <h1 className="text-2xl font-bold text-white">Batch Members</h1>
          <p className="text-gray-400 mt-1">Manage members in this batch</p>
        </div>
        <button
          onClick={() => {
            fetchAvailableMembers();
            setShowAddModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors"
        >
          <UserPlus className="w-5 h-5" />
          Add Members
        </button>
      </div>

      {/* Search */}
      <div className="mb-6 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search members..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md pl-10 pr-4 py-2.5 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent transition-colors"
        />
      </div>

      {/* Members Table */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-cyber-accent/10">
              <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Member</th>
              <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Progress</th>
              <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Courses</th>
              <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Labs</th>
              <th className="text-right px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-cyber-accent/10">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center">
                  <div className="flex items-center justify-center gap-3">
                    <div className="w-6 h-6 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
                    <span className="text-gray-400">Loading members...</span>
                  </div>
                </td>
              </tr>
            ) : filteredMembers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center">
                  <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">No members in this batch</p>
                  <button
                    onClick={() => {
                      fetchAvailableMembers();
                      setShowAddModal(true);
                    }}
                    className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-cyber-accent/10 text-cyber-accent rounded-lg hover:bg-cyber-accent/20 transition-colors"
                  >
                    <UserPlus className="w-4 h-4" />
                    Add Members
                  </button>
                </td>
              </tr>
            ) : (
              filteredMembers.map((member) => (
                <tr key={member.id} className="hover:bg-cyber-accent/5 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center">
                        <span className="text-cyber-accent font-medium">
                          {member.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-white font-medium">{member.username}</p>
                        <p className="text-sm text-gray-500">{member.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div className="h-full bg-cyber-accent rounded-full" style={{ width: `${member.progress}%` }} />
                      </div>
                      <span className="text-sm text-gray-400">{member.progress}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-gray-400">
                      <BookOpen className="w-4 h-4" />
                      <span>{member.courses_completed}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-gray-400">
                      <Terminal className="w-4 h-4" />
                      <span>{member.labs_completed}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRemoveMember(member.id)}
                      className="px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded transition-colors"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add Members Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="w-full max-w-md bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Add Members to Batch</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="max-h-64 overflow-y-auto space-y-2">
              {availableMembers.length === 0 ? (
                <p className="text-center text-gray-400 py-4">No available members to add</p>
              ) : (
                availableMembers.map((member) => (
                  <button
                    key={member.id}
                    onClick={() => {
                      setSelectedMembers(prev =>
                        prev.includes(member.id)
                          ? prev.filter(id => id !== member.id)
                          : [...prev, member.id]
                      );
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors ${
                      selectedMembers.includes(member.id)
                        ? 'border-[#00ff9d] bg-cyber-accent/10'
                        : 'border-cyber-accent/20 hover:border-cyber-accent/40'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-cyber-accent/20 flex items-center justify-center">
                        <span className="text-cyber-accent text-sm font-medium">
                          {member.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="text-left">
                        <p className="text-white text-sm">{member.username}</p>
                        <p className="text-xs text-gray-500">{member.email}</p>
                      </div>
                    </div>
                    {selectedMembers.includes(member.id) && (
                      <Check className="w-5 h-5 text-cyber-accent" />
                    )}
                  </button>
                ))
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2.5 border border-cyber-accent/20 text-gray-400 rounded-lg hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddMembers}
                disabled={selectedMembers.length === 0}
                className="flex-1 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors disabled:opacity-50"
              >
                Add {selectedMembers.length > 0 && `(${selectedMembers.length})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </PortalLayout>
  );
}
