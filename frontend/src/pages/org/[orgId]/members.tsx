import { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, Search, Loader2, UserPlus, Mail, MoreVertical,
  TrendingUp, BookOpen, Award, ChevronDown
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi } from '@/services/api';
import OrgLayout from '@/components/common/OrgLayout';
import Link from 'next/link';

interface Member {
  id: string;
  user_id: string;
  user: {
    id: string;
    email: string;
    full_name?: string;
    username?: string;
  };
  org_role: string;
  is_active: boolean;
  joined_at: string;
  progress_percent?: number;
  courses_completed?: number;
  labs_completed?: number;
}

const roleColors: Record<string, string> = {
  owner: 'bg-yellow-500/20 text-yellow-400',
  admin: 'bg-blue-500/20 text-blue-400',
  instructor: 'bg-purple-500/20 text-purple-400',
  member: 'bg-gray-500/20 text-gray-400',
};

export default function OrgMembers() {
  const router = useRouter();
  const { orgId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');

  const { data: orgData } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsApi.get(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  const { data: membersData, isLoading } = useQuery({
    queryKey: ['organization-members', orgId, { search, role: roleFilter }],
    queryFn: () => organizationsApi.getMembers(orgId as string, {
      search: search || undefined,
      role: roleFilter !== 'all' ? roleFilter : undefined,
    }),
    enabled: isAuthenticated && !!orgId,
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      organizationsApi.updateMember(orgId as string, memberId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-members', orgId] });
    },
  });

  const org = orgData?.organization || orgData;
  const members = membersData?.items || membersData || [];
  const currentUserRole = user?.org_role?.toLowerCase();
  const canManageRoles = currentUserRole === 'owner' || currentUserRole === 'admin';

  return (
    <OrgLayout title="Members" subtitle={org?.name}>
      {/* Header Actions */}
      <div className="flex flex-col md:flex-row justify-between gap-4 mb-8">
        <div className="flex-1 max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search members by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#0d1520] border border-blue-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>
        <div className="flex gap-3">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-4 py-2 bg-[#0d1520] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
          >
            <option value="all">All Roles</option>
            <option value="owner">Owner</option>
            <option value="admin">Admin</option>
            <option value="instructor">Instructor</option>
            <option value="member">Member</option>
          </select>
          <Link
            href={`/org/${orgId}/invitations`}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
          >
            <UserPlus className="w-5 h-5" />
            Invite Members
          </Link>
        </div>
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
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Role</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Progress</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Courses</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Labs</th>
                <th className="text-left px-6 py-4 text-sm font-medium text-gray-400">Joined</th>
                {canManageRoles && (
                  <th className="text-right px-6 py-4 text-sm font-medium text-gray-400">Actions</th>
                )}
              </tr>
            </thead>
            <tbody>
              {members.map((member: Member) => (
                <MemberRow
                  key={member.id}
                  member={member}
                  canManageRoles={canManageRoles}
                  currentUserRole={currentUserRole}
                  onRoleChange={(role) => updateRoleMutation.mutate({ memberId: member.user_id, role })}
                  isUpdating={updateRoleMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 bg-[#0d1520] rounded-xl border border-blue-500/20">
          <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No members found</h3>
          <p className="text-gray-400 mb-4">
            {search || roleFilter !== 'all'
              ? 'No members match your search criteria'
              : 'Start by inviting members to your organization'}
          </p>
          <Link
            href={`/org/${orgId}/invitations`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
          >
            <Mail className="w-4 h-4" />
            Send Invitations
          </Link>
        </div>
      )}
    </OrgLayout>
  );
}

function MemberRow({
  member,
  canManageRoles,
  currentUserRole,
  onRoleChange,
  isUpdating,
}: {
  member: Member;
  canManageRoles: boolean;
  currentUserRole?: string;
  onRoleChange: (role: string) => void;
  isUpdating: boolean;
}) {
  const [showDropdown, setShowDropdown] = useState(false);
  const memberRole = member.org_role?.toLowerCase();

  // Can only change roles of users with lower privilege
  const canChangeThisRole = canManageRoles &&
    memberRole !== 'owner' &&
    (currentUserRole === 'owner' || (currentUserRole === 'admin' && memberRole !== 'admin'));

  const roles = currentUserRole === 'owner'
    ? ['admin', 'instructor', 'member']
    : ['instructor', 'member'];

  return (
    <tr className="border-b border-blue-500/10 hover:bg-blue-500/5">
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
        <span className={`text-xs px-2 py-1 rounded-full capitalize ${roleColors[memberRole] || roleColors.member}`}>
          {memberRole}
        </span>
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
          <span>{member.courses_completed || 0}</span>
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-1 text-gray-400">
          <Award className="w-4 h-4" />
          <span>{member.labs_completed || 0}</span>
        </div>
      </td>
      <td className="px-6 py-4 text-sm text-gray-400">
        {new Date(member.joined_at).toLocaleDateString()}
      </td>
      {canManageRoles && (
        <td className="px-6 py-4 text-right">
          {canChangeThisRole && (
            <div className="relative">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="p-2 hover:bg-blue-500/10 rounded-lg transition-colors text-gray-400 hover:text-white"
              >
                <MoreVertical className="w-5 h-5" />
              </button>
              {showDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowDropdown(false)}
                  />
                  <div className="absolute right-0 mt-2 w-48 bg-[#12121a] rounded-lg shadow-xl border border-blue-500/20 z-20">
                    <p className="px-4 py-2 text-xs text-gray-500 border-b border-blue-500/10">
                      Change Role
                    </p>
                    {roles.map((role) => (
                      <button
                        key={role}
                        onClick={() => {
                          onRoleChange(role);
                          setShowDropdown(false);
                        }}
                        disabled={isUpdating || role === memberRole}
                        className={`w-full text-left px-4 py-2 text-sm hover:bg-blue-500/10 transition-colors capitalize ${
                          role === memberRole ? 'text-blue-400' : 'text-gray-300'
                        }`}
                      >
                        {role}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </td>
      )}
    </tr>
  );
}
