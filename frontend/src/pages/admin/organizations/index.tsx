import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Building2, Search, Plus, Users, Calendar, Loader2, X,
  MoreVertical, Edit, Trash2, Eye, Settings
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';

interface Organization {
  id: string;
  name: string;
  slug: string;
  org_type: string;
  description?: string;
  is_active: boolean;
  member_count: number;
  batch_count: number;
  subscription_tier?: string;
  created_at: string;
}

const orgTypeColors: Record<string, string> = {
  enterprise: 'bg-blue-500/20 text-blue-400',
  educational: 'bg-green-500/20 text-green-400',
  government: 'bg-purple-500/20 text-purple-400',
  non_profit: 'bg-orange-500/20 text-orange-400',
};

export default function OrganizationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['organizations', { search }],
    queryFn: () => organizationsApi.list({ search: search || undefined }),
    enabled: isAuthenticated,
  });

  const deleteMutation = useMutation({
    mutationFn: organizationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
    },
  });

  if (!isAuthenticated) return null;

  const organizations = data?.items || data || [];
  const isSuperAdmin = user?.role?.toLowerCase() === 'super_admin';

  return (
    <AdminLayout title="Organizations" subtitle="Manage organizations and their members">
      {/* Header Actions */}
      {isSuperAdmin && (
        <div className="flex justify-end mb-8">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
          >
            <Plus className="w-5 h-5" />
            Create Organization
          </button>
        </div>
      )}

      {/* Search */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-4 mb-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search organizations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent/50"
          />
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-400">Failed to load organizations</p>
        </div>
      ) : organizations.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {organizations.map((org: Organization) => (
            <OrgCard
              key={org.id}
              org={org}
              onView={() => router.push(`/admin/organizations/${org.id}`)}
              onEdit={() => router.push(`/admin/organizations/${org.id}`)}
              onDelete={() => {
                if (confirm(`Delete organization "${org.name}"?`)) {
                  deleteMutation.mutate(org.id);
                }
              }}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Building2 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No organizations found</h3>
          <p className="text-gray-400 mb-4">
            {isSuperAdmin ? 'Create your first organization to get started.' : 'No organizations have been created yet.'}
          </p>
          {isSuperAdmin && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
            >
              Create Organization
            </button>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateOrgModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            queryClient.invalidateQueries({ queryKey: ['organizations'] });
          }}
        />
      )}
    </AdminLayout>
  );
}

function OrgCard({
  org,
  onView,
  onEdit,
  onDelete,
}: {
  org: Organization;
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden hover:border-cyber-accent/40 transition-colors group">
      <div className="p-5">
        <div className="flex justify-between items-start mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyber-accent/20 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-cyber-accent" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white group-hover:text-cyber-accent transition-colors cursor-pointer" onClick={onView}>
                {org.name}
              </h3>
              <span className={`text-xs px-2 py-0.5 rounded-full ${orgTypeColors[org.org_type] || 'bg-gray-500/20 text-gray-400'}`}>
                {org.org_type.replace('_', ' ')}
              </span>
            </div>
          </div>
          <div className="relative">
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
                  <button onClick={onView} className="w-full px-3 py-2 text-left text-gray-300 hover:bg-cyber-accent/10 flex items-center gap-2">
                    <Eye className="w-4 h-4" /> View
                  </button>
                  <button onClick={onEdit} className="w-full px-3 py-2 text-left text-gray-300 hover:bg-cyber-accent/10 flex items-center gap-2">
                    <Settings className="w-4 h-4" /> Settings
                  </button>
                  <button onClick={onDelete} className="w-full px-3 py-2 text-left text-red-400 hover:bg-red-500/10 flex items-center gap-2">
                    <Trash2 className="w-4 h-4" /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {org.description && (
          <p className="text-gray-400 text-sm mb-4 line-clamp-2">{org.description}</p>
        )}

        <div className="flex items-center gap-4 text-sm text-gray-400">
          <div className="flex items-center gap-1">
            <Users className="w-4 h-4" />
            <span>{org.member_count || 0} members</span>
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            <span>{new Date(org.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {!org.is_active && (
          <div className="mt-3 px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded inline-block">
            Inactive
          </div>
        )}
      </div>

      <div className="border-t border-cyber-accent/10 px-5 py-3 bg-cyber-darker/50">
        <button
          onClick={onView}
          className="w-full text-center text-cyber-accent hover:text-cyber-accent/80 text-sm font-medium"
        >
          View Dashboard
        </button>
      </div>
    </div>
  );
}

function CreateOrgModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    name: '',
    org_type: 'enterprise',
    description: '',
    contact_email: '',
    max_members: 100,
  });
  const [error, setError] = useState('');

  const createMutation = useMutation({
    mutationFn: organizationsApi.create,
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to create organization');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Organization name is required');
      return;
    }
    createMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-6 max-w-md w-full mx-4 shadow-xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Create Organization</h2>
          <button onClick={onClose} className="p-1 hover:bg-cyber-darker rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Organization Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
              placeholder="Acme Corporation"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Type</label>
            <select
              value={formData.org_type}
              onChange={(e) => setFormData({ ...formData, org_type: e.target.value })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
            >
              <option value="enterprise">Enterprise</option>
              <option value="educational">Educational</option>
              <option value="government">Government</option>
              <option value="non_profit">Non-Profit</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50 resize-none"
              rows={3}
              placeholder="Brief description of the organization..."
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Contact Email</label>
            <input
              type="email"
              value={formData.contact_email}
              onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
              placeholder="admin@example.com"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Max Members</label>
            <input
              type="number"
              value={formData.max_members}
              onChange={(e) => setFormData({ ...formData, max_members: parseInt(e.target.value) || 100 })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
              min={1}
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
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
              disabled={createMutation.isPending}
              className="flex-1 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
