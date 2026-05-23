import { defineStore } from "pinia";

import { api } from "../api/client";
import type {
  Agent,
  KnowledgeBase,
  ModelConfig,
  ModelConfigTestResult,
  RetrievedChunk,
  RunResult,
  SampleDocument,
  ToolDefinition
} from "../api/types";

export const useWorkspaceStore = defineStore("workspace", {
  state: () => ({
    agents: [] as Agent[],
    knowledgeBases: [] as KnowledgeBase[],
    sampleDocuments: [] as SampleDocument[],
    tools: [] as ToolDefinition[],
    modelConfigs: [] as ModelConfig[],
    modelConfig: null as ModelConfig | null,
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
      model_config_id?: string | null;
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
    async loadSampleDocuments() {
      const response = await api.get<SampleDocument[]>("/knowledge-bases/sample-documents");
      this.sampleDocuments = response.data;
    },
    async loadTools() {
      const response = await api.get<ToolDefinition[]>("/tools");
      this.tools = response.data;
      return response.data;
    },
    async importSampleDocument(kbId: string, documentId: string) {
      const response = await api.post<RetrievedChunk[]>(
        `/knowledge-bases/${kbId}/sample-documents/${documentId}`
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
    },
    async loadModelConfig() {
      const response = await api.get<ModelConfig>("/settings/model");
      this.modelConfig = response.data;
      return response.data;
    },
    async loadModelConfigs() {
      const response = await api.get<ModelConfig[]>("/settings/models");
      this.modelConfigs = response.data;
      this.modelConfig = response.data.find((item) => item.is_default) ?? response.data[0] ?? null;
      return response.data;
    },
    async createModelConfig(payload: {
      name: string;
      base_url: string;
      api_key: string;
      default_model: string;
      is_default: boolean;
    }) {
      const response = await api.post<ModelConfig>("/settings/models", payload);
      await this.loadModelConfigs();
      return response.data;
    },
    async updateNamedModelConfig(
      configId: string,
      payload: {
        name: string;
        base_url: string;
        api_key: string;
        default_model: string;
        is_default: boolean;
      }
    ) {
      const response = await api.put<ModelConfig>(`/settings/models/${configId}`, payload);
      await this.loadModelConfigs();
      return response.data;
    },
    async setDefaultModelConfig(configId: string) {
      const response = await api.post<ModelConfig>(`/settings/models/${configId}/default`);
      await this.loadModelConfigs();
      return response.data;
    },
    async testModelConfig(configId: string) {
      const response = await api.post<ModelConfigTestResult>(`/settings/models/${configId}/test`);
      return response.data;
    },
    async deleteModelConfig(configId: string) {
      await api.delete(`/settings/models/${configId}`);
      await this.loadModelConfigs();
    },
    async updateModelConfig(payload: {
      name?: string;
      base_url: string;
      api_key: string;
      default_model: string;
    }) {
      const response = await api.put<ModelConfig>("/settings/model", {
        name: payload.name ?? "default",
        ...payload,
        is_default: true
      });
      this.modelConfig = response.data;
      return response.data;
    }
  }
});
