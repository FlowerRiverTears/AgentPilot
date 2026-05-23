export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model?: string | null;
  model_config_id?: string | null;
  knowledge_base_ids: string[];
  tool_ids: string[];
  status: string;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  document_count: number;
}

export interface RetrievedChunk {
  chunk_id: string;
  content: string;
  score: number;
  source: string;
}

export interface SampleDocument {
  id: string;
  title: string;
  filename: string;
}

export interface ToolDefinition {
  id: string;
  name: string;
  description: string;
}

export interface RunResult {
  run_id: string;
  agent_id: string;
  status: string;
  model: string;
  answer: string;
  citations: RetrievedChunk[];
  steps: Array<{ name: string; status: string; detail: string }>;
}

export interface ModelConfig {
  id: string;
  name: string;
  base_url: string;
  api_key_set: boolean;
  default_model: string;
  is_default: boolean;
}

export interface ModelConfigTestResult {
  ok: boolean;
  message: string;
}
