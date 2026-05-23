import { defineStore } from "pinia";

export const useUiStore = defineStore("ui", {
  state: () => ({
    theme: (localStorage.getItem("agentpilot-theme") as "light" | "dark" | null) ?? "light"
  }),
  actions: {
    toggleTheme() {
      this.theme = this.theme === "light" ? "dark" : "light";
      localStorage.setItem("agentpilot-theme", this.theme);
      document.body.setAttribute("data-theme", this.theme);
    },
    initTheme() {
      document.body.setAttribute("data-theme", this.theme);
    }
  }
});
