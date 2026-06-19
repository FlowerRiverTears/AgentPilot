import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  timeout: 180000
});

const TOKEN_KEY = "agentpilot_token";

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      const currentPath = window.location.pathname;
      if (currentPath !== "/login" && currentPath !== "/portal") {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
      }
    }
    return Promise.reject(error);
  }
);
