import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import {
  Copy,
  Check,
  ExternalLink,
  Lightbulb,
  AlertTriangle,
  Info,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Play,
  Image as ImageIcon,
  Maximize2,
  Minimize2,
  X,
} from 'lucide-react';

interface ContentBlock {
  id: string;
  block_type: string;
  order: number;
  content: string;
  block_metadata: Record<string, any>;
}

interface Props {
  block: ContentBlock;
  onCopyCode?: (code: string, blockId: string) => void;
  copiedCode?: string | null;
}

export default function ContentBlockRenderer({ block, onCopyCode, copiedCode }: Props) {
  const { block_type, content, block_metadata, id } = block;

  switch (block_type) {
    case 'text':
      return <TextBlock content={content} />;

    case 'code':
      return (
        <CodeBlock
          content={content}
          metadata={block_metadata}
          onCopy={onCopyCode}
          copied={copiedCode === id}
          blockId={id}
        />
      );

    case 'image':
      return <ImageBlock content={content} metadata={block_metadata} />;

    case 'video':
      return <VideoBlock metadata={block_metadata} />;

    case 'diagram':
      return <DiagramBlock content={content} metadata={block_metadata} />;

    case 'wikipedia':
      return <WikipediaBlock content={content} metadata={block_metadata} />;

    case 'callout':
      return <CalloutBlock content={content} metadata={block_metadata} />;

    case 'collapsible':
      return <CollapsibleBlock content={content} metadata={block_metadata} />;

    case 'quiz_inline':
      return <InlineQuizBlock metadata={block_metadata} />;

    default:
      return <TextBlock content={content} />;
  }
}

// Text Block - Renders markdown content
function TextBlock({ content }: { content: string }) {
  if (!content) return null;

  return (
    <div className="prose prose-invert prose-lg max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className="bg-gray-800 px-1.5 py-0.5 rounded text-cyber-accent" {...props}>
                {children}
              </code>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-cyber-accent pl-4 italic text-gray-300">
                {children}
              </blockquote>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyber-accent hover:underline"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// Code Block - Syntax highlighted code with copy button
function CodeBlock({
  content,
  metadata,
  onCopy,
  copied,
  blockId,
}: {
  content: string;
  metadata: Record<string, any>;
  onCopy?: (code: string, blockId: string) => void;
  copied?: boolean;
  blockId: string;
}) {
  const language = metadata?.language || 'text';
  const filename = metadata?.filename;
  const description = metadata?.description;

  return (
    <div className="bg-cyber-darker rounded-xl border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <span className="text-xs text-cyber-accent uppercase font-mono">{language}</span>
          {filename && <span className="text-xs text-gray-400">{filename}</span>}
        </div>
        <button
          onClick={() => onCopy?.(content, blockId)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-4 h-4 text-green-400" />
              <span className="text-green-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Description */}
      {description && (
        <div className="px-4 py-2 bg-gray-800/30 text-sm text-gray-400 border-b border-gray-700">
          {description}
        </div>
      )}

      {/* Code */}
      <div className="overflow-x-auto">
        <SyntaxHighlighter
          style={oneDark}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            background: 'transparent',
            padding: '1rem',
          }}
        >
          {content || ''}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

// Image Block - Displays images with attribution
function ImageBlock({
  content,
  metadata,
}: {
  content: string;
  metadata: Record<string, any>;
}) {
  const url = metadata?.url;
  const alt = content || metadata?.alt || 'Course image';
  const attribution = metadata?.attribution;
  const sourceUrl = metadata?.source_url;

  if (!url) {
    return (
      <div className="bg-cyber-dark rounded-xl border border-gray-800 p-8 flex items-center justify-center">
        <ImageIcon className="w-12 h-12 text-gray-600" />
      </div>
    );
  }

  return (
    <figure className="rounded-xl overflow-hidden border border-gray-800">
      <img
        src={url}
        alt={alt}
        className="w-full h-auto"
        loading="lazy"
      />
      {(attribution || alt) && (
        <figcaption className="bg-cyber-darker px-4 py-2 text-sm text-gray-400">
          {alt}
          {attribution && (
            <span className="block text-xs text-gray-500 mt-1">
              {sourceUrl ? (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyber-accent"
                >
                  {attribution}
                </a>
              ) : (
                attribution
              )}
            </span>
          )}
        </figcaption>
      )}
    </figure>
  );
}

// Video Block - YouTube embed
function VideoBlock({ metadata }: { metadata: Record<string, any> }) {
  const youtubeId = metadata?.youtube_id;
  const title = metadata?.title;

  if (!youtubeId) {
    return (
      <div className="bg-cyber-dark rounded-xl border border-gray-800 p-8 flex items-center justify-center">
        <Play className="w-12 h-12 text-gray-600" />
      </div>
    );
  }

  return (
    <div className="rounded-xl overflow-hidden border border-gray-800">
      <div className="aspect-video">
        <iframe
          width="100%"
          height="100%"
          src={`https://www.youtube.com/embed/${youtubeId}`}
          title={title || 'Video'}
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
      {title && (
        <div className="bg-cyber-darker px-4 py-2 text-sm text-gray-300">{title}</div>
      )}
    </div>
  );
}

// Diagram Block - Mermaid diagrams with fullscreen support
function DiagramBlock({
  content,
  metadata,
}: {
  content: string;
  metadata: Record<string, any>;
}) {
  const diagramRef = useRef<HTMLDivElement>(null);
  const fullscreenDiagramRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const title = metadata?.title;
  const description = metadata?.description;

  useEffect(() => {
    const renderDiagram = async () => {
      const targetRef = isFullscreen ? fullscreenDiagramRef : diagramRef;
      if (!content || !targetRef.current) return;

      try {
        // Dynamically import mermaid
        const mermaid = (await import('mermaid')).default;

        mermaid.initialize({
          startOnLoad: false,
          theme: 'dark',
          themeVariables: {
            primaryColor: '#00ff9f',
            primaryTextColor: '#fff',
            primaryBorderColor: '#00ff9f',
            lineColor: '#00ff9f',
            secondaryColor: '#1a1a2e',
            tertiaryColor: '#0f0f1a',
          },
        });

        const { svg } = await mermaid.render(`diagram-${Date.now()}-${isFullscreen ? 'fs' : 'normal'}`, content);
        targetRef.current.innerHTML = svg;
        setError(null);
      } catch (err: any) {
        console.error('Mermaid render error:', err);
        setError(err.message || 'Failed to render diagram');
      }
    };

    renderDiagram();
  }, [content, isFullscreen]);

  // Handle escape key to close fullscreen
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isFullscreen]);

  return (
    <>
      {/* Normal view */}
      <div className="bg-cyber-dark rounded-xl border border-gray-800 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-gray-700">
          <span className="text-sm text-gray-300">{title || 'Diagram'}</span>
          <button
            onClick={() => setIsFullscreen(true)}
            className="p-1.5 hover:bg-cyber-accent/20 rounded-lg text-gray-400 hover:text-cyber-accent transition-colors"
            title="View fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
        {description && (
          <div className="px-4 py-2 bg-gray-800/30 text-xs text-gray-400 border-b border-gray-700">
            {description}
          </div>
        )}
        <div className="p-4 flex justify-center overflow-x-auto">
          {error ? (
            <div className="text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 inline mr-2" />
              {error}
            </div>
          ) : (
            <div ref={diagramRef} className="mermaid" />
          )}
        </div>
      </div>

      {/* Fullscreen modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
            <div>
              <h3 className="text-white font-medium">{title || 'Diagram'}</h3>
              {description && <p className="text-sm text-gray-400 mt-1">{description}</p>}
            </div>
            <button
              onClick={() => setIsFullscreen(false)}
              className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
              title="Close fullscreen (Esc)"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Diagram */}
          <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
            {error ? (
              <div className="text-red-400 text-lg">
                <AlertCircle className="w-8 h-8 inline mr-3" />
                {error}
              </div>
            ) : (
              <div
                ref={fullscreenDiagramRef}
                className="mermaid transform scale-125"
                style={{ maxWidth: '90vw', maxHeight: '80vh' }}
              />
            )}
          </div>

          {/* Footer hint */}
          <div className="text-center py-3 text-gray-500 text-sm border-t border-gray-800">
            Press <kbd className="px-2 py-0.5 bg-gray-800 rounded text-gray-300">Esc</kbd> to close
          </div>
        </div>
      )}
    </>
  );
}

// Wikipedia Block - Wikipedia content excerpt
function WikipediaBlock({
  content,
  metadata,
}: {
  content: string;
  metadata: Record<string, any>;
}) {
  const title = metadata?.title;
  const url = metadata?.url;
  const thumbnail = metadata?.thumbnail;

  return (
    <div className="bg-cyber-dark rounded-xl border border-gray-800 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-800/50 border-b border-gray-700">
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/32px-Wikipedia-logo-v2.svg.png"
          alt="Wikipedia"
          className="w-5 h-5"
        />
        <span className="text-sm text-gray-300">Wikipedia</span>
      </div>
      <div className="p-4 flex gap-4">
        {thumbnail && (
          <img
            src={thumbnail}
            alt={title}
            className="w-24 h-24 object-cover rounded-lg flex-shrink-0"
          />
        )}
        <div className="flex-1">
          <h4 className="text-white font-medium mb-2">{title}</h4>
          <p className="text-gray-400 text-sm mb-3">{content}</p>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyber-accent text-sm hover:underline inline-flex items-center gap-1"
            >
              Read more on Wikipedia
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// Callout Block - Tips, warnings, notes
function CalloutBlock({
  content,
  metadata,
}: {
  content: string;
  metadata: Record<string, any>;
}) {
  const calloutType = metadata?.callout_type || 'info';
  const title = metadata?.title;

  const styles: Record<string, { bg: string; border: string; icon: any; iconColor: string }> = {
    tip: {
      bg: 'bg-green-500/10',
      border: 'border-green-500/30',
      icon: Lightbulb,
      iconColor: 'text-green-400',
    },
    warning: {
      bg: 'bg-yellow-500/10',
      border: 'border-yellow-500/30',
      icon: AlertTriangle,
      iconColor: 'text-yellow-400',
    },
    danger: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/30',
      icon: AlertCircle,
      iconColor: 'text-red-400',
    },
    note: {
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/30',
      icon: Info,
      iconColor: 'text-blue-400',
    },
    info: {
      bg: 'bg-cyber-accent/10',
      border: 'border-cyber-accent/30',
      icon: Info,
      iconColor: 'text-cyber-accent',
    },
  };

  const style = styles[calloutType] || styles.info;
  const Icon = style.icon;

  return (
    <div className={`${style.bg} ${style.border} border rounded-xl p-4`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 ${style.iconColor} mt-0.5 flex-shrink-0`} />
        <div className="flex-1">
          {title && <h4 className="text-white font-medium mb-1">{title}</h4>}
          <div className="text-gray-300 text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}

// Collapsible Block - Expandable content
function CollapsibleBlock({
  content,
  metadata,
}: {
  content: string;
  metadata: Record<string, any>;
}) {
  const [isOpen, setIsOpen] = useState(metadata?.default_open || false);
  const title = metadata?.title || 'Click to expand';

  return (
    <div className="bg-cyber-dark rounded-xl border border-gray-800 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-cyber-accent/5 transition-colors"
      >
        <span className="text-white font-medium">{title}</span>
        {isOpen ? (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-gray-400" />
        )}
      </button>
      {isOpen && (
        <div className="px-4 pb-4 border-t border-gray-800">
          <div className="pt-4 text-gray-300 text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

// Inline Quiz Block
function InlineQuizBlock({ metadata }: { metadata: Record<string, any> }) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);

  const question = metadata?.question;
  const options = metadata?.options || [];
  const correctAnswer = metadata?.correct_answer;
  const explanation = metadata?.explanation;

  const handleSubmit = () => {
    setShowResult(true);
  };

  const isCorrect = selectedAnswer === correctAnswer;

  return (
    <div className="bg-cyber-dark rounded-xl border border-gray-800 overflow-hidden">
      <div className="px-4 py-2 bg-gray-800/50 border-b border-gray-700">
        <span className="text-sm text-cyber-accent">Quick Check</span>
      </div>
      <div className="p-4">
        <p className="text-white mb-4">{question}</p>

        <div className="space-y-2 mb-4">
          {options.map((option: string, index: number) => (
            <button
              key={index}
              onClick={() => !showResult && setSelectedAnswer(option)}
              disabled={showResult}
              className={`w-full text-left px-4 py-2 rounded-lg border transition-colors ${
                showResult
                  ? option === correctAnswer
                    ? 'bg-green-500/20 border-green-500 text-green-400'
                    : option === selectedAnswer
                    ? 'bg-red-500/20 border-red-500 text-red-400'
                    : 'bg-gray-800 border-gray-700 text-gray-400'
                  : selectedAnswer === option
                  ? 'bg-cyber-accent/20 border-cyber-accent text-cyber-accent'
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600'
              }`}
            >
              {option}
            </button>
          ))}
        </div>

        {!showResult ? (
          <button
            onClick={handleSubmit}
            disabled={!selectedAnswer}
            className="px-4 py-2 bg-cyber-accent text-black font-medium rounded-lg hover:bg-cyber-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Check Answer
          </button>
        ) : (
          <div
            className={`p-3 rounded-lg ${
              isCorrect ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
            }`}
          >
            <p className="font-medium mb-1">{isCorrect ? 'Correct!' : 'Incorrect'}</p>
            {explanation && <p className="text-sm text-gray-300">{explanation}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
