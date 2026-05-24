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
                          <div class="citation-snippet">{{ snippet(chunk.content) }}</div>
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
import { computed, nextTick, onMounted, ref, watch } from "vue";
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
  messages: PortalMessage[];
  chatHistory: ChatMessage[];
}

const STORAGE_KEY = "agentpilot-portal-conversation";
const MAX_STORED_MESSAGES = 60;

const message = useMessage();
const router = useRouter();
const ui = useUiStore();
const store = useWorkspaceStore();
const selectedAgentId = ref<string | null>(null);
const input = ref("");
const sending = ref(false);
const loadingAgents = ref(false);
const messages = ref<PortalMessage[]>([]);
const chatHistory = ref<ChatMessage[]>([]);
const chatThreadRef = ref<HTMLElement | null>(null);

const publishedAgents = computed(() => store.publishedAgents);

const selectedAgent = computed(
  () => publishedAgents.value.find((agent) => agent.id === selectedAgentId.value) ?? null
);

function selectAgent(agentId: string) {
  selectedAgentId.value = agentId;
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

  input.value = "";
  messages.value.push({
    id: crypto.randomUUID(),
    role: "user",
    content,
    parts: [{ type: "text", content }]
  });
  persistConversation();
  scrollToBottom();

  chatHistory.value.push({ role: "user", content });
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
  messages.value.push(assistantMsg);
  persistConversation();
  scrollToBottom();

  try {
    const response = await fetch("/api/runs/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_id: agentId,
        input: content,
        messages: chatHistory.value.slice(0, -1)
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
              chatHistory.value.push({ role: "assistant", content: fullAnswer });
              trimHistory();
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
        chatHistory.value.push({ role: "assistant", content: fullAnswer });
        trimHistory();
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

function trimHistory(limit = 20) {
  if (chatHistory.value.length > limit) {
    chatHistory.value = chatHistory.value.slice(-limit);
  }
}

function persistConversation() {
  const state: PortalConversationState = {
    selectedAgentId: selectedAgentId.value,
    messages: messages.value.slice(-MAX_STORED_MESSAGES).map((item) => ({
      ...item,
      streaming: false
    })),
    chatHistory: chatHistory.value.slice(-20)
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function restoreConversation() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;

  try {
    const state = JSON.parse(raw) as Partial<PortalConversationState>;
    selectedAgentId.value = typeof state.selectedAgentId === "string" ? state.selectedAgentId : null;
    messages.value = Array.isArray(state.messages)
      ? state.messages
          .filter((item) => item.role === "user" || item.role === "assistant")
          .map((item) => ({
            ...item,
            streaming: false,
            parts: item.parts?.length ? item.parts : splitThinking(item.content || "").parts
          }))
      : [];
    chatHistory.value = Array.isArray(state.chatHistory)
      ? state.chatHistory.filter(
          (item) =>
            (item.role === "user" || item.role === "assistant") &&
            typeof item.content === "string" &&
            item.content.trim()
        )
      : [];
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function snippet(text: string, limit = 160) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit)}...`;
}

watch([messages, chatHistory, selectedAgentId], persistConversation, { deep: true });

onMounted(async () => {
  restoreConversation();
  await refreshAgents();
  scrollToBottom();
});
</script>
