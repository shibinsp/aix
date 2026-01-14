import { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  FolderKanban, Search, Plus, Loader2, Users, BookOpen,
  Calendar, MoreVertical, TrendingUp, X
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi, batchesApi } from '@/services/api';
import OrgLayout from '@/components/common/OrgLayout';

interface Batch {
  id: string;
  name: string;
  description?: string;
  status: string;
  start_date?: string;
  end_date?: string;
  max_users: number;
  member_count?: number;
  curriculum_courses?: string[];
  avg_progress?: number;
}

const statusColors: Record<string, string> = {
  active: 'bg-green-500/20 text-green-400 border-green-500/30',
  inactive: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  archived: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
};

export default function OrgBatches() {
  const router = useRouter();
  const { orgId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { data: orgData } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsApi.get(orgId as string),
    enabled: isAuthenticated && !!orgId,
  });

  const { data: batchesData, isLoading } = useQuery({
    queryKey: ['organization-batches', orgId, { search, status: statusFilter }],
    queryFn: () => batchesApi.list(orgId as string, {
      search: search || undefined,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
    enabled: isAuthenticated && !!orgId,
  });

  const org = orgData?.organization || orgData;
  const batches = batchesData?.items || batchesData || [];
  const currentUserRole = user?.org_role?.toLowerCase();
  const canCreateBatch = currentUserRole === 'owner' || currentUserRole === 'admin';

  return (
    <OrgLayout title="Batches" subtitle={org?.name}>
      {/* Header Actions */}
      <div className="flex flex-col md:flex-row justify-between gap-4 mb-8">
        <div className="flex-1 max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search batches..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#0d1520] border border-blue-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>
        <div className="flex gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-[#0d1520] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </select>
          {canCreateBatch && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
            >
              <Plus className="w-5 h-5" />
              Create Batch
            </button>
          )}
        </div>
      </div>

      {/* Batches Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
        </div>
      ) : batches.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {batches.map((batch: Batch) => (
            <BatchCard key={batch.id} batch={batch} orgId={orgId as string} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-[#0d1520] rounded-xl border border-blue-500/20">
          <FolderKanban className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No batches found</h3>
          <p className="text-gray-400 mb-4">
            {search || statusFilter !== 'all'
              ? 'No batches match your search criteria'
              : 'Create your first batch to organize learners into groups'}
          </p>
          {canCreateBatch && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium"
            >
              <Plus className="w-4 h-4" />
              Create Batch
            </button>
          )}
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
    </OrgLayout>
  );
}

function BatchCard({ batch, orgId }: { batch: Batch; orgId: string }) {
  return (
    <Link
      href={`/org/${orgId}/batches/${batch.id}`}
      className="bg-[#0d1520] rounded-xl border border-blue-500/20 p-5 hover:border-blue-500/40 transition-colors group"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center">
          <FolderKanban className="w-6 h-6 text-blue-400" />
        </div>
        <span className={`text-xs px-2 py-1 rounded-full border ${statusColors[batch.status] || statusColors.inactive}`}>
          {batch.status}
        </span>
      </div>

      <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
        {batch.name}
      </h3>
      {batch.description && (
        <p className="text-sm text-gray-500 mb-4 line-clamp-2">{batch.description}</p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center p-2 bg-[#0a0a0f] rounded-lg">
          <div className="flex items-center justify-center gap-1 text-gray-400 mb-1">
            <Users className="w-3 h-3" />
          </div>
          <p className="text-white font-medium text-sm">
            {batch.member_count || 0}/{batch.max_users}
          </p>
          <p className="text-xs text-gray-500">Members</p>
        </div>
        <div className="text-center p-2 bg-[#0a0a0f] rounded-lg">
          <div className="flex items-center justify-center gap-1 text-gray-400 mb-1">
            <BookOpen className="w-3 h-3" />
          </div>
          <p className="text-white font-medium text-sm">
            {batch.curriculum_courses?.length || 0}
          </p>
          <p className="text-xs text-gray-500">Courses</p>
        </div>
        <div className="text-center p-2 bg-[#0a0a0f] rounded-lg">
          <div className="flex items-center justify-center gap-1 text-gray-400 mb-1">
            <TrendingUp className="w-3 h-3" />
          </div>
          <p className="text-white font-medium text-sm">
            {batch.avg_progress || 0}%
          </p>
          <p className="text-xs text-gray-500">Progress</p>
        </div>
      </div>

      {/* Dates */}
      {(batch.start_date || batch.end_date) && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Calendar className="w-3 h-3" />
          {batch.start_date && (
            <span>{new Date(batch.start_date).toLocaleDateString()}</span>
          )}
          {batch.start_date && batch.end_date && <span>-</span>}
          {batch.end_date && (
            <span>{new Date(batch.end_date).toLocaleDateString()}</span>
          )}
        </div>
      )}
    </Link>
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
    mutationFn: (data: typeof formData) => batchesApi.create(orgId, data),
    onSuccess: () => onSuccess(),
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
    createMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#0d1520] rounded-2xl border border-blue-500/30 p-6 max-w-lg w-full mx-4 shadow-xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Create New Batch</h2>
          <button onClick={onClose} className="p-1 hover:bg-blue-500/10 rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Batch Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => { setFormData({ ...formData, name: e.target.value }); setError(''); }}
              className="w-full px-3 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
              placeholder="e.g., Fall 2024 Cohort"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50 resize-none"
              rows={3}
              placeholder="Optional description..."
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Max Members</label>
            <input
              type="number"
              value={formData.max_users}
              onChange={(e) => setFormData({ ...formData, max_users: parseInt(e.target.value) || 1 })}
              min={1}
              max={1000}
              className="w-full px-3 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Start Date</label>
              <input
                type="date"
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                className="w-full px-3 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">End Date</label>
              <input
                type="date"
                value={formData.end_date}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                className="w-full px-3 py-2 bg-[#0a0a0f] border border-blue-500/20 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
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
              className="flex-1 px-4 py-2 border border-blue-500/30 text-gray-300 rounded-lg hover:bg-blue-500/10 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-500/90 transition-colors font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Batch'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
