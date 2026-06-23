import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Tasks
  ingestTask: async (sourceText, sourceType = 'manual') => {
    const response = await apiClient.post('/tasks/ingest', {
      source_text: sourceText,
      source_type: sourceType,
    });
    return response.data;
  },
  createTask: async ({ title, deadline, estimatedHours = 2.0, interestTag = null, sourceType = 'manual' }) => {
    const response = await apiClient.post('/tasks/create', {
      title,
      deadline,
      estimated_hours: estimatedHours,
      interest_tag: interestTag,
      source_type: sourceType,
    });
    return response.data;
  },
  getTasks: async () => {
    const response = await apiClient.get('/tasks');
    return response.data;
  },
  updatePacing: async (taskId, date) => {
    const response = await apiClient.patch(`/tasks/${taskId}`, { deadline: date });
    return response.data;
  },
  completeTask: async (taskId) => {
    const response = await apiClient.post(`/tasks/${taskId}/complete`);
    return response.data;
  },
  deleteTask: async (taskId) => {
    const response = await apiClient.delete(`/tasks/${taskId}`);
    return response.data;
  },
  updateTask: async (taskId, data) => {
    const response = await apiClient.patch(`/tasks/${taskId}`, data);
    return response.data;
  },

  // Bubble interactions
  getNextBubbleTask: async () => {
    const response = await apiClient.get('/bubble/next');
    return response.data;
  },
  completeSubBlock: async (subBlockId) => {
    const response = await apiClient.post(`/sub-blocks/${subBlockId}/complete`);
    return response.data;
  },
  getAISummary: async () => {
    const response = await apiClient.get('/bubble/summary');
    return response.data;
  },

  // State / Morning routine
  submitMood: async (moodScore) => {
    const response = await apiClient.post('/state/log', { mood_score: moodScore });
    return response.data;
  },

  // User settings
  getUserSettings: async () => {
    const response = await apiClient.get('/user/settings');
    return response.data;
  },
  updateUserSettings: async (settings) => {
    const response = await apiClient.patch('/user/settings', settings);
    return response.data;
  },

  // Integrations
  getIntegrationsStatus: async () => {
    const response = await apiClient.get('/integrations/status');
    return response.data;
  },
  getIntegrationStatus: async (provider) => {
    const response = await apiClient.get(`/integrations/status/${provider}`);
    return response.data;
  },
  configureIntegration: async ({ provider, accessToken, refreshToken, expiresInSeconds = 3600, settings = {} }) => {
    const response = await apiClient.post('/integrations/config', {
      provider,
      access_token: accessToken,
      refresh_token: refreshToken || null,
      expires_in_seconds: expiresInSeconds,
      settings,
    });
    return response.data;
  },

  // Assistant Chat
  sendChatMessage: async (messages) => {
    const response = await apiClient.post('/chat', { messages });
    return response.data;
  },

  // Rewards / Shop
  getUnlockedRewards: async () => {
    const response = await apiClient.get('/rewards/unlocked');
    return response.data;
  },
  getVaultDrops: async () => {
    const response = await apiClient.get('/rewards/vault');
    return response.data;
  },
  purchaseReward: async (type, itemId, metadata = {}) => {
    const response = await apiClient.post('/rewards/purchase', {
      type,
      item_id: itemId,
      metadata,
    });
    return response.data;
  },

  // Generic HTTP helpers (used by sync settings, etc.)
  get: async (url) => {
    const response = await apiClient.get(url);
    return response.data;
  },
  post: async (url, data) => {
    const response = await apiClient.post(url, data);
    return response.data;
  },
  put: async (url, data) => {
    const response = await apiClient.put(url, data);
    return response.data;
  },
  delete: async (url) => {
    const response = await apiClient.delete(url);
    return response.data;
  },
};

export default api;
