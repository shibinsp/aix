import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation } from '@tanstack/react-query';
import dynamic from 'next/dynamic';
import {
  Terminal,
  Play,
  Square,
  Loader2,
  RefreshCw,
  CheckCircle,
  Copy,
  ArrowLeft,
  Clock,
  Cpu,
  HardDrive,
  Shield,
  Monitor,
  ExternalLink
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { vmApi } from '@/services/api';

// Dynamic import for terminal
const LabTerminal = dynamic(() => import('@/components/labs/LabTerminal'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-[#0d1117]">
      <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
    </div>
  ),
});

type VMType = 'terminal' | 'desktop';

export default function VMPage() {
  const router = useRouter();
  const { isAuthenticated, token, hasHydrated } = useAuthStore();
  const [selectedType, setSelectedType] = useState<VMType>('terminal');
  const [activeSession, setActiveSession] = useState<any>(null);
  const [copiedText, setCopiedText] = useState('');

  // Check authentication (only after hydration)
  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Get active sessions
  const { data: sessions, isLoading: sessionsLoading, refetch: refetchSessions } = useQuery({
    queryKey: ['vmSessions'],
    queryFn: vmApi.getActiveSessions,
    enabled: isAuthenticated,
    refetchInterval: 5000,
  });

  // Check for active sessions on load
  useEffect(() => {
    if (sessions?.length > 0) {
      const runningSession = sessions.find((s: any) =>
        s.status?.toLowerCase() === 'running'
      );
      if (runningSession) {
        setActiveSession(runningSession);
        // Set type based on preset
        if (runningSession.preset === 'desktop') {
          setSelectedType('desktop');
        }
      }
    }
  }, [sessions]);

  // Start VM mutation
  const startVMMutation = useMutation({
    mutationFn: (type: VMType) => vmApi.startVM(type === 'desktop' ? 'desktop' : 'minimal'),
    onSuccess: (data) => {
      setActiveSession(data);
      refetchSessions();
    },
  });

  // Stop VM mutation
  const stopVMMutation = useMutation({
    mutationFn: (sessionId: string) => vmApi.stopSession(sessionId),
    onSuccess: () => {
      setActiveSession(null);
      refetchSessions();
    },
  });

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(''), 2000);
  };

  const handleBack = () => {
    const sessionId = activeSession?.session_id || activeSession?.id;
    if (sessionId) {
      stopVMMutation.mutate(sessionId);
    }
  };

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const sessionId = activeSession?.session_id || activeSession?.id;
  const isDesktop = activeSession?.preset === 'desktop';

  // Active VM Session View
  if (activeSession && sessionId) {
    return (
      <div className="flex h-full bg-cyber-darker">
        {/* Left Panel - VM Info */}
        <div className="w-[320px] flex flex-col border-r border-cyber-accent/20 bg-cyber-dark">
          {/* Header with Back Button */}
          <div className="p-4 border-b border-cyber-accent/20">
            <button
              onClick={handleBack}
              disabled={stopVMMutation.isPending}
              className="flex items-center gap-2 text-gray-400 hover:text-white mb-4 transition-colors"
            >
              {stopVMMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowLeft className="w-4 h-4" />
              )}
              <span className="text-sm">Back</span>
            </button>

            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                isDesktop ? 'bg-blue-500/20' : 'bg-green-500/20'
              }`}>
                {isDesktop ? (
                  <Monitor className="w-6 h-6 text-blue-400" />
                ) : (
                  <Terminal className="w-6 h-6 text-green-400" />
                )}
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">
                  Alphha Linux {isDesktop ? 'Desktop' : 'Terminal'}
                </h1>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  <span className="text-green-400">Running</span>
                </div>
              </div>
            </div>
          </div>

          {/* Terminal SSH Access */}
          {!isDesktop && (
            <div className="p-4 border-b border-cyber-accent/10">
              <h3 className="text-sm font-semibold text-cyber-accent mb-3">CONNECTION</h3>
              <div className="bg-cyber-darker rounded-lg p-3 space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400">SSH Access</span>
                    <button
                      onClick={() => copyToClipboard(
                        `ssh alphha@185.182.187.146 -p ${activeSession.ssh_port || 2222}`,
                        'ssh'
                      )}
                      className="text-gray-500 hover:text-white"
                    >
                      {copiedText === 'ssh' ? (
                        <CheckCircle className="w-3 h-3 text-green-400" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                  <code className="text-xs text-white font-mono block bg-black/30 p-2 rounded">
                    ssh alphha@185.182.187.146 -p {activeSession.ssh_port || 2222}
                  </code>
                </div>
                <div>
                  <span className="text-xs text-gray-400">Credentials</span>
                  <div className="flex gap-4 mt-1">
                    <div>
                      <span className="text-xs text-gray-500">User: </span>
                      <code className="text-xs text-white">alphha</code>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">Pass: </span>
                      <code className="text-xs text-white">alphha</code>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Desktop VNC URL */}
          {isDesktop && activeSession.vnc_url && (
            <div className="p-4 border-b border-cyber-accent/10">
              <h3 className="text-sm font-semibold text-cyber-accent mb-3">DESKTOP ACCESS</h3>
              <div className="bg-cyber-darker rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-400">Open in new tab</span>
                  <a
                    href={activeSession.vnc_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyber-accent hover:text-cyber-accent/80"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  Password: <code className="text-white">{activeSession.vnc_password || 'toor'}</code>
                </p>
              </div>
            </div>
          )}

          {/* Session Info */}
          <div className="p-4 border-b border-cyber-accent/10">
            <h3 className="text-sm font-semibold text-cyber-accent mb-3">SESSION</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Type</span>
                <span className="text-white">{isDesktop ? 'Desktop' : 'Terminal'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Session ID</span>
                <span className="text-white font-mono text-xs">
                  {sessionId?.slice(0, 8)}...
                </span>
              </div>
              {activeSession.expires_at && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Expires</span>
                  <span className="text-white text-xs">
                    {new Date(activeSession.expires_at).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Quick Commands (Terminal only) */}
          {!isDesktop && (
            <div className="p-4 flex-1 overflow-y-auto">
              <h3 className="text-sm font-semibold text-cyber-accent mb-3">QUICK COMMANDS</h3>
              <div className="space-y-2">
                {[
                  { cmd: 'whoami', desc: 'Current user' },
                  { cmd: 'uname -a', desc: 'System info' },
                  { cmd: 'cat /etc/os-release', desc: 'OS details' },
                  { cmd: 'free -h', desc: 'Memory usage' },
                  { cmd: 'df -h', desc: 'Disk usage' },
                  { cmd: 'ip addr', desc: 'Network info' },
                ].map((item) => (
                  <button
                    key={item.cmd}
                    onClick={() => copyToClipboard(item.cmd, item.cmd)}
                    className="w-full flex items-center justify-between p-2 bg-cyber-darker rounded hover:bg-gray-800 transition-colors group"
                  >
                    <code className="text-sm text-white font-mono">{item.cmd}</code>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">{item.desc}</span>
                      {copiedText === item.cmd ? (
                        <CheckCircle className="w-3 h-3 text-green-400" />
                      ) : (
                        <Copy className="w-3 h-3 text-gray-500 opacity-0 group-hover:opacity-100" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Desktop Tips */}
          {isDesktop && (
            <div className="p-4 flex-1 overflow-y-auto">
              <h3 className="text-sm font-semibold text-cyber-accent mb-3">DESKTOP TIPS</h3>
              <div className="space-y-2 text-sm text-gray-300">
                <p>• Click inside desktop to focus</p>
                <p>• Ctrl+Alt+Shift for clipboard</p>
                <p>• Right-click for context menu</p>
                <p>• Use Firefox for web browsing</p>
              </div>
            </div>
          )}

          {/* Stop Button */}
          <div className="p-4 border-t border-cyber-accent/20">
            <button
              onClick={() => stopVMMutation.mutate(sessionId)}
              disabled={stopVMMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
            >
              {stopVMMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Square className="w-4 h-4" />
              )}
              Stop VM
            </button>
          </div>
        </div>

        {/* Right Panel - Terminal or Desktop */}
        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-700">
            <div className="flex items-center gap-2">
              {isDesktop ? (
                <Monitor className="w-4 h-4 text-blue-400" />
              ) : (
                <Terminal className="w-4 h-4 text-green-400" />
              )}
              <span className="text-sm text-white">
                Alphha Linux {isDesktop ? 'Desktop' : 'Terminal'}
              </span>
            </div>
            <button
              onClick={() => refetchSessions()}
              className="p-1 text-gray-400 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {isDesktop ? (
            <div className="flex-1 bg-black flex items-center justify-center">
              {activeSession.vnc_url ? (
                <div className="text-center p-8 max-w-md">
                  <Monitor className="w-16 h-16 text-blue-400 mx-auto mb-6" />
                  <h3 className="text-xl font-bold text-white mb-3">Desktop Ready</h3>
                  <p className="text-gray-400 mb-6">
                    Your Alphha Linux Desktop is running. Click below to open the VNC viewer in a new tab.
                  </p>
                  <a
                    href={activeSession.vnc_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
                  >
                    <ExternalLink className="w-5 h-5" />
                    Open Desktop
                  </a>
                  <div className="mt-6 p-4 bg-gray-900 rounded-lg text-left">
                    <p className="text-sm text-gray-400 mb-2">VNC Password:</p>
                    <code className="text-lg text-white font-mono">{activeSession.vnc_password || 'toor'}</code>
                  </div>
                  <p className="text-xs text-gray-500 mt-4">
                    Note: VNC runs on a separate port and opens in a new browser tab.
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-400">
                  <Loader2 className="w-8 h-8 animate-spin mb-4" />
                  <p>Loading desktop...</p>
                </div>
              )}
            </div>
          ) : (
            token && (
              <LabTerminal
                sessionId={sessionId}
                containerName="target"
                token={token}
                onDisconnect={() => {}}
              />
            )
          )}
        </div>
      </div>
    );
  }

  // VM Selection View
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Alphha Linux VM</h1>
          <p className="text-gray-400">
            Choose between Terminal or Desktop environment
          </p>
        </div>

        {/* VM Type Selection */}
        <div className="grid grid-cols-2 gap-6 mb-8">
          {/* Terminal Option */}
          <button
            onClick={() => setSelectedType('terminal')}
            className={`p-6 rounded-xl border-2 text-left transition-all ${
              selectedType === 'terminal'
                ? 'border-green-500 bg-green-500/10'
                : 'border-gray-700 bg-cyber-dark hover:border-gray-600'
            }`}
          >
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center mb-4 ${
              selectedType === 'terminal' ? 'bg-green-500/20' : 'bg-gray-800'
            }`}>
              <Terminal className={`w-7 h-7 ${
                selectedType === 'terminal' ? 'text-green-400' : 'text-gray-400'
              }`} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Terminal</h3>
            <p className="text-sm text-gray-400 mb-4">
              Lightweight CLI environment for command-line tasks
            </p>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Cpu className="w-3 h-3" />
                <span>1 CPU</span>
              </div>
              <div className="flex items-center gap-1">
                <HardDrive className="w-3 h-3" />
                <span>512 MB</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>60 min</span>
              </div>
            </div>
          </button>

          {/* Desktop Option */}
          <button
            onClick={() => setSelectedType('desktop')}
            className={`p-6 rounded-xl border-2 text-left transition-all ${
              selectedType === 'desktop'
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-gray-700 bg-cyber-dark hover:border-gray-600'
            }`}
          >
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center mb-4 ${
              selectedType === 'desktop' ? 'bg-blue-500/20' : 'bg-gray-800'
            }`}>
              <Monitor className={`w-7 h-7 ${
                selectedType === 'desktop' ? 'text-blue-400' : 'text-gray-400'
              }`} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Desktop</h3>
            <p className="text-sm text-gray-400 mb-4">
              Full graphical desktop with browser and GUI tools
            </p>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Cpu className="w-3 h-3" />
                <span>2 CPU</span>
              </div>
              <div className="flex items-center gap-1">
                <HardDrive className="w-3 h-3" />
                <span>2 GB</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>60 min</span>
              </div>
            </div>
          </button>
        </div>

        {/* Selected VM Info */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">
              {selectedType === 'terminal' ? 'Terminal' : 'Desktop'} Environment
            </h3>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              selectedType === 'desktop'
                ? 'bg-blue-500/20 text-blue-400'
                : 'bg-green-500/20 text-green-400'
            }`}>
              {selectedType === 'desktop' ? 'VNC Desktop' : 'Web Terminal'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-cyber-accent mb-2">Features</h4>
              <ul className="text-sm text-gray-300 space-y-1">
                {selectedType === 'terminal' ? (
                  <>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Alpine Linux base
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Web-based terminal
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Isolated network
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Fast startup (~5s)
                    </li>
                  </>
                ) : (
                  <>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Ubuntu XFCE desktop
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      VNC in browser
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Firefox browser
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      GUI applications
                    </li>
                  </>
                )}
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-medium text-cyber-accent mb-2">Included Tools</h4>
              <ul className="text-sm text-gray-300 space-y-1">
                {selectedType === 'terminal' ? (
                  <>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      curl, wget, netcat
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      vim, nano, tmux
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Python, GCC, Git
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      htop, strace
                    </li>
                  </>
                ) : (
                  <>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Firefox, Chromium
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Terminal emulator
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      File manager
                    </li>
                    <li className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-gray-500" />
                      Text editor
                    </li>
                  </>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Launch Button */}
        <div className="text-center">
          <button
            onClick={() => startVMMutation.mutate(selectedType)}
            disabled={startVMMutation.isPending || sessionsLoading}
            className={`inline-flex items-center gap-3 px-10 py-4 rounded-xl transition-all font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed shadow-lg ${
              selectedType === 'desktop'
                ? 'bg-blue-500 hover:bg-blue-600 text-white shadow-blue-500/20'
                : 'bg-green-500 hover:bg-green-600 text-white shadow-green-500/20'
            }`}
          >
            {startVMMutation.isPending ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                Starting {selectedType === 'desktop' ? 'Desktop' : 'Terminal'}...
              </>
            ) : (
              <>
                <Play className="w-6 h-6" />
                Launch {selectedType === 'desktop' ? 'Desktop' : 'Terminal'} VM
              </>
            )}
          </button>

          {startVMMutation.isError && (
            <p className="mt-4 text-red-400 text-sm">
              Failed to start VM. Please try again.
            </p>
          )}

          {sessionsLoading && (
            <p className="mt-4 text-gray-400 text-sm flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Checking for active sessions...
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
