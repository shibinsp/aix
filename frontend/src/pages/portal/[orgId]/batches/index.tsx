import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  FolderKanban,
  Plus,
  Search,
  Users,
  Calendar,
  MoreVertical,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  X
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { batchesApi } from '@/services/api';

interface Batch {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'completed' | 'upcoming';
  member_count: number;
  course_count: number;
  start_date: string;
  end_date: string;
  progress: number;
}

export default function PortalBatches() {
  const router = useRouter();
  const { orgId } = router.query;
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newBatch, setNewBatch] = useState({ name: '', description: '', start_date: '', end_date: '' });

  useEffect(() => {
    if (orgId) {
      fetchBatches();
    }
  }, [orgId]);

  const fetchBatches = async () => {
    if (typeof orgId !== 'string') return;

    try {
      const res = await batchesApi.list(orgId);
      setBatches(res.batches || res || []);
    } catch (error) {
      setBatches([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (typeof orgId !== 'string') return;

    try {
      await batchesApi.create(orgId, {
        name: newBatch.name,
        description: newBatch.description,
        start_date: newBatch.start_date,
        end_date: newBatch.end_date
      });
      setShowCreateModal(false);
      setNewBatch({ name: '', description: '', start_date: '', end_date: '' });
      fetchBatches();
    } catch (error) {
      console.error('Failed to create batch:', error);
    }
  };

  const filteredBatches = batches.filter(batch => {
    const matchesSearch = batch.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || batch.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { color: string; icon: any }> = {
      active: { color: 'bg-cyber-accent/20 text-cyber-accent border-cyber-accent/30', icon: CheckCircle },
      completed: { color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: CheckCircle },
      upcoming: { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: Clock }
    };
    return badges[status] || badges.active;
  };

  return (
    <PortalLayout title="Batches" subtitle="Manage training batches and cohorts">
      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search batches..."
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
          <option value="active">Active</option>
          <option value="upcoming">Upcoming</option>
          <option value="completed">Completed</option>
        </select>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Create Batch
        </button>
      </div>

      {/* Batches Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
        </div>
      ) : filteredBatches.length === 0 ? (
        <div className="text-center py-12 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <FolderKanban className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No batches found</p>
          <p className="text-sm text-gray-500 mt-1">Create your first batch to get started</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-cyber-accent/10 text-cyber-accent rounded-lg hover:bg-cyber-accent/20 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Batch
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBatches.map((batch) => {
            const statusBadge = getStatusBadge(batch.status);
            const StatusIcon = statusBadge.icon;
            return (
              <Link
                key={batch.id}
                href={`/portal/${orgId}/batches/${batch.id}`}
                className="block p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20 hover:border-cyber-accent/40 transition-all group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 rounded-lg bg-cyber-accent/10">
                    <FolderKanban className="w-6 h-6 text-cyber-accent" />
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${statusBadge.color}`}>
                    <StatusIcon className="w-3 h-3" />
                    {batch.status}
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-cyber-accent transition-colors">
                  {batch.name}
                </h3>
                <p className="text-sm text-gray-400 mb-4 line-clamp-2">
                  {batch.description || 'No description'}
                </p>

                <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-4 h-4" />
                    <span>{batch.member_count} members</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-4 h-4" />
                    <span>{new Date(batch.start_date).toLocaleDateString()}</span>
                  </div>
                </div>

                {batch.status === 'active' && (
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-gray-500">Progress</span>
                      <span className="text-cyber-accent">{batch.progress}%</span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyber-accent rounded-full transition-all"
                        style={{ width: `${batch.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="mt-4 flex items-center text-cyber-accent text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                  <span>View Details</span>
                  <ChevronRight className="w-4 h-4 ml-1" />
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Create Batch Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="w-full max-w-md bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Create New Batch</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateBatch} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Batch Name
                </label>
                <input
                  type="text"
                  value={newBatch.name}
                  onChange={(e) => setNewBatch({ ...newBatch, name: e.target.value })}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent"
                  placeholder="e.g., Cybersecurity Fundamentals Q1 2024"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={newBatch.description}
                  onChange={(e) => setNewBatch({ ...newBatch, description: e.target.value })}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent resize-none"
                  rows={3}
                  placeholder="Describe this batch..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={newBatch.start_date}
                    onChange={(e) => setNewBatch({ ...newBatch, start_date: e.target.value })}
                    className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={newBatch.end_date}
                    onChange={(e) => setNewBatch({ ...newBatch, end_date: e.target.value })}
                    className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent"
                    required
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2.5 border border-cyber-accent/20 text-gray-400 rounded-lg hover:bg-white/5 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors"
                >
                  Create Batch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </PortalLayout>
  );
}
