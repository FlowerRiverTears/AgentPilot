import { defineStore } from "pinia";

import { api } from "../api/client";
import type { Agent, KnowledgeBase, RetrievedChunk, RunResult } from "../api/types";

export const useWorkspaceStore = defineStore("workspace", {
  state: () => ({
    agents: [] as Agent[],
    knowledgeBases: [] as KnowledgeBase[],
    lastRun: null as RunResult | null
  }),
  actions: {
    async loadAgents() {
      const response = await api.get<Agent[]>("/agents");
      this.agents = response.data;
    },
    async createAgent(payload: {
      name: string;
      description: string;
      system_prompt: string;
      model?: string;
      knowledge_base_ids: string[];
      tool_ids?: string[];
    }) {
      const response = await api.post<Agent>("/agents", payload);
      this.agents.unshift(response.data);
      return response.data;
    },
    async loadKnowledgeBases() {
      const response = await api.get<KnowledgeBase[]>("/knowledge-bases");
      this.knowledgeBases = response.data;
    },
    async createKnowledgeBase(payload: { name: string; description: string }) {
      const response = await api.post<KnowledgeBase>("/knowledge-bases", payload);
      this.knowledgeBases.unshift(response.data);
      return response.data;
    },
    async deleteKnowledgeBase(kbId: string) {
      await api.delete(`/knowledge-bases/${kbId}`);
      this.knowledgeBases = this.knowledgeBases.filter((item) => item.id !== kbId);
    },
    async uploadKnowledgeDocument(kbId: string, file: File) {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.post<RetrievedChunk[]>(
        `/knowledge-bases/${kbId}/documents`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" }
        }
      );
      await this.loadKnowledgeBases();
      return response.data;
    },
    async retrieveKnowledge(kbId: string, query: string, topK = 5) {
      const response = await api.post<RetrievedChunk[]>(`/knowledge-bases/${kbId}/retrieve-test`, {
        query,
        top_k: topK
      });
      return response.data;
    },
    async runAgent(agentId: string, input: string) {
      const response = await api.post<RunResult>("/runs", {
        agent_id: agentId,
        input
      });
      this.lastRun = response.data;
      return response.data;
    },
    async reloadForRunPage() {
      await this.loadAgents();
    }
  }
});
