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
  getTasks: async () => {
    const response = await apiClient.get('/tasks');
    return response.data;
  },
  updatePacing: async (taskId, date) => {
    const response = await apiClient.patch(`/tasks/${taskId}/pacing`, { target_date: date });
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
    const response = await apiClient.post(`/tasks/${subBlockId}/complete`);
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
  }
};

export default api;
