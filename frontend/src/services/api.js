import axios from 'axios';
import { getToken } from './auth';

// Create an axios instance with base URL pointing to backend API
const api = axios.create({
  baseURL: '/api', // Vite proxy forwards /api to backend
});

// Add a request interceptor to attach the session token if present
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
    config.headers['X-Session-Token'] = token;
  }
  return config;
});

// Add response interceptor for consistent error extraction
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // If backend returns a structured message, attach it
    if (error.response?.data?.message) {
      error.customMessage = error.response.data.message;
    }
    return Promise.reject(error);
  }
);

export default api;
