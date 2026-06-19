<template>
  <div class="portal-shell">
    <header class="portal-topbar">
      <div>
        <div class="portal-brand">AgentPilot</div>
        <div class="portal-subtitle">智能体服务台</div>
      </div>
      <div class="topbar-actions">
        <n-button secondary @click="ui.toggleTheme">
          {{ ui.theme === "dark" ? "亮色" : "深色" }}
        </n-button>
        <n-button secondary @click="goAdmin">进入后台</n-button>
      </div>
    </header>

    <main class="portal-page">
      <section class="portal-sidebar">
        <div class="portal-heading">
          <div>
            <p class="portal-kicker">选择服务</p>
            <h1>今天想咨询什么？</h1>
          </div>
          <n-button text size="small" :loading="loadingAgents" @click="refreshAgents">刷新</n-button>
        </div>

        <div v-if="!publishedAgents.length" class="portal-empty-panel">
          <h2>还没有可用智能体</h2>
          <p>请进入后台创建并发布智能体后，再回到前台提供服务。</p>
          <n-button type="primary" @click="goAdmin">去后台创建</n-button>
        </div>

        <div v-else class="agent-list">
          <button
            v-for="agent in publishedAgents"
            :key="agent.id"
            class="agent-choice"
            :class="{ active: agent.id === selectedAgentId }"
            type="button"
            @click="selectAgent(agent.id)"
          >
            <span class="agent-choice-title">{{ agent.name }}</span>
            <span class="agent-choice-desc">{{ agent.description || "可为你处理咨询和任务" }}</span>
          </button>
        </div>
      </section>

      <section class="portal-chat">
        <div class="chat-header">
          <div>
            <p class="portal-kicker">当前服务</p>
            <h2>{{ selectedAgent?.name || "请选择智能体" }}</h2>
            <p>{{ selectedAgent?.description || "选择左侧智能体后即可开始对话。" }}</p>
          </div>
          <n-tag v-if="selectedAgent" type="success" round>在线</n-tag>
        </div>

        <div ref="chatThreadRef" class="chat-thread">
          <div v-if="!messages.length" class="chat-empty">
            <h3>开始对话</h3>
            <p>输入问题后，智能体会根据已配置能力和知识回答。</p>
          </div>

          <article
            v-for="messageItem in messages"
            :key="messageItem.id"
            class="chat-message"
            :class="messageItem.role"
          >
            <div class="chat-bubble">
              <div class="chat-role">
                {{ messageItem.role === "user" ? "我" : messageItem.agentName || selectedAgent?.name || "智能体" }}
              </div>
              <n-collapse v-if="messageItem.thinking" class="thinking-collapse">
                <n-collapse-item title="思考过程" name="thinking">
                  <div class="thinking-content">{{ messageItem.thinking }}</div>
                </n-collapse-item>
              </n-collapse>
              <div class="answer-render">
                <template v-for="(part, index) in messageItem.parts" :key="index">
                  <pre v-if="part.type === 'code'" class="answer-code"><code>{{ part.content }}</code></pre>
                  <div v-else class="chat-content markdown-body" v-html="part.html || part.content" />
                </template>
                <span v-if="messageItem.streaming" class="streaming-cursor">▍</span>
              </div>
              <div v-if="messageItem.citations?.length" class="chat-citations">
                <n-collapse>
                  <n-collapse-item title="引用来源" name="citations">
                    <n-list>
                      <n-list-item v-for="chunk in messageItem.citations" :key="chunk.chunk_id">
                        <n-thing :title="chunk.source" :description="`相似度：${chunk.score.toFixed(3)}`">
                          <div v-if="chunk.content_type === 'image' && chunk.image_url" class="citation-image">
                            <img :src="minioImageUrl(chunk.image_url)" :alt="chunk.content" class="citation-img" />
                            <div class="citation-snippet">{{ snippet(chunk.content) }}</div>
                          </div>
                          <div v-else class="citation-snippet">{{ snippet(chunk.content) }}</div>
                        </n-thing>
                      </n-list-item>
                    </n-list>
                  </n-collapse-item>
                </n-collapse>
              </div>
            </div>
          </article>
        </div>

        <div class="chat-composer">
          <n-input
            v-model:value="input"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 5 }"
            placeholder="输入你想咨询的问题"
            :disabled="!selectedAgent || sending"
            @keydown.enter.exact.prevent="send"
          />
          <n-button type="primary" :loading="sending" :disabled="!selectedAgent" @click="send">
            发送
          </n-button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useMessage } from "naive-ui";
import { useRouter } from "vue-router";

import type { ChatMessage, RetrievedChunk } from "../api/types";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import { splitThinking, type AnswerPart } from "../utils/answerFormat";

interface PortalMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  parts: AnswerPart[];
  agentId?: string;
  agentName?: string;
  thinking?: string;
  citations?: RetrievedChunk[];
  streaming?: boolean;
}

interface PortalConversationState {
  selectedAgentId: string | null;
  conversations: Record<string, AgentConversation>;
  messages?: PortalMessage[];
  chatHistory?: ChatMessage[];
}

interface AgentConversation {
  messages: PortalMessage[];
  chatHistory: ChatMessage[];
}

const STORAGE_KEY = "agentpilot-portal-conversation";
const MAX_STORED_MESSAGES = 40;
const MAX_STORED_CONTENT_LENGTH = 12000;
const MAX_STORED_CITATIONS = 3;
const MAX_STORED_CITATION_LENGTH = 600;

const message = useMessage();
const router = useRouter();
const ui = useUiStore();
const store = useWorkspaceStore();
const selectedAgentId = ref<string | null>(null);
const input = ref("");
const sending = ref(false);
const loadingAgents = ref(false);
const conversations = reactive<Record<string, AgentConversation>>({});
const chatThreadRef = ref<HTMLElement | null>(null);

const publishedAgents = computed(() => store.publishedAgents);

const selectedAgent = computed(
  () => publishedAgents.value.find((agent) => agent.id === selectedAgentId.value) ?? null
);

const activeConversation = computed(() => {
  if (!selectedAgentId.value) return null;
  return ensureConversation(selectedAgentId.value);
});

const messages = computed(() => activeConversation.value?.messages ?? []);

function ensureConversation(agentId: string): AgentConversation {
  conversations[agentId] ??= { messages: [], chatHistory: [] };
  return conversations[agentId];
}

function selectAgent(agentId: string) {
  selectedAgentId.value = agentId;
  ensureConversation(agentId);
  persistConversation();
  scrollToBottom();
}

function goAdmin() {
  router.push("/agents");
}

async function refreshAgents() {
  loadingAgents.value = true;
  try {
    await store.loadPublishedAgents();
    if (!selectedAgent.value) {
      selectedAgentId.value = publishedAgents.value.some((agent) => agent.id === selectedAgentId.value)
        ? selectedAgentId.value
        : publishedAgents.value[0]?.id ?? null;
    }
    if (selectedAgentId.value) {
      ensureConversation(selectedAgentId.value);
    }
  } finally {
    loadingAgents.value = false;
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatThreadRef.value) {
      chatThreadRef.value.scrollTop = chatThreadRef.value.scrollHeight;
    }
  });
}

async function send() {
  const content = input.value.trim();
  if (!selectedAgentId.value) {
    message.warning("请先选择一个智能体");
    return;
  }
  if (!content) {
    message.warning("请输入问题");
    return;
  }

  const agentId = selectedAgentId.value;
  const agentName = selectedAgent.value?.name || "智能体";
  const conversation = ensureConversation(agentId);

  input.value = "";
  conversation.messages.push({
    id: crypto.randomUUID(),
    role: "user",
    content,
    parts: [{ type: "text", content }]
  });
  persistConversation();
  scrollToBottom();

  conversation.chatHistory.push({ role: "user", content });
  persistConversation();

  sending.value = true;
  const assistantMsg: PortalMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "",
    parts: [{ type: "text", content: "" }],
    agentId,
    agentName,
    citations: [],
    streaming: true
  };
  conversation.messages.push(assistantMsg);
  persistConversation();
  scrollToBottom();

  try {
    const response = await fetch("/api/runs/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_id: agentId,
        input: content,
        messages: conversation.chatHistory.slice(0, -1)
      })
    });

    if (!response.ok || !response.body) {
      throw new Error("Stream request failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullAnswer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.startsWith("event: steps")) continue;
        if (line.startsWith("event: citations")) {
          const dataLine = lines[i + 1];
          if (dataLine?.startsWith("data: ")) {
            try {
              assistantMsg.citations = JSON.parse(dataLine.slice(6));
            } catch { /* ignore */ }
          }
          continue;
        }
        if (line.startsWith("event: done")) {
          const dataLine = lines[i + 1];
          if (dataLine?.startsWith("data: ")) {
            try {
              const doneData = JSON.parse(dataLine.slice(6));
              assistantMsg.content = fullAnswer;
              const parsed = splitThinking(fullAnswer);
              assistantMsg.parts = parsed.parts;
              assistantMsg.thinking = parsed.thinking;
              assistantMsg.streaming = false;
              conversation.chatHistory.push({ role: "assistant", content: fullAnswer });
              trimHistory(conversation);
              persistConversation();
            } catch { /* ignore */ }
          }
          continue;
        }
        if (line.startsWith("data: ")) {
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.token) {
              fullAnswer += payload.token;
              assistantMsg.content = fullAnswer;
              const parsed = splitThinking(fullAnswer);
              assistantMsg.parts = parsed.parts;
              assistantMsg.thinking = parsed.thinking;
              persistConversation();
              scrollToBottom();
            }
          } catch { /* ignore */ }
        }
      }
    }

    if (assistantMsg.streaming) {
      assistantMsg.streaming = false;
      assistantMsg.content = fullAnswer;
      const parsed = splitThinking(fullAnswer);
      assistantMsg.parts = parsed.parts;
      assistantMsg.thinking = parsed.thinking;
      if (fullAnswer) {
        conversation.chatHistory.push({ role: "assistant", content: fullAnswer });
        trimHistory(conversation);
        persistConversation();
      }
    }
  } catch (error) {
    assistantMsg.streaming = false;
    assistantMsg.content = "智能体暂时无法回复，请检查后台智能体和模型配置";
    assistantMsg.parts = [{ type: "text", content: assistantMsg.content }];
    persistConversation();
    message.error("智能体暂时无法回复，请检查后台智能体和模型配置");
    console.error(error);
  } finally {
    sending.value = false;
  }
}

function trimHistory(conversation: AgentConversation, limit = 20) {
  if (conversation.chatHistory.length > limit) {
    conversation.chatHistory = conversation.chatHistory.slice(-limit);
  }
}

function persistConversation() {
  const state: PortalConversationState = {
    selectedAgentId: selectedAgentId.value,
    conversations: compactConversations(40, 20)
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    const fallbackState: PortalConversationState = {
      selectedAgentId: state.selectedAgentId,
      conversations: compactConversations(12, 12, false)
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(fallbackState));
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
}

function restoreConversation() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;

  try {
    const state = JSON.parse(raw) as Partial<PortalConversationState>;
    selectedAgentId.value = typeof state.selectedAgentId === "string" ? state.selectedAgentId : null;

    Object.keys(conversations).forEach((agentId) => {
      delete conversations[agentId];
    });

    if (state.conversations && typeof state.conversations === "object") {
      Object.entries(state.conversations).forEach(([agentId, conversation]) => {
        conversations[agentId] = restoreAgentConversation(conversation);
      });
    } else if (Array.isArray(state.messages) || Array.isArray(state.chatHistory)) {
      const legacyAgentId = selectedAgentId.value || "legacy";
      conversations[legacyAgentId] = restoreAgentConversation({
        messages: state.messages ?? [],
        chatHistory: state.chatHistory ?? []
      });
      selectedAgentId.value = selectedAgentId.value || legacyAgentId;
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function compactConversations(messageLimit: number, historyLimit: number, keepCitations = true) {
  return Object.fromEntries(
    Object.entries(conversations).map(([agentId, conversation]) => [
      agentId,
      {
        messages: conversation.messages.slice(-messageLimit).map((item) => compactMessage(item, keepCitations)),
        chatHistory: conversation.chatHistory.slice(-historyLimit)
      }
    ])
  );
}

function compactMessage(item: PortalMessage, keepCitations = true): PortalMessage {
  const content = trimStoredText(item.content || "", MAX_STORED_CONTENT_LENGTH);
  return {
    id: item.id,
    role: item.role,
    content,
    parts: [{ type: "text", content }],
    agentId: item.agentId,
    agentName: item.agentName,
    thinking: trimStoredText(item.thinking || "", 2000),
    citations: keepCitations
      ? item.citations?.slice(0, MAX_STORED_CITATIONS).map((chunk) => ({
          ...chunk,
          content: trimStoredText(chunk.content, MAX_STORED_CITATION_LENGTH)
        }))
      : [],
    streaming: false
  };
}

function restoreAgentConversation(conversation: Partial<AgentConversation>): AgentConversation {
  return {
    messages: Array.isArray(conversation.messages)
      ? conversation.messages
          .filter((item) => item.role === "user" || item.role === "assistant")
          .map((item) => ({
            ...item,
            streaming: false,
            content: trimStoredText(item.content || "", MAX_STORED_CONTENT_LENGTH),
            parts: splitThinking(item.content || "").parts,
            citations: Array.isArray(item.citations) ? item.citations : []
          }))
      : [],
    chatHistory: Array.isArray(conversation.chatHistory)
      ? conversation.chatHistory.filter(
          (item) =>
            (item.role === "user" || item.role === "assistant") &&
            typeof item.content === "string" &&
            item.content.trim()
        )
      : []
  };
}

function trimStoredText(text: string, limit: number) {
  if (text.length <= limit) return text;
  return `${text.slice(0, limit)}...`;
}

function snippet(text: string, limit = 160) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit)}...`;
}

function minioImageUrl(path: string) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base = window.location.port === "5173" ? "http://localhost:19000" : "http://localhost:9000";
  return `${base}${path}`;
}

watch([conversations, selectedAgentId], persistConversation, { deep: true, flush: "post" });

onMounted(async () => {
  restoreConversation();
  window.addEventListener("beforeunload", persistConversation);
  await refreshAgents();
  scrollToBottom();
});

onBeforeUnmount(() => {
  persistConversation();
  window.removeEventListener("beforeunload", persistConversation);
});
</script>
