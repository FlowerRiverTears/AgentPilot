import { defineStore } from "pinia";

export const useUiStore = defineStore("ui", {
  state: () => ({
    theme: (localStorage.getItem("agentpilot-theme") as "light" | "dark" | null) ?? "light",
    locale: (localStorage.getItem("agentpilot-locale") as "zh" | "en" | null) ?? "zh"
  }),
  actions: {
    toggleTheme() {
      this.theme = this.theme === "light" ? "dark" : "light";
      localStorage.setItem("agentpilot-theme", this.theme);
      document.body.setAttribute("data-theme", this.theme);
    },
    initTheme() {
      document.body.setAttribute("data-theme", this.theme);
    },
    toggleLocale() {
      this.locale = this.locale === "zh" ? "en" : "zh";
      localStorage.setItem("agentpilot-locale", this.locale);
    }
  }
});
