import { defineStore } from "pinia";
import { api } from "../api/client";

export interface UserInfo {
  username: string;
  role: string;
}

const TOKEN_KEY = "agentpilot_token";
const USER_KEY = "agentpilot_user";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
    user: JSON.parse(localStorage.getItem(USER_KEY) || "null") as UserInfo | null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    async login(username: string, password: string) {
      const response = await api.post<{ access_token: string; username: string; role: string }>("/auth/login", {
        username,
        password,
      });
      this.token = response.data.access_token;
      this.user = { username: response.data.username, role: response.data.role };
      localStorage.setItem(TOKEN_KEY, this.token);
      localStorage.setItem(USER_KEY, JSON.stringify(this.user));
    },
    async fetchMe() {
      try {
        const response = await api.get<UserInfo>("/auth/me");
        this.user = response.data;
        localStorage.setItem(USER_KEY, JSON.stringify(this.user));
      } catch {
        this.logout();
      }
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    },
  },
});
