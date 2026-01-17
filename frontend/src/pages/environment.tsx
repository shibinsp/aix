import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Terminal, Monitor, Play, Square, RotateCcw, Loader2,
  Clock, AlertCircle, ExternalLink, Wifi, WifiOff
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { environmentsApi, limitsApi } from '@/services/api';

interface Environment {
  id: string;
  user_id: string;
  env_type: 'terminal' | 'desktop';
  container_id?: string;
  volume_name: string;
  status: 'stopped' | 'starting' | 'running' | 'error';
  access_url?: string;
  ssh_port?: number;
  vnc_port?: number;
  total_usage_minutes: number;
  monthly_usage_minutes: number;
  created_at: string;
  last_started_at?: string;
  error_message?: string;
}

interface EnvironmentLimits {
  max_terminal_hours_monthly: number;
  max_desktop_hours_monthly: number;
  max_storage_gb: number;
  enable_persistent_vm: boolean;
}

export default function EnvironmentPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  const { data: environmentsData, isLoading } = useQuery({
    queryKey: ['my-environments'],
    queryFn: () => environmentsApi.getMy(),
    enabled: isAuthenticated,
    refetchInterval: 5000, // Poll every 5 seconds for status updates
  });

  const { data: limitsData } = useQuery({
    queryKey: ['my-limits'],
    queryFn: () => limitsApi.getMyLimits(),
    enabled: isAuthenticated,
  });

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  const environments = environmentsData || {};
  const limits: EnvironmentLimits = limitsData?.limits || {
    max_terminal_hours_monthly: 30,
    max_desktop_hours_monthly: 10,
    max_storage_gb: 2,
    enable_persistent_vm: true,
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">My Environment</h1>
        <p className="text-gray-400">
          Access your persistent terminal and desktop environments
        </p>
      </div>

      {/* Environment Cards */}
      <div className="grid md:grid-cols-2 gap-6">
        <EnvironmentCard
          envType="terminal"
          environment={environments.terminal}
          maxHours={limits.max_terminal_hours_monthly}
          enabled={limits.enable_persistent_vm}
        />
        <EnvironmentCard
          envType="desktop"
          environment={environments.desktop}
          maxHours={limits.max_desktop_hours_monthly}
          enabled={limits.enable_persistent_vm}
        />
      </div>

      {/* Usage Stats */}
      <div className="mt-8 bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Resource Usage</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <UsageStat
            label="Terminal Hours"
            used={Math.round((environments.terminal?.monthly_usage_minutes || 0) / 60 * 10) / 10}
            max={limits.max_terminal_hours_monthly}
            unit="hrs"
          />
          <UsageStat
            label="VM Hours"
            used={Math.round((environments.desktop?.monthly_usage_minutes || 0) / 60 * 10) / 10}
            max={limits.max_desktop_hours_monthly}
            unit="hrs"
          />
          <UsageStat
            label="Storage"
            used={0}
            max={limits.max_storage_gb}
            unit="GB"
          />
        </div>
      </div>
    </div>
  );
}

function EnvironmentCard({
  envType,
  environment,
  maxHours,
  enabled,
}: {
  envType: 'terminal' | 'desktop';
  environment?: Environment;
  maxHours: number;
  enabled: boolean;
}) {
  const queryClient = useQueryClient();
  const isTerminal = envType === 'terminal';
  const Icon = isTerminal ? Terminal : Monitor;

  const startMutation = useMutation({
    mutationFn: () => environmentsApi.start(envType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-environments'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => environmentsApi.stop(envType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-environments'] });
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => environmentsApi.reset(envType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-environments'] });
    },
  });

  const status = environment?.status || 'stopped';
  const isRunning = status === 'running';
  const isStarting = status === 'starting';
  const isError = status === 'error';
  const usedHours = Math.round((environment?.monthly_usage_minutes || 0) / 60 * 10) / 10;
  const usagePercent = Math.min(100, (usedHours / maxHours) * 100);

  const handleStart = () => {
    if (!enabled) return;
    startMutation.mutate();
  };

  const handleStop = () => {
    stopMutation.mutate();
  };

  const handleReset = () => {
    if (confirm(`Reset your ${envType}? This will delete all your data and start fresh.`)) {
      resetMutation.mutate();
    }
  };

  const handleConnect = () => {
    if (environment?.access_url) {
      window.open(environment.access_url, '_blank');
    }
  };

  return (
    <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden">
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              isTerminal ? 'bg-green-500/20' : 'bg-purple-500/20'
            }`}>
              <Icon className={`w-6 h-6 ${isTerminal ? 'text-green-400' : 'text-purple-400'}`} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">
                {isTerminal ? 'Terminal' : 'Desktop'}
              </h3>
              <p className="text-sm text-gray-500">
                {isTerminal ? 'SSH access to Linux environment' : 'VNC desktop environment'}
              </p>
            </div>
          </div>
          <StatusBadge status={status} />
        </div>

        {/* Usage Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Monthly Usage</span>
            <span className="text-white">{usedHours} / {maxHours} hrs</span>
          </div>
          <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                usagePercent >= 90 ? 'bg-red-500' :
                usagePercent >= 70 ? 'bg-yellow-500' :
                'bg-cyber-accent'
              }`}
              style={{ width: `${usagePercent}%` }}
            />
          </div>
        </div>

        {/* Connection Info */}
        {isRunning && environment?.access_url && (
          <div className="mb-4 p-3 bg-cyber-darker rounded-lg">
            <div className="flex items-center gap-2 text-sm">
              <Wifi className="w-4 h-4 text-green-400" />
              <span className="text-green-400 font-medium">Connected</span>
            </div>
            {isTerminal && environment.ssh_port && (
              <p className="text-xs text-gray-500 mt-1 font-mono">
                ssh root@localhost -p {environment.ssh_port}
              </p>
            )}
          </div>
        )}

        {isError && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <span className="text-sm text-red-400">Environment error. Click Start to retry or Reset to clear data.</span>
            </div>
            {environment?.error_message && (
              <p className="text-xs text-gray-500 mt-1">{environment.error_message}</p>
            )}
          </div>
        )}

        {!enabled && (
          <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-yellow-400">Persistent environments are disabled for your account.</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="border-t border-cyber-accent/10 px-6 py-4 bg-cyber-darker/50">
        <div className="flex gap-3">
          {isRunning ? (
            <>
              <button
                onClick={handleConnect}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
              >
                <ExternalLink className="w-4 h-4" />
                Connect
              </button>
              <button
                onClick={handleStop}
                disabled={stopMutation.isPending}
                className="flex items-center justify-center gap-2 px-4 py-2 border border-red-500/30 text-red-400 rounded-lg hover:bg-red-500/10 transition-colors disabled:opacity-50"
              >
                {stopMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Square className="w-4 h-4" />
                )}
                Stop
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleStart}
                disabled={!enabled || isStarting || startMutation.isPending || usedHours >= maxHours}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
              >
                {isStarting || startMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Starting...
                  </>
                ) : isError ? (
                  <>
                    <Play className="w-4 h-4" />
                    Retry
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Start
                  </>
                )}
              </button>
              <button
                onClick={handleReset}
                disabled={resetMutation.isPending || isStarting}
                className="flex items-center justify-center gap-2 px-4 py-2 border border-cyber-accent/30 text-gray-300 rounded-lg hover:bg-cyber-dark transition-colors disabled:opacity-50"
                title="Reset environment (delete all data)"
              >
                {resetMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RotateCcw className="w-4 h-4" />
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; icon: any; label: string }> = {
    stopped: { color: 'bg-gray-500/20 text-gray-400', icon: WifiOff, label: 'Stopped' },
    starting: { color: 'bg-yellow-500/20 text-yellow-400', icon: Loader2, label: 'Starting' },
    running: { color: 'bg-green-500/20 text-green-400', icon: Wifi, label: 'Running' },
    error: { color: 'bg-red-500/20 text-red-400', icon: AlertCircle, label: 'Error' },
  };

  const { color, icon: Icon, label } = config[status] || config.stopped;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
      <Icon className={`w-3 h-3 ${status === 'starting' ? 'animate-spin' : ''}`} />
      {label}
    </span>
  );
}

function UsageStat({
  label,
  used,
  max,
  unit,
}: {
  label: string;
  used: number;
  max: number;
  unit: string;
}) {
  const percent = Math.min(100, (used / max) * 100);

  return (
    <div>
      <div className="flex justify-between text-sm mb-2">
        <span className="text-gray-400">{label}</span>
        <span className="text-white">
          {used} / {max} {unit}
        </span>
      </div>
      <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            percent >= 90 ? 'bg-red-500' :
            percent >= 70 ? 'bg-yellow-500' :
            'bg-cyber-accent'
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
