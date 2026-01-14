import { create } from 'zustand';
import { newsApi } from '@/services/api';

interface SavedArticle {
  id: string;
  title: string;
  summary: string;
  category: string;
  severity?: string;
  source: string;
  date: string;
  tags: string[];
  savedAt?: string;
}

interface NewsStore {
  savedArticles: SavedArticle[];
  favoriteIds: string[];
  isLoading: boolean;
  hasLoaded: boolean;

  // Actions
  loadSavedArticles: () => Promise<void>;
  saveArticle: (article: Omit<SavedArticle, 'savedAt'>) => Promise<void>;
  unsaveArticle: (articleId: string) => Promise<void>;
  isSaved: (articleId: string) => boolean;

  toggleFavorite: (articleId: string) => Promise<void>;
  isFavorite: (articleId: string) => boolean;

  clearAll: () => void;
}

export const useNewsStore = create<NewsStore>()((set, get) => ({
  savedArticles: [],
  favoriteIds: [],
  isLoading: false,
  hasLoaded: false,

  loadSavedArticles: async () => {
    const { hasLoaded, isLoading } = get();
    if (hasLoaded || isLoading) return;

    set({ isLoading: true });
    try {
      const response = await newsApi.getSavedArticles();
      set({
        savedArticles: response.articles.map((a: any) => ({
          id: a.id,
          title: a.title,
          summary: a.summary,
          category: a.category,
          severity: a.severity,
          source: a.source,
          date: a.date,
          tags: a.tags || [],
          savedAt: a.saved_at,
        })),
        favoriteIds: response.favorite_ids || [],
        hasLoaded: true,
        isLoading: false,
      });
    } catch (error) {
      console.error('Failed to load saved articles:', error);
      set({ isLoading: false, hasLoaded: true });
    }
  },

  saveArticle: async (article) => {
    const { savedArticles } = get();
    if (savedArticles.find(a => a.id === article.id)) {
      return; // Already saved
    }

    // Optimistic update
    const newArticle = { ...article, savedAt: new Date().toISOString() };
    set({ savedArticles: [...savedArticles, newArticle] });

    try {
      await newsApi.saveArticle({
        id: article.id,
        title: article.title,
        summary: article.summary,
        category: article.category,
        severity: article.severity,
        source: article.source,
        date: article.date,
        tags: article.tags,
      });
    } catch (error) {
      console.error('Failed to save article:', error);
      // Rollback on error
      set({ savedArticles: savedArticles });
    }
  },

  unsaveArticle: async (articleId) => {
    const { savedArticles, favoriteIds } = get();
    const originalArticles = savedArticles;
    const originalFavorites = favoriteIds;

    // Optimistic update
    set({
      savedArticles: savedArticles.filter(a => a.id !== articleId),
      favoriteIds: favoriteIds.filter(id => id !== articleId)
    });

    try {
      await newsApi.unsaveArticle(articleId);
    } catch (error) {
      console.error('Failed to unsave article:', error);
      // Rollback on error
      set({ savedArticles: originalArticles, favoriteIds: originalFavorites });
    }
  },

  isSaved: (articleId) => {
    return get().savedArticles.some(a => a.id === articleId);
  },

  toggleFavorite: async (articleId) => {
    const { favoriteIds, savedArticles } = get();

    // Only allow favoriting if article is saved
    if (!savedArticles.find(a => a.id === articleId)) {
      return;
    }

    const originalFavorites = favoriteIds;
    const isFav = favoriteIds.includes(articleId);

    // Optimistic update
    if (isFav) {
      set({ favoriteIds: favoriteIds.filter(id => id !== articleId) });
    } else {
      set({ favoriteIds: [...favoriteIds, articleId] });
    }

    try {
      await newsApi.toggleFavorite(articleId);
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      // Rollback on error
      set({ favoriteIds: originalFavorites });
    }
  },

  isFavorite: (articleId) => {
    return get().favoriteIds.includes(articleId);
  },

  clearAll: () => {
    set({ savedArticles: [], favoriteIds: [], hasLoaded: false });
  },
}));
