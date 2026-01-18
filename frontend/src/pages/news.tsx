import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import {
  Newspaper,
  RefreshCw,
  AlertTriangle,
  Shield,
  Bug,
  Lock,
  Globe,
  Server,
  Clock,
  Tag,
  Filter,
  ExternalLink,
  X,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  FileText,
  Cpu,
  Target,
  List,
  Bookmark,
  BookmarkCheck,
  Star,
  Download,
  GraduationCap,
  Loader2
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useNewsStore } from '@/store/newsStore';
import { newsApi, coursesApi } from '@/services/api';

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  category: string;
  severity?: string;
  source: string;
  date: string;
  tags: string[];
}

interface ArticleDetail extends NewsArticle {
  full_analysis: string;
  technical_details: string;
  impact_assessment: string;
  recommendations: string[];
  related_cves: string[];
  affected_systems: string[];
  iocs: string[];
}

interface NewsResponse {
  articles: NewsArticle[];
  generated_at: string;
  cached: boolean;
}

const categoryIcons: Record<string, any> = {
  'Vulnerabilities': Bug,
  'Ransomware': Lock,
  'Data Breach': Server,
  'Malware': Bug,
  'APT': Shield,
  'Patches': Shield,
  'Policy': Globe,
  'Threats': AlertTriangle,
};

const severityColors: Record<string, string> = {
  'Critical': 'bg-red-500/20 text-red-400 border-red-500/30',
  'High': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  'Medium': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'Low': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  'Info': 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

const categoryColors: Record<string, string> = {
  'Vulnerabilities': 'bg-purple-500/20 text-purple-400',
  'Ransomware': 'bg-red-500/20 text-red-400',
  'Data Breach': 'bg-orange-500/20 text-orange-400',
  'Malware': 'bg-pink-500/20 text-pink-400',
  'APT': 'bg-yellow-500/20 text-yellow-400',
  'Patches': 'bg-green-500/20 text-green-400',
  'Policy': 'bg-blue-500/20 text-blue-400',
  'Threats': 'bg-cyan-500/20 text-cyan-400',
};

// Article Detail Modal Component
function ArticleDetailModal({
  articleId,
  articleData,
  onClose,
  onLearnClick
}: {
  articleId: string;
  articleData?: NewsArticle;
  onClose: () => void;
  onLearnClick: (article: NewsArticle) => void;
}) {
  const { data: article, isLoading, error } = useQuery<ArticleDetail>({
    queryKey: ['articleDetail', articleId],
    queryFn: async () => {
      // If we have article data (saved article), use POST endpoint
      if (articleData) {
        return newsApi.getArticleDetailFromData({
          id: articleData.id,
          title: articleData.title,
          summary: articleData.summary,
          category: articleData.category,
          severity: articleData.severity,
          source: articleData.source,
          date: articleData.date,
          tags: articleData.tags,
        });
      }
      // Otherwise use GET endpoint (article from current news cache)
      return newsApi.getArticleDetail(articleId);
    },
    enabled: !!articleId,
  });

  const { saveArticle, unsaveArticle, isSaved, toggleFavorite, isFavorite } = useNewsStore();

  const saved = isSaved(articleId);
  const favorite = isFavorite(articleId);

  const handleLearn = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (article) {
      onLearnClick(article);
      onClose();
    }
  };

  const handleSave = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (article) {
      if (saved) {
        unsaveArticle(articleId);
      } else {
        saveArticle({
          id: article.id,
          title: article.title,
          summary: article.summary,
          category: article.category,
          severity: article.severity,
          source: article.source,
          date: article.date,
          tags: article.tags,
        });
      }
    }
  };

  const handleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (saved) {
      toggleFavorite(articleId);
    }
  };

  const handleDownload = () => {
    if (!article) return;

    const content = `# ${article.title}

**Category:** ${article.category}
**Severity:** ${article.severity || 'Info'}
**Source:** ${article.source}
**Date:** ${article.date}

## Summary
${article.summary}

## Full Analysis
${article.full_analysis}

## Technical Details
${article.technical_details}

## Impact Assessment
${article.impact_assessment}

## Recommendations
${article.recommendations.map(r => `- ${r}`).join('\n')}

## Related CVEs
${article.related_cves.length > 0 ? article.related_cves.join(', ') : 'None'}

## Affected Systems
${article.affected_systems.length > 0 ? article.affected_systems.join(', ') : 'None'}

## Indicators of Compromise (IOCs)
${article.iocs.length > 0 ? article.iocs.join('\n') : 'None'}

---
Saved from CyberAIx - Cyber News
`;

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${article.title.replace(/[^a-z0-9]/gi, '_').substring(0, 50)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const CategoryIcon = article ? (categoryIcons[article.category] || Newspaper) : Newspaper;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden bg-cyber-dark rounded-2xl border border-cyber-accent/30 shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between p-6 border-b border-cyber-accent/20 bg-cyber-dark">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${article ? categoryColors[article.category] || 'bg-gray-500/20' : 'bg-gray-500/20'}`}>
              <CategoryIcon className="w-6 h-6" />
            </div>
            <span className="text-lg font-semibold text-white">Article Analysis</span>
          </div>
          <div className="flex items-center gap-2">
            {article && (
              <>
                <button
                  onClick={handleLearn}
                  className="flex items-center gap-2 px-3 py-2 bg-green-500 text-white font-medium rounded-lg hover:bg-green-600 transition-colors"
                  title="Generate Course & Lab from this article"
                >
                  <GraduationCap className="w-4 h-4" />
                  <span className="hidden sm:inline">Learn This</span>
                </button>
                <button
                  onClick={handleDownload}
                  className="p-2 text-gray-400 hover:text-cyber-accent hover:bg-white/10 rounded-lg transition-colors"
                  title="Download as Markdown"
                >
                  <Download className="w-5 h-5" />
                </button>
                <button
                  onClick={handleFavorite}
                  className={`p-2 rounded-lg transition-colors ${
                    favorite
                      ? 'text-yellow-400 bg-yellow-400/10'
                      : saved
                        ? 'text-gray-400 hover:text-yellow-400 hover:bg-white/10'
                        : 'text-gray-600 cursor-not-allowed'
                  }`}
                  title={saved ? (favorite ? 'Remove from Favorites' : 'Add to Favorites') : 'Save first to add to favorites'}
                  disabled={!saved}
                >
                  <Star className={`w-5 h-5 ${favorite ? 'fill-current' : ''}`} />
                </button>
                <button
                  onClick={handleSave}
                  className={`p-2 rounded-lg transition-colors ${
                    saved
                      ? 'text-cyber-accent bg-cyber-accent/10'
                      : 'text-gray-400 hover:text-cyber-accent hover:bg-white/10'
                  }`}
                  title={saved ? 'Remove from Saved' : 'Save Article'}
                >
                  {saved ? <BookmarkCheck className="w-5 h-5" /> : <Bookmark className="w-5 h-5" />}
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-80px)] p-6">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <RefreshCw className="w-12 h-12 text-cyber-accent animate-spin mb-4" />
              <p className="text-gray-400">Generating detailed analysis...</p>
              <p className="text-gray-500 text-sm mt-2">This may take a few seconds</p>
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <p className="text-red-400">Failed to load article details</p>
            </div>
          )}

          {article && !isLoading && (
            <div className="space-y-6">
              {/* Title and Meta */}
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className={`px-3 py-1 text-sm rounded-full border ${severityColors[article.severity || 'Info']}`}>
                    {article.severity || 'Info'}
                  </span>
                  <span className={`px-3 py-1 text-sm rounded-full ${categoryColors[article.category] || 'bg-gray-500/20 text-gray-400'}`}>
                    {article.category}
                  </span>
                  <span className="flex items-center gap-1 text-gray-500 text-sm">
                    <Clock className="w-4 h-4" />
                    {article.date}
                  </span>
                  <span className="flex items-center gap-1 text-gray-500 text-sm">
                    <ExternalLink className="w-4 h-4" />
                    {article.source}
                  </span>
                </div>
                <h2 className="text-2xl font-bold text-white mb-3">{article.title}</h2>
                <p className="text-gray-300 text-lg leading-relaxed">{article.summary}</p>
              </div>

              {/* Tags */}
              {article.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {article.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-3 py-1 text-sm bg-cyber-darker text-cyber-accent rounded-full"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Full Analysis */}
              <div className="bg-cyber-darker rounded-xl p-5 border border-gray-800">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="w-5 h-5 text-cyber-accent" />
                  <h3 className="text-lg font-semibold text-white">Full Analysis</h3>
                </div>
                <p className="text-gray-300 leading-relaxed whitespace-pre-line">
                  {article.full_analysis}
                </p>
              </div>

              {/* Technical Details */}
              <div className="bg-cyber-darker rounded-xl p-5 border border-gray-800">
                <div className="flex items-center gap-2 mb-3">
                  <Cpu className="w-5 h-5 text-purple-400" />
                  <h3 className="text-lg font-semibold text-white">Technical Details</h3>
                </div>
                <p className="text-gray-300 leading-relaxed whitespace-pre-line">
                  {article.technical_details}
                </p>
              </div>

              {/* Impact Assessment */}
              <div className="bg-cyber-darker rounded-xl p-5 border border-gray-800">
                <div className="flex items-center gap-2 mb-3">
                  <Target className="w-5 h-5 text-orange-400" />
                  <h3 className="text-lg font-semibold text-white">Impact Assessment</h3>
                </div>
                <p className="text-gray-300 leading-relaxed whitespace-pre-line">
                  {article.impact_assessment}
                </p>
              </div>

              {/* Recommendations */}
              {article.recommendations.length > 0 && (
                <div className="bg-cyber-darker rounded-xl p-5 border border-gray-800">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    <h3 className="text-lg font-semibold text-white">Recommendations</h3>
                  </div>
                  <ul className="space-y-2">
                    {article.recommendations.map((rec, index) => (
                      <li key={index} className="flex items-start gap-3 text-gray-300">
                        <ChevronRight className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Technical Indicators Grid */}
              <div className="grid md:grid-cols-3 gap-4">
                {/* Related CVEs */}
                {article.related_cves.length > 0 && (
                  <div className="bg-cyber-darker rounded-xl p-4 border border-gray-800">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertCircle className="w-4 h-4 text-red-400" />
                      <h4 className="font-medium text-white">Related CVEs</h4>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {article.related_cves.map((cve) => (
                        <span
                          key={cve}
                          className="px-2 py-1 text-xs bg-red-500/10 text-red-400 rounded border border-red-500/20 font-mono"
                        >
                          {cve}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Affected Systems */}
                {article.affected_systems.length > 0 && (
                  <div className="bg-cyber-darker rounded-xl p-4 border border-gray-800">
                    <div className="flex items-center gap-2 mb-3">
                      <Server className="w-4 h-4 text-blue-400" />
                      <h4 className="font-medium text-white">Affected Systems</h4>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {article.affected_systems.map((sys) => (
                        <span
                          key={sys}
                          className="px-2 py-1 text-xs bg-blue-500/10 text-blue-400 rounded border border-blue-500/20"
                        >
                          {sys}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* IOCs */}
                {article.iocs.length > 0 && (
                  <div className="bg-cyber-darker rounded-xl p-4 border border-gray-800">
                    <div className="flex items-center gap-2 mb-3">
                      <List className="w-4 h-4 text-yellow-400" />
                      <h4 className="font-medium text-white">IOCs</h4>
                    </div>
                    <div className="space-y-1">
                      {article.iocs.slice(0, 5).map((ioc) => (
                        <div
                          key={ioc}
                          className="text-xs text-yellow-400 font-mono truncate"
                          title={ioc}
                        >
                          {ioc}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

type ViewTab = 'all' | 'saved' | 'favorites';

interface GeneratingState {
  articleId: string | null;
  isGenerating: boolean;
  error: string | null;
  success: { courseId: string; courseSlug: string; labId?: string } | null;
}

interface CourseGenerationOptions {
  num_modules: number;
  lesson_length: 'short' | 'medium' | 'long';
  include_code_examples: boolean;
  include_diagrams: boolean;
  include_quizzes: boolean;
  difficulty_override: 'beginner' | 'intermediate' | 'advanced' | null;
}

// Learn This Options Modal Component
function LearnOptionsModal({
  article,
  onClose,
  onGenerate,
}: {
  article: NewsArticle;
  onClose: () => void;
  onGenerate: (options: CourseGenerationOptions) => void;
}) {
  const [options, setOptions] = useState<CourseGenerationOptions>({
    num_modules: 4,
    lesson_length: 'medium',
    include_code_examples: true,
    include_diagrams: true,
    include_quizzes: true,
    difficulty_override: null,
  });

  const difficultyLabels: Record<string, { label: string; desc: string }> = {
    beginner: { label: 'Beginner', desc: 'New to cybersecurity' },
    intermediate: { label: 'Intermediate', desc: 'Some experience' },
    advanced: { label: 'Advanced', desc: 'Expert level' },
  };

  const lessonLengthLabels: Record<string, { label: string; desc: string }> = {
    short: { label: 'Short', desc: '500-800 words' },
    medium: { label: 'Medium', desc: '800-1200 words' },
    long: { label: 'Long', desc: '1200-1800 words' },
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-cyber-dark rounded-2xl border border-cyber-accent/30 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-cyber-accent/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <GraduationCap className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Generate Course</h2>
              <p className="text-sm text-gray-400">Customize your learning experience</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Article Preview */}
          <div className="p-4 bg-cyber-darker rounded-lg border border-gray-700">
            <p className="text-sm text-gray-400 mb-1">Generating course from:</p>
            <p className="text-white font-medium line-clamp-2">{article.title}</p>
          </div>

          {/* Number of Modules */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Number of Modules
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="3"
                max="8"
                value={options.num_modules}
                onChange={(e) => setOptions({ ...options, num_modules: parseInt(e.target.value) })}
                className="flex-1 h-2 bg-cyber-darker rounded-lg appearance-none cursor-pointer accent-cyber-accent"
              />
              <span className="w-8 text-center text-white font-mono">{options.num_modules}</span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Each module contains 3-4 lessons</p>
          </div>

          {/* Lesson Length */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Lesson Length
            </label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(lessonLengthLabels).map(([key, { label, desc }]) => (
                <button
                  key={key}
                  onClick={() => setOptions({ ...options, lesson_length: key as any })}
                  className={`p-3 rounded-lg border text-center transition-colors ${
                    options.lesson_length === key
                      ? 'bg-cyber-accent/20 border-cyber-accent text-cyber-accent'
                      : 'bg-cyber-darker border-gray-700 text-gray-300 hover:border-gray-600'
                  }`}
                >
                  <div className="font-medium">{label}</div>
                  <div className="text-xs text-gray-500 mt-1">{desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Difficulty Override */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Difficulty Level
            </label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(difficultyLabels).map(([key, { label, desc }]) => (
                <button
                  key={key}
                  onClick={() => setOptions({
                    ...options,
                    difficulty_override: options.difficulty_override === key ? null : key as any
                  })}
                  className={`p-3 rounded-lg border text-center transition-colors ${
                    options.difficulty_override === key
                      ? 'bg-cyber-accent/20 border-cyber-accent text-cyber-accent'
                      : 'bg-cyber-darker border-gray-700 text-gray-300 hover:border-gray-600'
                  }`}
                >
                  <div className="font-medium">{label}</div>
                  <div className="text-xs text-gray-500 mt-1">{desc}</div>
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-1">Leave unselected to auto-detect from article severity</p>
          </div>

          {/* Content Options */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Content Options
            </label>
            <div className="space-y-3">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.include_code_examples}
                  onChange={(e) => setOptions({ ...options, include_code_examples: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-600 bg-cyber-darker text-cyber-accent focus:ring-cyber-accent focus:ring-offset-0"
                />
                <span className="text-gray-300">Include code examples</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.include_diagrams}
                  onChange={(e) => setOptions({ ...options, include_diagrams: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-600 bg-cyber-darker text-cyber-accent focus:ring-cyber-accent focus:ring-offset-0"
                />
                <span className="text-gray-300">Include diagrams & flowcharts</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.include_quizzes}
                  onChange={(e) => setOptions({ ...options, include_quizzes: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-600 bg-cyber-darker text-cyber-accent focus:ring-cyber-accent focus:ring-offset-0"
                />
                <span className="text-gray-300">Include quizzes & review questions</span>
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-cyber-accent/20 bg-cyber-darker/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onGenerate(options)}
            className="flex items-center gap-2 px-6 py-2 bg-green-500 text-white font-medium rounded-lg hover:bg-green-600 transition-colors"
          >
            <GraduationCap className="w-5 h-5" />
            Generate Course
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CyberNews() {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const { savedArticles, favoriteIds, saveArticle, unsaveArticle, isSaved, toggleFavorite, isFavorite } = useNewsStore();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [selectedArticleData, setSelectedArticleData] = useState<NewsArticle | null>(null);
  const [activeTab, setActiveTab] = useState<ViewTab>('all');
  const [learnOptionsArticle, setLearnOptionsArticle] = useState<NewsArticle | null>(null);
  const [generating, setGenerating] = useState<GeneratingState>({
    articleId: null,
    isGenerating: false,
    error: null,
    success: null,
  });

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  const { data: newsData, isLoading, error, refetch, isFetching } = useQuery<NewsResponse>({
    queryKey: ['cyberNews'],
    queryFn: () => newsApi.getNews(false),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
  });

  const handleRefresh = () => {
    newsApi.getNews(true).then(() => refetch());
  };

  const handleSaveArticle = (e: React.MouseEvent, article: NewsArticle) => {
    e.stopPropagation();
    if (isSaved(article.id)) {
      unsaveArticle(article.id);
    } else {
      saveArticle(article);
    }
  };

  const handleToggleFavorite = (e: React.MouseEvent, articleId: string) => {
    e.stopPropagation();
    if (isSaved(articleId)) {
      toggleFavorite(articleId);
    }
  };

  const handleLearnFromNews = (article: NewsArticle) => {
    // Show the options modal instead of immediately generating
    setLearnOptionsArticle(article);
  };

  const handleGenerateWithOptions = async (options: CourseGenerationOptions) => {
    if (!learnOptionsArticle) return;

    const article = learnOptionsArticle;
    setLearnOptionsArticle(null); // Close the modal

    setGenerating({
      articleId: article.id,
      isGenerating: true,
      error: null,
      success: null,
    });

    try {
      const result = await coursesApi.generateFromNews({
        article_id: article.id,
        title: article.title,
        summary: article.summary,
        category: article.category,
        severity: article.severity,
        tags: article.tags,
        num_modules: options.num_modules,
        lesson_length: options.lesson_length,
        include_code_examples: options.include_code_examples,
        include_diagrams: options.include_diagrams,
        include_quizzes: options.include_quizzes,
        difficulty_override: options.difficulty_override || undefined,
      });

      setGenerating({
        articleId: article.id,
        isGenerating: false,
        error: null,
        success: {
          courseId: result.course_id,
          courseSlug: result.course_slug,
          labId: result.lab_id,
        },
      });

      // Redirect to the course after a short delay
      setTimeout(() => {
        router.push(`/courses?highlight=${result.course_id}`);
      }, 2000);

    } catch (err: any) {
      setGenerating({
        articleId: article.id,
        isGenerating: false,
        error: err.response?.data?.detail || 'Failed to generate learning content',
        success: null,
      });
    }
  };

  // Get articles based on active tab
  const getArticlesForTab = (): NewsArticle[] => {
    if (activeTab === 'saved') {
      return savedArticles;
    }
    if (activeTab === 'favorites') {
      return savedArticles.filter(a => favoriteIds.includes(a.id));
    }
    return newsData?.articles || [];
  };

  const filteredArticles = getArticlesForTab().filter((article) => {
    if (selectedCategory !== 'all' && article.category !== selectedCategory) {
      return false;
    }
    if (selectedSeverity !== 'all' && article.severity !== selectedSeverity) {
      return false;
    }
    return true;
  });

  const categories = Array.from(new Set(newsData?.articles.map((a: NewsArticle) => a.category) || []));
  const severities = Array.from(new Set(newsData?.articles.map((a: NewsArticle) => a.severity).filter(Boolean) || []));

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="p-8">
      {/* Article Detail Modal */}
      {selectedArticleId && (
        <ArticleDetailModal
          articleId={selectedArticleId}
          articleData={selectedArticleData || undefined}
          onClose={() => {
            setSelectedArticleId(null);
            setSelectedArticleData(null);
          }}
          onLearnClick={handleLearnFromNews}
        />
      )}

      {/* Learn Options Modal */}
      {learnOptionsArticle && (
        <LearnOptionsModal
          article={learnOptionsArticle}
          onClose={() => setLearnOptionsArticle(null)}
          onGenerate={handleGenerateWithOptions}
        />
      )}

      {/* Generating Overlay */}
      {generating.isGenerating && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-8 max-w-md text-center">
            <Loader2 className="w-16 h-16 text-cyber-accent animate-spin mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">Generating Learning Content</h3>
            <p className="text-gray-400 mb-4">
              AI is creating a personalized course and lab based on this article...
            </p>
            <p className="text-gray-500 text-sm">This may take 30-60 seconds</p>
          </div>
        </div>
      )}

      {/* Success Toast */}
      {generating.success && (
        <div className="fixed bottom-6 right-6 z-[60] bg-green-500 text-white px-6 py-4 rounded-xl shadow-2xl flex items-center gap-4 animate-in slide-in-from-bottom-5">
          <CheckCircle className="w-8 h-8" />
          <div>
            <p className="font-bold">Course & Lab Created!</p>
            <p className="text-sm opacity-90">Redirecting to your new course...</p>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {generating.error && (
        <div className="fixed bottom-6 right-6 z-[60] bg-red-500 text-white px-6 py-4 rounded-xl shadow-2xl flex items-center gap-4">
          <AlertTriangle className="w-8 h-8" />
          <div>
            <p className="font-bold">Generation Failed</p>
            <p className="text-sm opacity-90">{generating.error}</p>
          </div>
          <button
            onClick={() => setGenerating(g => ({ ...g, error: null }))}
            className="ml-2 p-1 hover:bg-white/20 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Newspaper className="w-8 h-8 text-cyber-accent" />
            Cyber News
          </h1>
          <p className="text-gray-400 mt-1">
            Latest cybersecurity news and threat intelligence
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isFetching || activeTab !== 'all'}
          className="flex items-center gap-2 px-4 py-2 bg-cyber-accent text-cyber-dark font-medium rounded-lg hover:bg-cyber-accent/90 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          {isFetching ? 'Updating...' : 'Refresh News'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6 border-b border-gray-700 pb-4">
        <button
          onClick={() => setActiveTab('all')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'all'
              ? 'bg-cyber-accent text-cyber-dark'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Newspaper className="w-4 h-4" />
          All News
        </button>
        <button
          onClick={() => setActiveTab('saved')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'saved'
              ? 'bg-cyber-accent text-cyber-dark'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Bookmark className="w-4 h-4" />
          Saved
          {savedArticles.length > 0 && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              activeTab === 'saved' ? 'bg-cyber-dark/30' : 'bg-gray-700'
            }`}>
              {savedArticles.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('favorites')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'favorites'
              ? 'bg-yellow-500 text-cyber-dark'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Star className="w-4 h-4" />
          Favorites
          {favoriteIds.length > 0 && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              activeTab === 'favorites' ? 'bg-cyber-dark/30' : 'bg-gray-700'
            }`}>
              {favoriteIds.length}
            </span>
          )}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-cyber-dark border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyber-accent"
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-gray-400" />
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-cyber-dark border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyber-accent"
          >
            <option value="all">All Severities</option>
            {severities.map((sev) => (
              <option key={sev} value={sev}>{sev}</option>
            ))}
          </select>
        </div>
        {newsData?.cached && (
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Cached data
          </span>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <RefreshCw className="w-12 h-12 text-cyber-accent animate-spin mx-auto mb-4" />
            <p className="text-gray-400">Fetching latest cyber news...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400">Failed to load news. Please try again.</p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* News Grid */}
      {!isLoading && !error && (
        <div className="grid gap-6">
          {filteredArticles.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              {activeTab === 'saved' ? (
                <>
                  <Bookmark className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No saved articles yet</p>
                  <p className="text-sm mt-2">Click the bookmark icon on any article to save it</p>
                </>
              ) : activeTab === 'favorites' ? (
                <>
                  <Star className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No favorite articles yet</p>
                  <p className="text-sm mt-2">Save an article first, then click the star to add to favorites</p>
                </>
              ) : (
                <>
                  <Newspaper className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No news articles match your filters</p>
                </>
              )}
            </div>
          ) : (
            filteredArticles.map((article) => {
              const CategoryIcon = categoryIcons[article.category] || Newspaper;
              const articleSaved = isSaved(article.id);
              const articleFavorite = isFavorite(article.id);
              return (
                <article
                  key={article.id}
                  onClick={() => {
                    setSelectedArticleId(article.id);
                    // Pass article data for saved/favorites tabs so details can be generated even if not in server cache
                    if (activeTab === 'saved' || activeTab === 'favorites') {
                      setSelectedArticleData(article);
                    } else {
                      setSelectedArticleData(null);
                    }
                  }}
                  className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6 hover:border-cyber-accent/40 transition-all cursor-pointer hover:shadow-lg hover:shadow-cyber-accent/5 group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <div className={`p-2 rounded-lg ${categoryColors[article.category] || 'bg-gray-500/20'}`}>
                          <CategoryIcon className="w-5 h-5" />
                        </div>
                        <span className={`px-2 py-1 text-xs rounded border ${severityColors[article.severity || 'Info']}`}>
                          {article.severity || 'Info'}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded ${categoryColors[article.category] || 'bg-gray-500/20 text-gray-400'}`}>
                          {article.category}
                        </span>
                      </div>

                      <h2 className="text-xl font-semibold text-white mb-2 group-hover:text-cyber-accent transition-colors">
                        {article.title}
                      </h2>

                      <p className="text-gray-400 mb-4 leading-relaxed">
                        {article.summary}
                      </p>

                      <div className="flex flex-wrap items-center gap-4 text-sm">
                        <span className="flex items-center gap-1 text-gray-500">
                          <ExternalLink className="w-4 h-4" />
                          {article.source}
                        </span>
                        <span className="flex items-center gap-1 text-gray-500">
                          <Clock className="w-4 h-4" />
                          {article.date}
                        </span>
                        {article.tags.length > 0 && (
                          <div className="flex items-center gap-2">
                            <Tag className="w-4 h-4 text-gray-500" />
                            {article.tags.slice(0, 3).map((tag) => (
                              <span
                                key={tag}
                                className="px-2 py-0.5 text-xs bg-cyber-darker text-gray-400 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLearnFromNews(article);
                        }}
                        disabled={generating.isGenerating}
                        className={`p-2 rounded-lg transition-colors ${
                          generating.articleId === article.id && generating.isGenerating
                            ? 'text-green-400 bg-green-400/10 cursor-wait'
                            : 'text-gray-500 hover:text-green-400 hover:bg-green-400/10'
                        }`}
                        title="Generate Course & Lab from this article"
                      >
                        {generating.articleId === article.id && generating.isGenerating ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <GraduationCap className="w-5 h-5" />
                        )}
                      </button>
                      <button
                        onClick={(e) => handleToggleFavorite(e, article.id)}
                        className={`p-2 rounded-lg transition-colors ${
                          articleFavorite
                            ? 'text-yellow-400 bg-yellow-400/10'
                            : articleSaved
                              ? 'text-gray-500 hover:text-yellow-400 hover:bg-white/5'
                              : 'text-gray-700 cursor-not-allowed'
                        }`}
                        title={articleSaved ? (articleFavorite ? 'Remove from Favorites' : 'Add to Favorites') : 'Save first to favorite'}
                        disabled={!articleSaved}
                      >
                        <Star className={`w-5 h-5 ${articleFavorite ? 'fill-current' : ''}`} />
                      </button>
                      <button
                        onClick={(e) => handleSaveArticle(e, article)}
                        className={`p-2 rounded-lg transition-colors ${
                          articleSaved
                            ? 'text-cyber-accent bg-cyber-accent/10'
                            : 'text-gray-500 hover:text-cyber-accent hover:bg-white/5'
                        }`}
                        title={articleSaved ? 'Remove from Saved' : 'Save Article'}
                      >
                        {articleSaved ? <BookmarkCheck className="w-5 h-5" /> : <Bookmark className="w-5 h-5" />}
                      </button>
                      <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-cyber-accent transition-colors" />
                    </div>
                  </div>
                </article>
              );
            })
          )}
        </div>
      )}

      {/* Stats Footer */}
      {!isLoading && (
        <div className="mt-8 text-center text-sm text-gray-500">
          {activeTab === 'all' && newsData && (
            <>
              Showing {filteredArticles.length} of {newsData.articles.length} articles
              {newsData.generated_at && (
                <span className="ml-2">
                  | Last updated: {new Date(newsData.generated_at).toLocaleString()}
                </span>
              )}
            </>
          )}
          {activeTab === 'saved' && (
            <>Showing {filteredArticles.length} of {savedArticles.length} saved articles</>
          )}
          {activeTab === 'favorites' && (
            <>Showing {filteredArticles.length} of {favoriteIds.length} favorite articles</>
          )}
          <span className="ml-2">| Click on any article for detailed analysis</span>
        </div>
      )}
    </div>
  );
}
