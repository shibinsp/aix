import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity, Cpu, HardDrive, MemoryStick, Server, Box,
  RefreshCw, Loader2, StopCircle, Clock, User, Terminal
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { monitoringApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';

interface SystemResources {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  active_containers: number;
  active_vms: number;
}

interface ActiveLabSession {
  id: string;
  user_id: string;
  user_email: string;
  lab_title: string;
  started_at: string;
  container_ids?: string[];
}

interface LabCounts {
  active: number;
  completed: number;
  failed: number;
  terminated: number;
  total: number;
}

export default function ServerPerformance() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    const userRole = user?.role?.toLowerCase();
    if (userRole !== 'super_admin' && userRole !== 'admin') {
      router.push('/dashboard');
    }
  }, [isAuthenticated, user, router]);

  // Fetch system resources
  const { data: resources, isLoading: resourcesLoading } = useQuery<SystemResources>({
    queryKey: ['admin-monitoring-resources'],
    queryFn: monitoringApi.getResources,
    enabled: isAuthenticated,
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Fetch active lab sessions
  const { data: activeLabs, isLoading: labsLoading } = useQuery<ActiveLabSession[]>({
    queryKey: ['admin-monitoring-active-labs'],
    queryFn: monitoringApi.getActiveLabs,
    enabled: isAuthenticated,
    refetchInterval: autoRefresh ? 10000 : false,
  });

  // Fetch lab counts
  const { data: labCounts } = useQuery<LabCounts>({
    queryKey: ['admin-monitoring-lab-counts'],
    queryFn: monitoringApi.getLabCounts,
    enabled: isAuthenticated,
    refetchInterval: autoRefresh ? 10000 : false,
  });

  // Stop lab mutation
  const stopLabMutation = useMutation({
    mutationFn: (sessionId: string) => monitoringApi.stopLab(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-monitoring-active-labs'] });
      queryClient.invalidateQueries({ queryKey: ['admin-monitoring-lab-counts'] });
    },
  });

  const getUsageColor = (percent: number) => {
    if (percent < 50) return 'text-green-400';
    if (percent < 75) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getUsageBgColor = (percent: number) => {
    if (percent < 50) return 'bg-green-500';
    if (percent < 75) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const formatDuration = (startedAt: string) => {
    const start = new Date(startedAt);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins} min`;
    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return `${hours}h ${mins}m`;
  };

  if (!isAuthenticated) return null;

  return (
    <AdminLayout title="Server Performance" subtitle="Real-time system monitoring">
      {/* Auto-refresh toggle */}
      <div className="flex items-center justify-end mb-6">
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
            autoRefresh
              ? 'border-green-500/30 bg-green-500/10 text-green-400'
              : 'border-gray-500/30 bg-gray-500/10 text-gray-400'
          }`}
        >
          <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} style={{ animationDuration: '3s' }} />
          Auto-refresh {autoRefresh ? 'ON' : 'OFF'}
        </button>
      </div>

      {/* System Resources */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {/* CPU */}
        <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-purple-400" />
              </div>
              <span className="text-gray-400 font-medium">CPU Usage</span>
            </div>
            {resourcesLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-500" />}
          </div>
          <div className="mb-3">
            <span className={`text-4xl font-bold ${getUsageColor(resources?.cpu_percent || 0)}`}>
              {resources?.cpu_percent?.toFixed(1) || '0'}%
            </span>
          </div>
          <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getUsageBgColor(resources?.cpu_percent || 0)}`}
              style={{ width: `${resources?.cpu_percent || 0}%` }}
            />
          </div>
        </div>

        {/* Memory */}
        <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <MemoryStick className="w-5 h-5 text-blue-400" />
              </div>
              <span className="text-gray-400 font-medium">Memory Usage</span>
            </div>
            {resourcesLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-500" />}
          </div>
          <div className="mb-3">
            <span className={`text-4xl font-bold ${getUsageColor(resources?.memory_percent || 0)}`}>
              {resources?.memory_percent?.toFixed(1) || '0'}%
            </span>
            <span className="text-sm text-gray-500 ml-2">
              {resources?.memory_used_gb?.toFixed(1) || '0'} / {resources?.memory_total_gb?.toFixed(1) || '0'} GB
            </span>
          </div>
          <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getUsageBgColor(resources?.memory_percent || 0)}`}
              style={{ width: `${resources?.memory_percent || 0}%` }}
            />
          </div>
        </div>

        {/* Disk */}
        <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <HardDrive className="w-5 h-5 text-orange-400" />
              </div>
              <span className="text-gray-400 font-medium">Disk Usage</span>
            </div>
            {resourcesLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-500" />}
          </div>
          <div className="mb-3">
            <span className={`text-4xl font-bold ${getUsageColor(resources?.disk_percent || 0)}`}>
              {resources?.disk_percent?.toFixed(1) || '0'}%
            </span>
            <span className="text-sm text-gray-500 ml-2">
              {resources?.disk_used_gb?.toFixed(0) || '0'} / {resources?.disk_total_gb?.toFixed(0) || '0'} GB
            </span>
          </div>
          <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getUsageBgColor(resources?.disk_percent || 0)}`}
              style={{ width: `${resources?.disk_percent || 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Active Resources */}
      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-5">
          <div className="flex items-center gap-3 mb-2">
            <Box className="w-5 h-5 text-cyan-400" />
            <span className="text-gray-400">Containers</span>
          </div>
          <p className="text-3xl font-bold text-white">{resources?.active_containers || 0}</p>
        </div>
        <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-5">
          <div className="flex items-center gap-3 mb-2">
            <Server className="w-5 h-5 text-green-400" />
            <span className="text-gray-400">VMs</span>
          </div>
          <p className="text-3xl font-bold text-white">{resources?.active_vms || 0}</p>
        </div>
        <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-5">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="w-5 h-5 text-purple-400" />
            <span className="text-gray-400">Active Labs</span>
          </div>
          <p className="text-3xl font-bold text-white">{labCounts?.active || 0}</p>
        </div>
        <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-5">
          <div className="flex items-center gap-3 mb-2">
            <Terminal className="w-5 h-5 text-yellow-400" />
            <span className="text-gray-400">Total Sessions</span>
          </div>
          <p className="text-3xl font-bold text-white">{labCounts?.total || 0}</p>
        </div>
      </div>

      {/* Active Lab Sessions */}
      <div className="bg-cyber-dark rounded-xl border border-purple-500/20 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">Active Lab Sessions</h2>
          {labsLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-500" />}
        </div>

        {activeLabs && activeLabs.length > 0 ? (
          <div className="space-y-3">
            {activeLabs.map((session) => (
              <div
                key={session.id}
                className="flex items-center justify-between p-4 bg-cyber-darker rounded-lg border border-purple-500/10"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <User className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-white font-medium">{session.user_email}</p>
                    <p className="text-sm text-gray-500">{session.lab_title || 'Unknown Lab'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 text-gray-400">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm">{formatDuration(session.started_at)}</span>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm('Force stop this lab session?')) {
                        stopLabMutation.mutate(session.id);
                      }
                    }}
                    disabled={stopLabMutation.isPending}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors"
                  >
                    <StopCircle className="w-4 h-4" />
                    Stop
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Activity className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">No active lab sessions</p>
          </div>
        )}
      </div>

      {/* Lab Statistics */}
      {labCounts && (
        <div className="mt-6 grid grid-cols-4 gap-4">
          <div className="text-center p-4 bg-cyber-dark rounded-lg border border-green-500/20">
            <p className="text-2xl font-bold text-green-400">{labCounts.completed}</p>
            <p className="text-sm text-gray-500">Completed</p>
          </div>
          <div className="text-center p-4 bg-cyber-dark rounded-lg border border-yellow-500/20">
            <p className="text-2xl font-bold text-yellow-400">{labCounts.active}</p>
            <p className="text-sm text-gray-500">Active</p>
          </div>
          <div className="text-center p-4 bg-cyber-dark rounded-lg border border-red-500/20">
            <p className="text-2xl font-bold text-red-400">{labCounts.failed}</p>
            <p className="text-sm text-gray-500">Failed</p>
          </div>
          <div className="text-center p-4 bg-cyber-dark rounded-lg border border-gray-500/20">
            <p className="text-2xl font-bold text-gray-400">{labCounts.terminated}</p>
            <p className="text-sm text-gray-500">Terminated</p>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}
