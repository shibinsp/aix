import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  FolderKanban,
  Users,
  BookOpen,
  TrendingUp,
  Calendar,
  Clock,
  ArrowLeft,
  Edit,
  Trash2,
  UserPlus,
  ChevronRight
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { api } from '@/services/api';

interface BatchDetails {
  id: string;
  name: string;
  description: string;
  status: string;
  start_date: string;
  end_date: string;
  member_count: number;
  course_count: number;
  avg_progress: number;
  completions: number;
}

export default function BatchDashboard() {
  const router = useRouter();
  const { orgId, batchId } = router.query;
  const [batch, setBatch] = useState<BatchDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (orgId && batchId) {
      fetchBatchDetails();
    }
  }, [orgId, batchId]);

  const fetchBatchDetails = async () => {
    try {
      const res = await api.get(`/organizations/${orgId}/batches/${batchId}`);
      setBatch(res.data);
    } catch (error) {
      // Fallback data
      setBatch({
        id: batchId as string,
        name: 'Loading...',
        description: '',
        status: 'active',
        start_date: new Date().toISOString(),
        end_date: new Date().toISOString(),
        member_count: 0,
        course_count: 0,
        avg_progress: 0,
        completions: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const quickLinks = [
    { label: 'Members', icon: Users, href: `/portal/${orgId}/batches/${batchId}/members`, count: batch?.member_count },
    { label: 'Curriculum', icon: BookOpen, href: `/portal/${orgId}/batches/${batchId}/curriculum`, count: batch?.course_count },
    { label: 'Progress', icon: TrendingUp, href: `/portal/${orgId}/batches/${batchId}/progress`, count: `${batch?.avg_progress || 0}%` }
  ];

  return (
    <PortalLayout>
      {/* Back Link */}
      <Link
        href={`/portal/${orgId}/batches`}
        className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Batches
      </Link>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Header */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6 mb-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-4 rounded-xl bg-cyber-accent/10">
                  <FolderKanban className="w-8 h-8 text-cyber-accent" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">{batch?.name}</h1>
                  <p className="text-gray-400 mt-1">{batch?.description || 'No description'}</p>
                  <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-4 h-4" />
                      <span>
                        {batch?.start_date && new Date(batch.start_date).toLocaleDateString()} - {batch?.end_date && new Date(batch.end_date).toLocaleDateString()}
                      </span>
                    </div>
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      batch?.status === 'active'
                        ? 'bg-cyber-accent/20 text-cyber-accent border border-cyber-accent/30'
                        : batch?.status === 'completed'
                        ? 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                        : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    }`}>
                      {batch?.status}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors">
                  <Edit className="w-5 h-5" />
                </button>
                <button className="p-2 text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors">
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-cyber-accent/10">
                  <Users className="w-5 h-5 text-cyber-accent" />
                </div>
                <span className="text-gray-400 text-sm">Members</span>
              </div>
              <p className="text-3xl font-bold text-white">{batch?.member_count || 0}</p>
            </div>

            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <BookOpen className="w-5 h-5 text-blue-400" />
                </div>
                <span className="text-gray-400 text-sm">Courses</span>
              </div>
              <p className="text-3xl font-bold text-white">{batch?.course_count || 0}</p>
            </div>

            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                </div>
                <span className="text-gray-400 text-sm">Avg Progress</span>
              </div>
              <p className="text-3xl font-bold text-white">{batch?.avg_progress || 0}%</p>
            </div>

            <div className="p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-yellow-500/10">
                  <Clock className="w-5 h-5 text-yellow-400" />
                </div>
                <span className="text-gray-400 text-sm">Completions</span>
              </div>
              <p className="text-3xl font-bold text-white">{batch?.completions || 0}</p>
            </div>
          </div>

          {/* Quick Links */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {quickLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="flex items-center justify-between p-6 bg-cyber-dark rounded-xl border border-cyber-accent/20 hover:border-cyber-accent/40 transition-all group"
              >
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-cyber-accent/10 group-hover:bg-cyber-accent/20 transition-colors">
                    <link.icon className="w-6 h-6 text-cyber-accent" />
                  </div>
                  <div>
                    <p className="text-white font-medium">{link.label}</p>
                    <p className="text-sm text-gray-500">{link.count} {typeof link.count === 'number' ? 'items' : ''}</p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-cyber-accent transition-colors" />
              </Link>
            ))}
          </div>
        </>
      )}
    </PortalLayout>
  );
}
