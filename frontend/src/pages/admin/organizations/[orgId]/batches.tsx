import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderKanban, Search, Plus, ArrowLeft, Loader2, Users,
  Calendar, MoreVertical, Eye, Settings, Trash2, X, BookOpen
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi, batchesApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';
import Link from 'next/link';

interface Batch {
  id: string;
  name: string;
  description?: string;
  status: string;
  start_date?: string;
  end_date?: string;
  max_users: number;
  member_count: number;
  curriculum_courses: string[];
  created_at: string;
}

const statusColors: Record<string, string> = {
  active: 'bg-green-500/20 text-green-400',
  inactive: 'bg-gray-500/20 text-gray-400',
  completed: 'bg-blue-500/20 text-blue-400',
  archived: 'bg-yellow-500/20 text-yellow-400',
};

export default function OrganizationBatches() {
  const router = useRouter();
  const { orgId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

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

  const { data: batchesData, isLoading } = useQuery({
    queryKey: ['organization-batches', orgId, { search }],
    queryFn: () => batchesApi.list(orgId as string, { search: search || undefined }),
    enabled: isAuthenticated && !!orgId,
  });

  const deleteMutation = useMutation({
    mutationFn: batchesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-batches', orgId] });
    },
  });

  if (!isAuthenticated) return null;

  const batches = batchesData?.items || batchesData || [];

  return (
    <AdminLayout title="Batches" subtitle={orgData?.name}>
      {/* Header Actions */}
      <div className="flex justify-end mb-8">
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-500/90 transition-colors font-medium"
        >
          <Plus className="w-5 h-5" />
          Create Batch
        </button>
      </div>

      {/* Search */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search batches..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent/50"
          />
        </div>
      </div>

      {/* Batches Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
        </div>
      ) : batches.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {batches.map((batch: Batch) => (
            <BatchCard
              key={batch.id}
              batch={batch}
              orgId={orgId as string}
              onDelete={() => {
                if (confirm(`Delete batch "${batch.name}"?`)) {
                  deleteMutation.mutate(batch.id);
                }
              }}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <FolderKanban className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No batches found</h3>
          <p className="text-gray-400 mb-4">Create your first batch to organize learners.</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
          >
            Create Batch
          </button>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateBatchModal
          orgId={orgId as string}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            queryClient.invalidateQueries({ queryKey: ['organization-batches', orgId] });
          }}
        />
      )}
    </AdminLayout>
  );
}

function BatchCard({
  batch,
  orgId,
  onDelete,
}: {
  batch: Batch;
  orgId: string;
  onDelete: () => void;
}) {
  const router = useRouter();
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden hover:border-cyber-accent/40 transition-colors group">
      <div className="p-5">
        <div className="flex justify-between items-start mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyber-accent/20 flex items-center justify-center">
              <FolderKanban className="w-5 h-5 text-cyber-accent" />
            </div>
            <div>
              <h3
                className="text-lg font-semibold text-white group-hover:text-cyber-accent transition-colors cursor-pointer"
                onClick={() => router.push(`/admin/batches/${batch.id}`)}
              >
                {batch.name}
              </h3>
              <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[batch.status]}`}>
                {batch.status}
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
                  <button
                    onClick={() => router.push(`/admin/batches/${batch.id}`)}
                    className="w-full px-3 py-2 text-left text-gray-300 hover:bg-cyber-accent/10 flex items-center gap-2"
                  >
                    <Eye className="w-4 h-4" /> View
                  </button>
                  <button
                    onClick={() => router.push(`/admin/batches/${batch.id}/curriculum`)}
                    className="w-full px-3 py-2 text-left text-gray-300 hover:bg-cyber-accent/10 flex items-center gap-2"
                  >
                    <BookOpen className="w-4 h-4" /> Curriculum
                  </button>
                  <button
                    onClick={() => { setShowMenu(false); onDelete(); }}
                    className="w-full px-3 py-2 text-left text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {batch.description && (
          <p className="text-gray-400 text-sm mb-4 line-clamp-2">{batch.description}</p>
        )}

        <div className="flex items-center gap-4 text-sm text-gray-400">
          <div className="flex items-center gap-1">
            <Users className="w-4 h-4" />
            <span>{batch.member_count || 0}/{batch.max_users}</span>
          </div>
          <div className="flex items-center gap-1">
            <BookOpen className="w-4 h-4" />
            <span>{batch.curriculum_courses?.length || 0} courses</span>
          </div>
        </div>

        {(batch.start_date || batch.end_date) && (
          <div className="flex items-center gap-1 mt-3 text-xs text-gray-500">
            <Calendar className="w-3 h-3" />
            <span>
              {batch.start_date ? new Date(batch.start_date).toLocaleDateString() : 'N/A'}
              {' - '}
              {batch.end_date ? new Date(batch.end_date).toLocaleDateString() : 'N/A'}
            </span>
          </div>
        )}
      </div>

      <div className="border-t border-cyber-accent/10 px-5 py-3 bg-cyber-darker/50">
        <button
          onClick={() => router.push(`/admin/batches/${batch.id}/members`)}
          className="w-full text-center text-cyber-accent hover:text-cyber-accent/80 text-sm font-medium"
        >
          View Members
        </button>
      </div>
    </div>
  );
}

function CreateBatchModal({
  orgId,
  onClose,
  onSuccess,
}: {
  orgId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    max_users: 50,
    start_date: '',
    end_date: '',
  });
  const [error, setError] = useState('');

  const createMutation = useMutation({
    mutationFn: (data: any) => batchesApi.create(orgId, data),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to create batch');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Batch name is required');
      return;
    }
    createMutation.mutate({
      ...formData,
      start_date: formData.start_date || null,
      end_date: formData.end_date || null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-6 max-w-md w-full mx-4 shadow-xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Create Batch</h2>
          <button onClick={onClose} className="p-1 hover:bg-cyber-darker rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Batch Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
              placeholder="e.g., Cohort 2024 - Batch A"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50 resize-none"
              rows={3}
              placeholder="Brief description of this batch..."
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Max Users</label>
            <input
              type="number"
              value={formData.max_users}
              onChange={(e) => setFormData({ ...formData, max_users: parseInt(e.target.value) || 50 })}
              className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
              min={1}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Start Date</label>
              <input
                type="date"
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">End Date</label>
              <input
                type="date"
                value={formData.end_date}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                className="w-full px-3 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent/50"
              />
            </div>
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
