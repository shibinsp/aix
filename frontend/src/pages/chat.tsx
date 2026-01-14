import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Send,
  Plus,
  MessageSquare,
  Trash2,
  Book,
  ExternalLink,
  Loader2,
  Edit3,
  Check,
  X,
  MoreVertical,
  Brain
} from 'lucide-react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { useAuthStore } from '@/store/authStore';
import { chatApi } from '@/services/api';

export default function Chat() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Rename state
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  // Context menu state
  const [contextMenuId, setContextMenuId] = useState<string | null>(null);

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['chatSessions'],
    queryFn: chatApi.listSessions,
    enabled: isAuthenticated,
  });

  const { data: currentChat, isLoading: chatLoading } = useQuery({
    queryKey: ['chatSession', selectedSession],
    queryFn: () => chatApi.getSession(selectedSession!),
    enabled: !!selectedSession,
  });

  const createSessionMutation = useMutation({
    mutationFn: chatApi.createSession,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
      setSelectedSession(data.id);
    },
  });

  const deleteSessionMutation = useMutation({
    mutationFn: chatApi.deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
      if (selectedSession === contextMenuId) {
        setSelectedSession(null);
      }
      setContextMenuId(null);
    },
  });

  const renameSessionMutation = useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      chatApi.renameSession(sessionId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
      setEditingSessionId(null);
      setEditingTitle('');
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentChat?.messages, streamingMessage]);

  // Close context menu on click outside
  useEffect(() => {
    const handleClick = () => setContextMenuId(null);
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, []);

  const handleNewChat = () => {
    createSessionMutation.mutate({
      title: 'New Chat',
      teaching_mode: 'lecture',
    });
  };

  const handleDeleteChat = (sessionId: string) => {
    if (confirm('Are you sure you want to delete this chat?')) {
      deleteSessionMutation.mutate(sessionId);
    }
  };

  const handleStartRename = (session: any) => {
    setEditingSessionId(session.id);
    setEditingTitle(session.title || session.topic || 'New Chat');
    setContextMenuId(null);
  };

  const handleSaveRename = () => {
    if (editingSessionId && editingTitle.trim()) {
      renameSessionMutation.mutate({ sessionId: editingSessionId, title: editingTitle.trim() });
    }
  };

  const handleCancelRename = () => {
    setEditingSessionId(null);
    setEditingTitle('');
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedSession || isStreaming) return;

    const message = input;
    setInput('');
    setIsStreaming(true);
    setStreamingMessage('');

    try {
      // Add user message to UI immediately
      queryClient.setQueryData(['chatSession', selectedSession], (old: any) => ({
        ...old,
        messages: [
          ...(old?.messages || []),
          { id: 'temp-user', role: 'user', content: message, created_at: new Date().toISOString() },
        ],
      }));

      // Send message and get response
      const response = await chatApi.sendMessage(selectedSession, message);

      // Update with AI response
      queryClient.setQueryData(['chatSession', selectedSession], (old: any) => ({
        ...old,
        messages: [
          ...(old?.messages || []).filter((m: any) => m.id !== 'temp-user'),
          { id: 'user-' + Date.now(), role: 'user', content: message, created_at: new Date().toISOString() },
          response,
        ],
      }));
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsStreaming(false);
      setStreamingMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-full">
      {/* Sidebar - Chat Sessions */}
      <div className="w-64 bg-cyber-dark border-r border-cyber-accent/20 flex flex-col">
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-cyber-accent text-cyber-dark font-medium rounded-lg hover:bg-cyber-accent/90 transition-colors"
          >
            <Plus className="w-5 h-5" />
            New Chat
          </button>
        </div>

        {/* Chat Sessions List */}
        <div className="flex-1 overflow-y-auto p-2">
          {sessionsLoading ? (
            <div className="flex justify-center py-4">
              <Loader2 className="w-6 h-6 text-cyber-accent animate-spin" />
            </div>
          ) : (
            <div className="space-y-1">
              {sessions?.map((session: any) => (
                <div
                  key={session.id}
                  className={`relative group rounded-lg transition-colors ${
                    selectedSession === session.id
                      ? 'bg-cyber-accent/20'
                      : 'hover:bg-white/5'
                  }`}
                >
                  {editingSessionId === session.id ? (
                    <div className="flex items-center gap-1 px-2 py-2">
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename();
                          if (e.key === 'Escape') handleCancelRename();
                        }}
                        className="flex-1 px-2 py-1 bg-cyber-darker border border-cyber-accent rounded text-white text-sm focus:outline-none"
                        autoFocus
                      />
                      <button
                        onClick={handleSaveRename}
                        className="p-1 text-green-400 hover:bg-green-400/10 rounded"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleCancelRename}
                        className="p-1 text-red-400 hover:bg-red-400/10 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <button
                        onClick={() => setSelectedSession(session.id)}
                        className={`flex-1 flex items-center gap-3 px-3 py-2 text-left ${
                          selectedSession === session.id
                            ? 'text-white'
                            : 'text-gray-400'
                        }`}
                      >
                        <MessageSquare className="w-4 h-4 flex-shrink-0" />
                        <span className="truncate text-sm">
                          {session.title || session.topic || 'New Chat'}
                        </span>
                      </button>

                      {/* Actions Menu Button */}
                      <div className="relative">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setContextMenuId(contextMenuId === session.id ? null : session.id);
                          }}
                          className={`p-2 rounded transition-colors ${
                            contextMenuId === session.id
                              ? 'text-white bg-white/10'
                              : 'text-gray-500 opacity-0 group-hover:opacity-100 hover:text-white hover:bg-white/10'
                          }`}
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>

                        {/* Context Menu */}
                        {contextMenuId === session.id && (
                          <div className="absolute right-0 top-full mt-1 z-50 bg-cyber-darker border border-gray-700 rounded-lg shadow-xl overflow-hidden min-w-[140px]">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleStartRename(session);
                              }}
                              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-300 hover:bg-white/10 hover:text-white transition-colors"
                            >
                              <Edit3 className="w-4 h-4" />
                              Rename
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteChat(session.id);
                              }}
                              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {sessions?.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-4">
                  No chats yet. Start a new one!
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedSession ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-cyber-accent/20 bg-cyber-dark flex items-center justify-between">
              <div>
                <h2 className="font-medium text-white">
                  {currentChat?.session?.title || 'Alphha Tutor Chat'}
                </h2>
                <p className="text-sm text-gray-400">
                  Mode: {currentChat?.session?.teaching_mode || 'lecture'} |
                  Messages: {currentChat?.messages?.length || 0}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const session = sessions?.find((s: any) => s.id === selectedSession);
                    if (session) handleStartRename(session);
                  }}
                  className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                  title="Rename chat"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteChat(selectedSession)}
                  className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                  title="Delete chat"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {chatLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
                </div>
              ) : (
                <>
                  {currentChat?.messages?.map((message: any) => (
                    <Message key={message.id} message={message} />
                  ))}
                  {isStreaming && streamingMessage && (
                    <Message
                      message={{
                        role: 'assistant',
                        content: streamingMessage,
                      }}
                      isStreaming
                    />
                  )}
                </>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-cyber-accent/20 bg-cyber-dark">
              <div className="flex gap-3">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask the AI tutor anything about cybersecurity..."
                  className="flex-1 px-4 py-3 bg-cyber-darker border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent resize-none"
                  rows={2}
                  disabled={isStreaming}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
                  className="px-4 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isStreaming ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <div className="w-20 h-20 bg-cyber-accent/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Brain className="w-10 h-10 text-cyber-accent" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">AI Cybersecurity Tutor</h2>
              <p className="text-gray-400 mb-8">
                Start a new chat to get personalized help with cybersecurity topics,
                from basic concepts to advanced techniques.
              </p>

              <button
                onClick={handleNewChat}
                className="px-8 py-4 bg-cyber-accent text-cyber-dark font-bold rounded-xl hover:bg-cyber-accent/90 transition-colors"
              >
                Start New Chat
              </button>

              <div className="mt-8 text-left">
                <p className="text-gray-500 text-sm mb-3">Suggested topics:</p>
                <div className="flex flex-wrap gap-2">
                  {['SQL Injection', 'XSS Attacks', 'Buffer Overflow', 'Network Security', 'Malware Analysis'].map((topic) => (
                    <button
                      key={topic}
                      onClick={() => {
                        handleNewChat();
                        setTimeout(() => setInput(`Teach me about ${topic}`), 500);
                      }}
                      className="px-3 py-1.5 bg-cyber-darker text-gray-400 rounded-lg text-sm hover:text-white hover:bg-cyber-dark transition-colors"
                    >
                      {topic}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Custom markdown components for ChatGPT-like formatting
const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-2xl font-bold text-cyber-accent mt-6 mb-4 pb-2 border-b border-cyber-accent/30">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-xl font-bold text-white mt-6 mb-3 pb-2 border-b border-gray-700">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-lg font-semibold text-white mt-5 mb-2">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-base font-semibold text-gray-200 mt-4 mb-2">
      {children}
    </h4>
  ),
  p: ({ children }) => (
    <p className="text-gray-200 leading-relaxed mb-4">
      {children}
    </p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-white">
      {children}
    </strong>
  ),
  em: ({ children }) => (
    <em className="italic text-gray-300">
      {children}
    </em>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-6 mb-4 space-y-2 text-gray-200">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-6 mb-4 space-y-2 text-gray-200">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed">
      {children}
    </li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-cyber-accent bg-cyber-accent/10 pl-4 py-3 my-4 rounded-r-lg">
      <div className="text-gray-200 italic">
        {children}
      </div>
    </blockquote>
  ),
  hr: () => (
    <hr className="my-6 border-t border-gray-700" />
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-4 rounded-lg border border-gray-700">
      <table className="min-w-full divide-y divide-gray-700">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-cyber-darker">
      {children}
    </thead>
  ),
  tbody: ({ children }) => (
    <tbody className="divide-y divide-gray-700 bg-cyber-dark">
      {children}
    </tbody>
  ),
  tr: ({ children }) => (
    <tr className="hover:bg-cyber-accent/5 transition-colors">
      {children}
    </tr>
  ),
  th: ({ children }) => (
    <th className="px-4 py-3 text-left text-sm font-semibold text-cyber-accent uppercase tracking-wider">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-3 text-sm text-gray-200">
      {children}
    </td>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-cyber-accent hover:text-cyber-accent/80 underline underline-offset-2"
    >
      {children}
    </a>
  ),
  code: ({ className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    const codeString = String(children).replace(/\n$/, '');
    const isCodeBlock = match || codeString.includes('\n');

    if (isCodeBlock) {
      return (
        <div className="my-4 rounded-lg overflow-hidden border border-gray-700">
          {match && (
            <div className="bg-gray-800 px-4 py-2 text-xs text-gray-400 border-b border-gray-700 flex items-center justify-between">
              <span className="font-mono">{match[1]}</span>
              <button
                onClick={() => navigator.clipboard.writeText(codeString)}
                className="hover:text-cyber-accent transition-colors"
              >
                Copy
              </button>
            </div>
          )}
          <SyntaxHighlighter
            style={vscDarkPlus as any}
            language={match ? match[1] : 'text'}
            PreTag="div"
            customStyle={{
              margin: 0,
              padding: '1rem',
              background: '#1a1a2e',
              fontSize: '0.875rem',
            }}
          >
            {codeString}
          </SyntaxHighlighter>
        </div>
      );
    }

    return (
      <code className="bg-cyber-darker text-cyber-accent px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <div className="my-4">
      {children}
    </div>
  ),
};

function Message({ message, isStreaming = false }: { message: any; isStreaming?: boolean }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-4xl rounded-xl px-5 py-4 ${
          isUser
            ? 'bg-cyber-accent text-cyber-dark'
            : 'bg-cyber-dark border border-cyber-accent/20'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="ai-response-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {message.content}
            </ReactMarkdown>
            {isStreaming && <span className="cursor-blink" />}
          </div>
        )}

        {/* RAG Sources */}
        {message.rag_context?.sources?.length > 0 && (
          <div className="mt-4 pt-4 border-t border-cyber-accent/20">
            <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
              <Book className="w-3 h-3" /> Sources
            </p>
            <div className="space-y-1">
              {message.rag_context.sources.slice(0, 3).map((source: any, i: number) => (
                <div
                  key={i}
                  className="text-xs text-gray-400 flex items-center gap-1 hover:text-cyber-accent cursor-pointer"
                >
                  <ExternalLink className="w-3 h-3" />
                  {source.title}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
