import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  Users,
  Search,
  Filter,
  UserPlus,
  Mail,
  MoreVertical,
  TrendingUp,
  BookOpen,
  Terminal,
  ChevronDown
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { organizationsApi } from '@/services/api';

interface Member {
  id: string;
  username: string;
  email: string;
  org_role: string;
  skill_level: string;
  joined_at: string;
  courses_completed: number;
  labs_completed: number;
  progress: number;
}

export default function PortalMembers() {
  const router = useRouter();
  const { orgId } = router.query;
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [showInviteModal, setShowInviteModal] = useState(false);

  useEffect(() => {
    if (orgId) {
      fetchMembers();
    }
  }, [orgId]);

  const fetchMembers = async () => {
    if (typeof orgId !== 'string') return;

    try {
      const res = await organizationsApi.getMembers(orgId);
      setMembers(res.members || res || []);
    } catch (error) {
      // Use empty array if API not available
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    if (typeof orgId !== 'string') return;

    try {
      await organizationsApi.updateMember(orgId, memberId, { role: newRole });
      setMembers(members.map(m =>
        m.id === memberId ? { ...m, org_role: newRole } : m
      ));
    } catch (error) {
      console.error('Failed to update role:', error);
    }
  };

  const filteredMembers = members.filter(member => {
    const matchesSearch = member.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      member.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'all' || member.org_role.toLowerCase() === roleFilter;
    return matchesSearch && matchesRole;
  });

  const getRoleBadgeColor = (role: string) => {
    const colors: Record<string, string> = {
      owner: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      admin: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      instructor: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      member: 'bg-cyber-accent/20 text-cyber-accent border-cyber-accent/30'
    };
    return colors[role.toLowerCase()] || colors.member;
  };

  return (
    <PortalLayout title="Members" subtitle="Manage organization members and their roles">
      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent transition-colors"
          />
        </div>

        {/* Role Filter */}
        <div className="relative">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="appearance-none pl-10 pr-10 py-2.5 bg-cyber-dark border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent transition-colors cursor-pointer"
          >
            <option value="all">All Roles</option>
            <option value="owner">Owner</option>
            <option value="admin">Admin</option>
            <option value="instructor">Instructor</option>
            <option value="member">Member</option>
          </select>
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        </div>

        {/* Invite Button */}
        <button
          onClick={() => router.push(`/portal/${orgId}/invitations`)}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors"
        >
          <UserPlus className="w-5 h-5" />
          Invite Member
        </button>
      </div>

      {/* Members Table */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cyber-accent/10">
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Member
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Progress
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Courses
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Labs
                </th>
                <th className="text-right px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-accent/10">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex items-center justify-center gap-3">
                      <div className="w-6 h-6 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
                      <span className="text-gray-400">Loading members...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredMembers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No members found</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {searchQuery || roleFilter !== 'all'
                        ? 'Try adjusting your filters'
                        : 'Invite members to your organization'}
                    </p>
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
                      <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium border ${getRoleBadgeColor(member.org_role)}`}>
                        {member.org_role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-cyber-accent rounded-full"
                            style={{ width: `${member.progress || 0}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-400">{member.progress || 0}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-gray-400">
                        <BookOpen className="w-4 h-4" />
                        <span>{member.courses_completed || 0}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-gray-400">
                        <Terminal className="w-4 h-4" />
                        <span>{member.labs_completed || 0}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="relative inline-block">
                        <select
                          value={member.org_role.toLowerCase()}
                          onChange={(e) => handleRoleChange(member.id, e.target.value)}
                          className="appearance-none px-3 py-1.5 pr-8 bg-transparent border border-cyber-accent/20 rounded text-sm text-gray-400 focus:outline-none focus:border-cyber-accent cursor-pointer"
                        >
                          <option value="member">Member</option>
                          <option value="instructor">Instructor</option>
                          <option value="admin">Admin</option>
                        </select>
                        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary */}
      <div className="mt-6 flex items-center justify-between text-sm text-gray-500">
        <p>
          Showing {filteredMembers.length} of {members.length} members
        </p>
        {selectedMembers.length > 0 && (
          <p className="text-cyber-accent">
            {selectedMembers.length} selected
          </p>
        )}
      </div>
    </PortalLayout>
  );
}
