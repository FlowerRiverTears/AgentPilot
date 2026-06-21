export interface ToolChainStep {
  tool_id: string;
  input_mapping: { query: string };
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model?: string | null;
  model_config_id?: string | null;
  knowledge_base_ids: string[];
  tool_ids: string[];
  sub_agent_ids?: string[];
  tool_chain?: ToolChainStep[];
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
  content_type: string;
  image_url: string;
  document_id: string;
  source_uri: string;
  section_path: string;
  page_number: number | null;
  token_count: number;
  metadata: Record<string, unknown>;
  vector_score: number;
  lexical_score: number;
}

export interface SampleDocument {
  id: string;
  title: string;
  filename: string;
}

export interface ToolDefinition {
  id: string;
  name: string;
  type: string;
  description: string;
  config: HttpToolConfig;
  enabled: boolean;
}

export interface HttpToolConfig {
  url: string;
  method: "GET" | "POST";
  trigger_keywords: string[];
  headers: Record<string, string>;
  query: Record<string, unknown>;
  body: Record<string, unknown>;
  timeout_seconds: number;
}

export interface ToolPayload {
  name: string;
  type: "http";
  description: string;
  config: HttpToolConfig;
  enabled: boolean;
}

export interface ToolTestResult {
  ok: boolean;
  status_code?: number | null;
  elapsed_ms: number;
  output?: unknown;
  error: string;
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

export interface RunSummary {
  run_id: string;
  agent_id: string;
  agent_name: string;
  status: string;
  input: string;
  model: string;
  duration_ms: number | null;
  trace_id: string | null;
  created_at: string;
}

export interface ToolCallResult {
  tool_id: string;
  name: string;
  content: string;
}

export interface RunDetail extends RunSummary {
  answer: string;
  citations: Array<{
    chunk_id: string;
    content: string;
    score: number;
    source: string;
    content_type: string;
    image_url: string;
    document_id: string;
    source_uri: string;
    section_path: string;
    page_number: number | null;
    token_count: number;
    metadata: Record<string, unknown>;
    vector_score: number;
    lexical_score: number;
  }>;
  steps: Array<{ name: string; status: string; detail: string }>;
  usage: Record<string, unknown>;
  tool_results: ToolCallResult[];
  error?: string;
}

export interface DocumentInfo {
  id: string;
  knowledge_base_id: string;
  filename: string;
  status: string;
  created_at: string;
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

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}
