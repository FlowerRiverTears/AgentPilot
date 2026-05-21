export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model?: string | null;
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

export interface RunResult {
  run_id: string;
  agent_id: string;
  status: string;
  model: string;
  answer: string;
  citations: RetrievedChunk[];
  steps: Array<{ name: string; status: string; detail: string }>;
}
