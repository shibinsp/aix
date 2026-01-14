import { useEffect, useRef, useCallback, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { Monitor, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import 'xterm/css/xterm.css';

interface LabTerminalProps {
  sessionId: string;
  containerName?: string;
  token: string;
  onDisconnect?: () => void;
}

export default function LabTerminal({
  sessionId,
  containerName = 'target',
  token,
  onDisconnect,
}: LabTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('connecting');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const connect = useCallback(() => {
    if (!terminalRef.current) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Clean up existing terminal
    if (xtermRef.current) {
      xtermRef.current.dispose();
      xtermRef.current = null;
    }

    setStatus('connecting');
    setErrorMessage('');

    // Create new terminal
    const term = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontSize: 14,
      fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#58a6ff',
        cursorAccent: '#0d1117',
        selectionBackground: '#264f78',
        black: '#0d1117',
        red: '#ff7b72',
        green: '#3fb950',
        yellow: '#d29922',
        blue: '#58a6ff',
        magenta: '#bc8cff',
        cyan: '#39c5cf',
        white: '#b1bac4',
        brightBlack: '#6e7681',
        brightRed: '#ffa198',
        brightGreen: '#56d364',
        brightYellow: '#e3b341',
        brightBlue: '#79c0ff',
        brightMagenta: '#d2a8ff',
        brightCyan: '#56d4dd',
        brightWhite: '#f0f6fc',
      },
      scrollback: 10000,
      convertEol: true,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Display connecting message
    term.writeln('\x1b[1;36m[CyberX Lab Terminal]\x1b[0m');
    term.writeln(`Connecting to container: ${containerName}...`);
    term.writeln('');

    // Build WebSocket URL
    // In production (HTTPS), use the same host without port (goes through reverse proxy)
    // In development (HTTP), use port 8000 directly
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const isProduction = window.location.protocol === 'https:';
    const defaultWsHost = isProduction
      ? `${wsProtocol}//${window.location.host}`  // Uses port 443 through proxy
      : `${wsProtocol}//${window.location.hostname}:8000`;  // Direct to backend in dev
    const wsHost = process.env.NEXT_PUBLIC_WS_URL || defaultWsHost;
    const wsUrl = `${wsHost}/ws/terminal/${sessionId}?token=${encodeURIComponent(token)}&container=${containerName}`;

    // Create WebSocket connection
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      term.clear();
      term.writeln('\x1b[1;32m[Connected to lab environment]\x1b[0m');
      term.writeln('');

      // Send initial size
      const { cols, rows } = term;
      ws.send(JSON.stringify({ type: 'resize', cols, rows }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'connected':
            term.writeln(`\x1b[1;32m${data.message}\x1b[0m`);
            term.writeln('');
            break;

          case 'output':
            term.write(data.data);
            break;

          case 'error':
            term.writeln(`\x1b[1;31mError: ${data.message}\x1b[0m`);
            setErrorMessage(data.message);
            break;

          default:
            // Unknown message type, might be raw output
            if (typeof data === 'string') {
              term.write(data);
            }
        }
      } catch {
        // Not JSON, treat as raw output
        term.write(event.data);
      }
    };

    ws.onclose = (event) => {
      setStatus('disconnected');
      term.writeln('');
      term.writeln('\x1b[1;33m[Connection closed]\x1b[0m');

      if (event.reason) {
        term.writeln(`Reason: ${event.reason}`);
        setErrorMessage(event.reason);
      }

      onDisconnect?.();
    };

    ws.onerror = () => {
      setStatus('error');
      setErrorMessage('Failed to connect to terminal server');
      term.writeln('');
      term.writeln('\x1b[1;31m[Connection error]\x1b[0m');
    };

    // Handle terminal input
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'input', data }));
      }
    });

    // Handle terminal resize
    term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    });
  }, [sessionId, containerName, token, onDisconnect]);

  // Initial connection
  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (xtermRef.current) {
        xtermRef.current.dispose();
      }
    };
  }, [connect]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current && xtermRef.current) {
        fitAddonRef.current.fit();
      }
    };

    window.addEventListener('resize', handleResize);

    // Also fit on initial render with a small delay
    const timeout = setTimeout(handleResize, 100);

    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timeout);
    };
  }, []);

  const handleReconnect = () => {
    connect();
  };

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Monitor className="w-4 h-4 text-cyan-400" />
          <span className="text-sm text-white font-medium">Lab Terminal</span>
          <span className="text-xs text-gray-500">({containerName})</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Status indicator */}
          <div className="flex items-center gap-2">
            {status === 'connecting' && (
              <>
                <Loader2 className="w-3 h-3 text-yellow-400 animate-spin" />
                <span className="text-xs text-yellow-400">Connecting...</span>
              </>
            )}
            {status === 'connected' && (
              <>
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                <span className="text-xs text-green-400">Connected</span>
              </>
            )}
            {status === 'disconnected' && (
              <>
                <div className="w-2 h-2 bg-gray-400 rounded-full" />
                <span className="text-xs text-gray-400">Disconnected</span>
              </>
            )}
            {status === 'error' && (
              <>
                <AlertCircle className="w-3 h-3 text-red-400" />
                <span className="text-xs text-red-400">Error</span>
              </>
            )}
          </div>

          {/* Reconnect button */}
          {(status === 'disconnected' || status === 'error') && (
            <button
              onClick={handleReconnect}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-cyan-500/20 text-cyan-400 rounded hover:bg-cyan-500/30 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {errorMessage && status === 'error' && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-red-400 text-sm">
          {errorMessage}
        </div>
      )}

      {/* Terminal container */}
      <div
        ref={terminalRef}
        className="flex-1 p-1"
        style={{ minHeight: '300px' }}
      />
    </div>
  );
}
