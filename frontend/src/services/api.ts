import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://cyyberaix.in');

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      if (typeof window !== 'undefined') {
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: async (data: { email: string; username: string; password: string; full_name?: string }) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login/json', { email, password });
    return response.data;
  },
  me: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// Chat API
export const chatApi = {
  createSession: async (data: { title?: string; teaching_mode?: string; topic?: string }) => {
    const response = await api.post('/chat/sessions', data);
    return response.data;
  },
  listSessions: async () => {
    const response = await api.get('/chat/sessions');
    return response.data;
  },
  getSession: async (sessionId: string) => {
    const response = await api.get(`/chat/sessions/${sessionId}`);
    return response.data;
  },
  sendMessage: async (sessionId: string, content: string) => {
    const response = await api.post(`/chat/sessions/${sessionId}/messages`, { content });
    return response.data;
  },
  deleteSession: async (sessionId: string) => {
    const response = await api.delete(`/chat/sessions/${sessionId}`);
    return response.data;
  },
  renameSession: async (sessionId: string, title: string) => {
    const response = await api.patch(`/chat/sessions/${sessionId}`, { title });
    return response.data;
  },
  quickAsk: async (content: string, teachingMode: string = 'lecture') => {
    const response = await api.post('/chat/quick-ask', { content }, { params: { teaching_mode: teachingMode } });
    return response.data;
  },
};

// Courses API
export const coursesApi = {
  list: async (params?: { category?: string; difficulty?: string; search?: string; limit?: number; page?: number; page_size?: number }) => {
    const response = await api.get('/courses', { params });
    return response.data;
  },
  get: async (courseId: string) => {
    const response = await api.get(`/courses/${courseId}`);
    return response.data;
  },
  getBySlug: async (slug: string) => {
    const response = await api.get(`/courses/slug/${slug}`);
    return response.data;
  },
  getFullLesson: async (courseId: string, lessonId: string) => {
    const response = await api.get(`/courses/${courseId}/lessons/${lessonId}/full`);
    return response.data;
  },
  generate: async (topic: string, difficulty: string = 'beginner', numModules: number = 5) => {
    const response = await api.post('/courses/generate', null, {
      params: { topic, difficulty, num_modules: numModules },
    });
    return response.data;
  },
  generateAdvanced: async (options: {
    topic: string;
    difficulty?: string;
    num_modules?: number;
    include_code_examples?: boolean;
    include_diagrams?: boolean;
    include_videos?: boolean;
    include_wikipedia?: boolean;
    include_quizzes?: boolean;
    target_lesson_length?: number;
  }) => {
    const response = await api.post('/courses/generate/advanced', options);
    return response.data;
  },
  getGenerationStatus: async (jobId: string) => {
    const response = await api.get(`/courses/generate/${jobId}/status`);
    return response.data;
  },
  regenerateLesson: async (jobId: string, lessonId: string) => {
    const response = await api.post(`/courses/generate/${jobId}/regenerate-lesson/${lessonId}`);
    return response.data;
  },
  generateFromNews: async (article: {
    article_id: string;
    title: string;
    summary: string;
    category: string;
    severity?: string;
    tags: string[];
  }) => {
    const response = await api.post('/courses/generate-from-news', article);
    return response.data;
  },
  publish: async (courseId: string) => {
    const response = await api.patch(`/courses/${courseId}/publish`);
    return response.data;
  },
  delete: async (courseId: string) => {
    const response = await api.delete(`/courses/${courseId}`);
    return response.data;
  },
};

// External Content API
export const externalApi = {
  searchWikipedia: async (query: string, limit: number = 5) => {
    const response = await api.get('/courses/external/wikipedia/search', { params: { query, limit } });
    return response.data;
  },
  getWikipediaSummary: async (topic: string) => {
    const response = await api.get('/courses/external/wikipedia/summary', { params: { topic } });
    return response.data;
  },
  searchImages: async (query: string, source: string = 'auto', limit: number = 5) => {
    const response = await api.get('/courses/external/images/search', { params: { query, source, limit } });
    return response.data;
  },
  searchYouTube: async (query: string, difficulty: string = 'beginner', limit: number = 5) => {
    const response = await api.get('/courses/external/youtube/search', { params: { query, difficulty, limit } });
    return response.data;
  },
};

// Labs API
export const labsApi = {
  list: async (params?: { lab_type?: string; difficulty?: string; category?: string; limit?: number }) => {
    const response = await api.get('/labs', { params });
    return response.data;
  },
  get: async (labId: string) => {
    const response = await api.get(`/labs/${labId}`);
    return response.data;
  },
  startSession: async (labId: string) => {
    const response = await api.post(`/labs/${labId}/sessions`);
    return response.data;
  },
  submitFlag: async (sessionId: string, flag: string) => {
    const response = await api.post(`/labs/sessions/${sessionId}/flags`, { flag });
    return response.data;
  },
  stopSession: async (sessionId: string) => {
    const response = await api.post(`/labs/sessions/${sessionId}/stop`);
    return response.data;
  },
  // Course integration methods
  startInCourse: async (data: { course_id: string; lesson_id: string; lab_id: string }) => {
    const response = await api.post('/labs/start-in-course', data);
    return response.data;
  },
  completeObjective: async (sessionId: string, objectiveIndex: number) => {
    const response = await api.post(`/labs/sessions/${sessionId}/objectives/${objectiveIndex}/complete`);
    return response.data;
  },
  getLabProgress: async (courseId: string) => {
    const response = await api.get(`/labs/progress/${courseId}`);
    return response.data;
  },
  endSession: async (sessionId: string) => {
    const response = await api.post(`/labs/sessions/${sessionId}/end`);
    return response.data;
  },
};

// Skills API
export const skillsApi = {
  getMySkills: async () => {
    const response = await api.get('/skills/my');
    return response.data;
  },
  getRecommendations: async () => {
    const response = await api.get('/skills/recommendations');
    return response.data;
  },
  getSkillTree: async () => {
    const response = await api.get('/skills/tree');
    return response.data;
  },
};

// Users API
export const usersApi = {
  getProfile: async () => {
    const response = await api.get('/users/me');
    return response.data;
  },
  updateProfile: async (data: any) => {
    const response = await api.patch('/users/me', data);
    return response.data;
  },
  getStats: async () => {
    const response = await api.get('/users/me/stats');
    return response.data;
  },
};

// VM API (Alphha Linux)
export const vmApi = {
  getPresets: async () => {
    const response = await api.get('/labs/alphha/presets');
    return response.data;
  },
  getTemplates: async () => {
    const response = await api.get('/labs/alphha/templates');
    return response.data;
  },
  checkImages: async () => {
    const response = await api.get('/labs/alphha/images');
    return response.data;
  },
  startVM: async (preset: string = 'minimal') => {
    const response = await api.post('/labs/alphha/start', null, { params: { preset } });
    return response.data;
  },
  startTemplateVM: async (templateId: string) => {
    const response = await api.post(`/labs/alphha/template/${templateId}/start`);
    return response.data;
  },
  getVMStatus: async () => {
    const response = await api.get('/labs/vm/status');
    return response.data;
  },
  getActiveSessions: async () => {
    const response = await api.get('/labs/sessions/my');
    return response.data;
  },
  stopSession: async (sessionId: string) => {
    const response = await api.post(`/labs/sessions/${sessionId}/stop`);
    return response.data;
  },
};

// News API - Real-time cybersecurity news from Hacker News, Reddit, NewsAPI
export const newsApi = {
  getNews: async (refresh: boolean = false) => {
    const response = await api.get('/news', { params: { refresh } });
    return response.data;
  },
  getTrending: async (limit: number = 10) => {
    const response = await api.get('/news/trending', { params: { limit } });
    return response.data;
  },
  getRecent: async (limit: number = 20) => {
    const response = await api.get('/news/recent', { params: { limit } });
    return response.data;
  },
  getCategories: async () => {
    const response = await api.get('/news/categories');
    return response.data;
  },
  getByCategory: async (category: string, limit: number = 20) => {
    const response = await api.get(`/news/by-category/${category}`, { params: { limit } });
    return response.data;
  },
  getBySeverity: async (severity: string, limit: number = 20) => {
    const response = await api.get(`/news/by-severity/${severity}`, { params: { limit } });
    return response.data;
  },
  getBySource: async (source: string, limit: number = 20) => {
    const response = await api.get(`/news/by-source/${source}`, { params: { limit } });
    return response.data;
  },
  search: async (query: string, limit: number = 20) => {
    const response = await api.get('/news/search', { params: { q: query, limit } });
    return response.data;
  },
  getArticleDetail: async (articleId: string) => {
    const response = await api.get(`/news/article/${articleId}`);
    return response.data;
  },
  getArticleDetailFromData: async (article: {
    id: string;
    title: string;
    summary: string;
    category: string;
    severity?: string;
    source: string;
    source_url?: string;
    date: string;
    tags: string[];
  }) => {
    const response = await api.post('/news/article/details', article);
    return response.data;
  },
  // Saved articles (persisted to database)
  getSavedArticles: async () => {
    const response = await api.get('/news/saved');
    return response.data;
  },
  saveArticle: async (article: {
    id: string;
    title: string;
    summary: string;
    category: string;
    severity?: string;
    source: string;
    source_url?: string;
    date: string;
    tags: string[];
  }) => {
    const response = await api.post('/news/saved', article);
    return response.data;
  },
  unsaveArticle: async (articleId: string) => {
    const response = await api.delete(`/news/saved/${articleId}`);
    return response.data;
  },
  toggleFavorite: async (articleId: string) => {
    const response = await api.post(`/news/saved/${articleId}/favorite`);
    return response.data;
  },
};

// Organizations API
export const organizationsApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string }) => {
    const response = await api.get('/organizations', { params });
    return response.data;
  },
  get: async (orgId: string) => {
    const response = await api.get(`/organizations/${orgId}`);
    return response.data;
  },
  create: async (data: {
    name: string;
    org_type?: string;
    description?: string;
    logo_url?: string;
    contact_email?: string;
    subscription_tier?: string;
    max_members?: number;
  }) => {
    const response = await api.post('/organizations', data);
    return response.data;
  },
  update: async (orgId: string, data: any) => {
    const response = await api.patch(`/organizations/${orgId}`, data);
    return response.data;
  },
  delete: async (orgId: string) => {
    const response = await api.delete(`/organizations/${orgId}`);
    return response.data;
  },
  getMembers: async (orgId: string, params?: { page?: number; page_size?: number; role?: string; search?: string }) => {
    const response = await api.get(`/organizations/${orgId}/members`, { params });
    return response.data;
  },
  addMember: async (orgId: string, data: { user_id: string; role?: string }) => {
    const response = await api.post(`/organizations/${orgId}/members`, data);
    return response.data;
  },
  updateMember: async (orgId: string, userId: string, data: { role?: string; is_active?: boolean }) => {
    const response = await api.patch(`/organizations/${orgId}/members/${userId}`, data);
    return response.data;
  },
  removeMember: async (orgId: string, userId: string) => {
    const response = await api.delete(`/organizations/${orgId}/members/${userId}`);
    return response.data;
  },
  getDashboard: async (orgId: string) => {
    const response = await api.get(`/organizations/${orgId}/dashboard`);
    return response.data;
  },
};

// Batches API
export const batchesApi = {
  list: async (orgId: string, params?: { page?: number; page_size?: number; status?: string; search?: string }) => {
    const response = await api.get(`/organizations/${orgId}/batches`, { params });
    return response.data;
  },
  get: async (batchId: string) => {
    const response = await api.get(`/batches/${batchId}`);
    return response.data;
  },
  create: async (orgId: string, data: {
    name: string;
    description?: string;
    start_date?: string;
    end_date?: string;
    max_users?: number;
  }) => {
    const response = await api.post(`/organizations/${orgId}/batches`, data);
    return response.data;
  },
  update: async (batchId: string, data: any) => {
    const response = await api.patch(`/batches/${batchId}`, data);
    return response.data;
  },
  delete: async (batchId: string) => {
    const response = await api.delete(`/batches/${batchId}`);
    return response.data;
  },
  getMembers: async (batchId: string, params?: { page?: number; page_size?: number; search?: string }) => {
    const response = await api.get(`/batches/${batchId}/members`, { params });
    return response.data;
  },
  addMembers: async (batchId: string, data: { user_ids: string[] }) => {
    const response = await api.post(`/batches/${batchId}/members`, data);
    return response.data;
  },
  removeMember: async (batchId: string, userId: string) => {
    const response = await api.delete(`/batches/${batchId}/members/${userId}`);
    return response.data;
  },
  updateCurriculum: async (batchId: string, data: { course_ids: string[] }) => {
    const response = await api.patch(`/batches/${batchId}/curriculum`, data);
    return response.data;
  },
  getLeaderboard: async (batchId: string, params?: { limit?: number }) => {
    const response = await api.get(`/batches/${batchId}/leaderboard`, { params });
    return response.data;
  },
};

// Invitations API
export const invitationsApi = {
  create: async (orgId: string, data: {
    email: string;
    role?: string;
    batch_id?: string;
    full_name?: string;
    message?: string;
    expires_days?: number;
  }) => {
    const response = await api.post(`/organizations/${orgId}/invitations`, data);
    return response.data;
  },
  createBulk: async (orgId: string, data: { invitations: any[] }) => {
    const response = await api.post(`/organizations/${orgId}/invitations/bulk`, data);
    return response.data;
  },
  list: async (orgId: string, params?: { page?: number; page_size?: number; status_filter?: string; search?: string }) => {
    const response = await api.get(`/organizations/${orgId}/invitations`, { params });
    return response.data;
  },
  cancel: async (inviteId: string) => {
    const response = await api.delete(`/invitations/${inviteId}`);
    return response.data;
  },
  resend: async (inviteId: string, data?: { send_email?: boolean }) => {
    const response = await api.post(`/invitations/${inviteId}/resend`, data || { send_email: true });
    return response.data;
  },
  // Public endpoints (no auth required)
  getByToken: async (token: string) => {
    const response = await api.get(`/invite/${token}`);
    return response.data;
  },
  accept: async (token: string, data?: { username?: string; password?: string }) => {
    const response = await api.post(`/invite/${token}/accept`, data || {});
    return response.data;
  },
  decline: async (token: string) => {
    const response = await api.post(`/invite/${token}/decline`);
    return response.data;
  },
};

// Limits API
export const limitsApi = {
  getDefaults: async () => {
    const response = await api.get('/limits/defaults');
    return response.data;
  },
  updateDefaults: async (data: any) => {
    const response = await api.patch('/limits/defaults', data);
    return response.data;
  },
  getMyLimits: async () => {
    const response = await api.get('/limits/my');
    return response.data;
  },
  getOrgLimits: async (orgId: string) => {
    const response = await api.get(`/limits/organizations/${orgId}`);
    return response.data;
  },
  updateOrgLimits: async (orgId: string, data: any) => {
    const response = await api.patch(`/limits/organizations/${orgId}`, data);
    return response.data;
  },
  getBatchLimits: async (batchId: string) => {
    const response = await api.get(`/limits/batches/${batchId}`);
    return response.data;
  },
  updateBatchLimits: async (batchId: string, data: any) => {
    const response = await api.patch(`/limits/batches/${batchId}`, data);
    return response.data;
  },
  getUserLimits: async (userId: string) => {
    const response = await api.get(`/limits/users/${userId}`);
    return response.data;
  },
  setUserOverride: async (userId: string, data: any) => {
    const response = await api.post(`/limits/users/${userId}`, data);
    return response.data;
  },
  updateUserOverride: async (userId: string, data: any) => {
    const response = await api.patch(`/limits/users/${userId}`, data);
    return response.data;
  },
  removeUserOverride: async (userId: string) => {
    const response = await api.delete(`/limits/users/${userId}`);
    return response.data;
  },
};

// Analytics API
export const analyticsApi = {
  getMy: async () => {
    const response = await api.get('/analytics/my');
    return response.data;
  },
  getMyProgress: async () => {
    const response = await api.get('/analytics/my/progress');
    return response.data;
  },
  getMyBenchmark: async () => {
    const response = await api.get('/analytics/my/benchmark');
    return response.data;
  },
  getOrg: async (orgId: string) => {
    const response = await api.get(`/analytics/organizations/${orgId}`);
    return response.data;
  },
  getOrgUsers: async (orgId: string, params?: { page?: number; page_size?: number }) => {
    const response = await api.get(`/analytics/organizations/${orgId}/users`, { params });
    return response.data;
  },
  getBatch: async (batchId: string) => {
    const response = await api.get(`/analytics/batches/${batchId}`);
    return response.data;
  },
  getBatchLeaderboard: async (batchId: string, params?: { limit?: number }) => {
    const response = await api.get(`/analytics/batches/${batchId}/leaderboard`, { params });
    return response.data;
  },
  getUser: async (userId: string) => {
    const response = await api.get(`/analytics/users/${userId}`);
    return response.data;
  },
  exportOrg: async (orgId: string, data: {
    format?: string;
    include_user_details?: boolean;
    include_progress?: boolean;
    include_activity?: boolean;
    date_from?: string;
    date_to?: string;
  }) => {
    const response = await api.post(`/analytics/organizations/${orgId}/export`, data);
    return response.data;
  },
  exportBatch: async (batchId: string, data: any) => {
    const response = await api.post(`/analytics/batches/${batchId}/export`, data);
    return response.data;
  },
};

// Environments API (Persistent Terminal/Desktop)
export const environmentsApi = {
  getMy: async () => {
    const response = await api.get('/environments/my');
    return response.data;
  },
  start: async (type: 'terminal' | 'desktop') => {
    const response = await api.post(`/environments/my/${type}/start`);
    return response.data;
  },
  stop: async (type: 'terminal' | 'desktop') => {
    const response = await api.post(`/environments/my/${type}/stop`);
    return response.data;
  },
  getStatus: async (type: 'terminal' | 'desktop') => {
    const response = await api.get(`/environments/my/${type}/status`);
    return response.data;
  },
  reset: async (type: 'terminal' | 'desktop') => {
    const response = await api.post(`/environments/my/${type}/reset`);
    return response.data;
  },
};

// Monitoring API (Admin - Server Performance)
export const monitoringApi = {
  getResources: async () => {
    const response = await api.get('/admin/monitoring/resources');
    return response.data;
  },
  getActiveLabs: async () => {
    const response = await api.get('/admin/monitoring/labs/active');
    return response.data;
  },
  getLabCounts: async () => {
    const response = await api.get('/admin/monitoring/labs/count');
    return response.data;
  },
  stopLab: async (sessionId: string) => {
    const response = await api.post(`/admin/monitoring/labs/${sessionId}/stop`);
    return response.data;
  },
};
