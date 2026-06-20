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

        <!-- 会话历史区域 -->
        <div v-if="selectedAgentId" class="conversation-history">
          <div class="history-header">
            <p class="portal-kicker">会话历史</p>
            <n-button size="tiny" type="primary" secondary @click="startNewConversation">
              新建会话
            </n-button>
          </div>
          <n-input
            v-model:value="searchKeyword"
            size="small"
            placeholder="搜索会话标题"
            clearable
            :loading="loadingHistory"
            @update:value="handleSearch"
            @keydown.enter="handleSearch"
          />
          <div class="history-list">
            <div v-if="loadingHistory && !conversationHistory.length" class="history-empty">
              加载中...
            </div>
            <div v-else-if="!conversationHistory.length" class="history-empty">
              暂无历史会话
            </div>
            <div
              v-for="item in conversationHistory"
              :key="item.id"
              class="history-item"
              :class="{ active: activeConversation?.conversationId === item.id }"
              @click="restoreConversationFromHistory(item)"
            >
              <div class="history-item-main">
                <div class="history-item-title">{{ item.title || "未命名会话" }}</div>
                <div class="history-item-meta">
                  <span>{{ item.message_count }} 条消息</span>
                  <span>{{ formatHistoryTime(item.updated_at) }}</span>
                </div>
              </div>
              <n-button
                size="tiny"
                quaternary
                type="error"
                @click="deleteHistoryConversation(item, $event)"
              >
                删除
              </n-button>
            </div>
          </div>
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
                <MermaidBlock v-if="part.type === 'mermaid'" :source="part.content" />
                <pre v-else-if="part.type === 'code'" class="answer-code"><code>{{ part.content }}</code></pre>
                <div v-else class="chat-content markdown-body" v-html="part.html || part.content" />
              </template>
              <span v-if="messageItem.streaming" class="streaming-cursor">▍</span>
            </div>
            <n-alert
              v-if="messageItem.error"
              type="error"
              :show-icon="true"
              class="chat-error"
            >
              {{ messageItem.error }}
            </n-alert>
            <n-alert
              v-if="messageItem.compressed && !messageItem.streaming"
              type="info"
              :show-icon="false"
              class="chat-compressed-tip"
            >
              上下文已压缩
            </n-alert>
            <div v-if="messageItem.role === 'assistant' && !messageItem.streaming && (messageItem.content || messageItem.error)" class="chat-actions">
              <n-button size="tiny" secondary :disabled="sending" @click="retry(messageItem)">
                重新回答
              </n-button>
              <n-button
                v-if="messageItem.runId"
                size="tiny"
                :type="messageItem.feedback === 'like' ? 'primary' : 'default'"
                :secondary="messageItem.feedback !== 'like'"
                @click="submitFeedback(messageItem, 'like')"
              >
                {{ messageItem.feedback === 'like' ? '已赞' : '赞' }}
              </n-button>
              <n-button
                v-if="messageItem.runId"
                size="tiny"
                :type="messageItem.feedback === 'dislike' ? 'error' : 'default'"
                :secondary="messageItem.feedback !== 'dislike'"
                @click="submitFeedback(messageItem, 'dislike')"
              >
                {{ messageItem.feedback === 'dislike' ? '已踩' : '踩' }}
              </n-button>
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
import { api } from "../api/client";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import { splitThinking, type AnswerPart } from "../utils/answerFormat";
import MermaidBlock from "../components/MermaidBlock.vue";

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
  error?: string;
  userInput?: string;
  runId?: string; // 关联的后端 run_id，用于反馈
  compressed?: boolean; // 是否触发了上下文压缩
  feedback?: "like" | "dislike" | null; // 用户反馈
}

interface PortalConversationState {
  selectedAgentId: string | null;
  conversations: Record<string, AgentConversation>;
  messages?: PortalMessage[];
  chatHistory?: ChatMessage[];
}

interface AgentConversation {
  sessionId: string; // 当前会话的 session_id（前端生成）
  conversationId?: string; // 后端返回的会话 ID（用于删除等）
  messages: PortalMessage[];
  chatHistory: ChatMessage[];
}

interface ConversationHistoryItem {
  id: string;
  agent_id: string;
  session_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
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
const conversationHistory = ref<ConversationHistoryItem[]>([]);
const searchKeyword = ref("");
const loadingHistory = ref(false);

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
  conversations[agentId] ??= {
    sessionId: crypto.randomUUID(),
    messages: [],
    chatHistory: []
  };
  return conversations[agentId];
}

function selectAgent(agentId: string) {
  selectedAgentId.value = agentId;
  ensureConversation(agentId);
  searchKeyword.value = "";
  void loadConversationHistory(agentId);
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
      void loadConversationHistory(selectedAgentId.value);
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

// ===== 会话历史管理 =====

async function loadConversationHistory(agentId: string) {
  loadingHistory.value = true;
  try {
    const response = await api.get<ConversationHistoryItem[]>("/conversations", {
      params: { agent_id: agentId }
    });
    conversationHistory.value = response.data;
  } catch (error) {
    console.error("加载会话历史失败", error);
    conversationHistory.value = [];
  } finally {
    loadingHistory.value = false;
  }
}

async function handleSearch() {
  const keyword = searchKeyword.value.trim();
  if (!keyword) {
    if (selectedAgentId.value) {
      await loadConversationHistory(selectedAgentId.value);
    }
    return;
  }
  loadingHistory.value = true;
  try {
    const response = await api.get<ConversationHistoryItem[]>("/conversations/search", {
      params: { q: keyword }
    });
    conversationHistory.value = response.data;
  } catch (error) {
    console.error("搜索会话失败", error);
  } finally {
    loadingHistory.value = false;
  }
}

function startNewConversation() {
  if (!selectedAgentId.value) return;
  const agentId = selectedAgentId.value;
  const conv = ensureConversation(agentId);
  conv.sessionId = crypto.randomUUID();
  conv.conversationId = undefined;
  conv.messages = [];
  conv.chatHistory = [];
  persistConversation();
  message.success("已开始新会话");
}

async function restoreConversationFromHistory(item: ConversationHistoryItem) {
  if (!selectedAgentId.value) return;
  try {
    const response = await api.get<{
      id: string;
      session_id: string;
      messages: Array<{ role: string; content: string }>;
    }>(`/conversations/${item.id}`);
    const data = response.data;
    const agentId = selectedAgentId.value;
    const conv = ensureConversation(agentId);
    conv.sessionId = data.session_id || item.session_id;
    conv.conversationId = data.id;
    const restoredMessages = Array.isArray(data.messages) ? data.messages : [];
    conv.messages = restoredMessages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => {
        const parsed = splitThinking(m.content || "");
        return {
          id: crypto.randomUUID(),
          role: m.role as "user" | "assistant",
          content: m.content || "",
          parts: parsed.parts,
          thinking: parsed.thinking,
          agentId,
          agentName: selectedAgent.value?.name,
          feedback: null
        } as PortalMessage;
      });
    conv.chatHistory = restoredMessages
      .filter((m) => (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && m.content.trim())
      .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));
    persistConversation();
    scrollToBottom();
  } catch (error) {
    console.error("恢复会话失败", error);
    message.error("恢复会话失败");
  }
}

async function deleteHistoryConversation(item: ConversationHistoryItem, event: Event) {
  event.stopPropagation();
  try {
    await api.delete(`/conversations/${item.id}`);
    conversationHistory.value = conversationHistory.value.filter((c) => c.id !== item.id);
    message.success("已删除会话");
  } catch (error) {
    console.error("删除会话失败", error);
    message.error("删除会话失败");
  }
}

async function saveCurrentConversation(agentId: string) {
  const conv = conversations[agentId];
  if (!conv || !conv.chatHistory.length) return;

  const firstUserMsg = conv.messages.find((m) => m.role === "user");
  const title = (firstUserMsg?.content || "新会话").slice(0, 50);
  const messagesPayload = conv.chatHistory.map((m) => ({ role: m.role, content: m.content }));

  try {
    const response = await api.post("/conversations", {
      agent_id: agentId,
      session_id: conv.sessionId,
      title,
      messages: messagesPayload
    });
    conv.conversationId = response.data.id;
    await loadConversationHistory(agentId);
  } catch (error) {
    console.error("保存会话失败", error);
  }
}

// ===== 反馈 =====

async function submitFeedback(msg: PortalMessage, rating: "like" | "dislike") {
  if (!msg.runId) {
    message.warning("该消息暂无关联运行记录，无法反馈");
    return;
  }
  // 再次点击相同反馈则取消（仅前端状态，不调用后端删除接口）
  if (msg.feedback === rating) {
    msg.feedback = null;
    return;
  }
  const previous = msg.feedback;
  msg.feedback = rating;
  try {
    await api.post("/feedback", {
      run_id: msg.runId,
      agent_id: msg.agentId,
      rating
    });
  } catch (error) {
    console.error("提交反馈失败", error);
    msg.feedback = previous; // 回滚
    message.error("提交反馈失败");
  }
}

function formatHistoryTime(iso: string): string {
  if (!iso) return "";
  try {
    const date = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "刚刚";
    if (minutes < 60) return `${minutes} 分钟前`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} 小时前`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days} 天前`;
    return date.toLocaleDateString();
  } catch {
    return iso;
  }
}

async function streamRequest(
  agentId: string,
  content: string,
  conversation: AgentConversation,
  assistantMsg: PortalMessage
) {
  sending.value = true;
  assistantMsg.streaming = true;
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
      throw new Error(`请求失败（HTTP ${response.status}）`);
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
        if (line.startsWith("event: error")) {
          const dataLine = lines[i + 1];
          if (dataLine?.startsWith("data: ")) {
            try {
              const errData = JSON.parse(dataLine.slice(6));
              assistantMsg.error = errData.message || "模型生成失败";
            } catch {
              assistantMsg.error = "模型生成失败";
            }
          }
          continue;
        }
        if (line.startsWith("event: done")) {
          const dataLine = lines[i + 1];
          if (dataLine?.startsWith("data: ")) {
            try {
              const doneData = JSON.parse(dataLine.slice(6));
              // 捕获 run_id 用于反馈，捕获 compressed 标记用于压缩提示
              if (doneData.run_id) {
                assistantMsg.runId = doneData.run_id;
              }
              if (doneData.compressed) {
                assistantMsg.compressed = true;
              }
              assistantMsg.content = fullAnswer;
              const parsed = splitThinking(fullAnswer);
              assistantMsg.parts = parsed.parts;
              assistantMsg.thinking = parsed.thinking;
              assistantMsg.streaming = false;
              if (fullAnswer && !assistantMsg.error) {
                conversation.chatHistory.push({ role: "assistant", content: fullAnswer });
                trimHistory(conversation);
              }
              persistConversation();
              // 保存会话到后端
              void saveCurrentConversation(agentId);
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
      if (fullAnswer && !assistantMsg.error) {
        conversation.chatHistory.push({ role: "assistant", content: fullAnswer });
        trimHistory(conversation);
        persistConversation();
        // 保存会话到后端
        void saveCurrentConversation(agentId);
      }
    }
  } catch (error) {
    assistantMsg.streaming = false;
    const err = error as Error;
    if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
      assistantMsg.error = "网络连接失败，请检查网络或后端服务是否正常运行";
    } else if (err.message.includes("timeout") || err.message.includes("Timeout")) {
      assistantMsg.error = "请求超时，模型响应时间过长";
    } else {
      assistantMsg.error = err.message || "智能体暂时无法回复";
    }
    persistConversation();
    console.error(error);
  } finally {
    sending.value = false;
  }
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

  const assistantMsg: PortalMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "",
    parts: [{ type: "text", content: "" }],
    agentId,
    agentName,
    citations: [],
    streaming: true,
    userInput: content
  };
  conversation.messages.push(assistantMsg);
  persistConversation();
  scrollToBottom();

  await streamRequest(agentId, content, conversation, assistantMsg);
}

async function retry(msg: PortalMessage) {
  if (!msg.userInput || !msg.agentId || sending.value) return;
  const agentId = msg.agentId;
  const content = msg.userInput;
  const conversation = ensureConversation(agentId);

  const msgIndex = conversation.messages.findIndex((m) => m.id === msg.id);
  if (msgIndex === -1) return;

  conversation.messages.splice(msgIndex, 1);

  const lastAssistantIdx = conversation.chatHistory.length - 1;
  if (lastAssistantIdx >= 0 && conversation.chatHistory[lastAssistantIdx].role === "assistant") {
    conversation.chatHistory.splice(lastAssistantIdx, 1);
  }

  const assistantMsg: PortalMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "",
    parts: [{ type: "text", content: "" }],
    agentId,
    agentName: msg.agentName,
    citations: [],
    streaming: true,
    userInput: content
  };
  conversation.messages.push(assistantMsg);
  persistConversation();
  scrollToBottom();

  await streamRequest(agentId, content, conversation, assistantMsg);
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
        sessionId: conversation.sessionId,
        conversationId: conversation.conversationId,
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
    streaming: false,
    runId: item.runId,
    compressed: item.compressed,
    feedback: item.feedback ?? null
  };
}

function restoreAgentConversation(conversation: Partial<AgentConversation>): AgentConversation {
  return {
    sessionId: typeof conversation.sessionId === "string" && conversation.sessionId
      ? conversation.sessionId
      : crypto.randomUUID(),
    conversationId: conversation.conversationId,
    messages: Array.isArray(conversation.messages)
      ? conversation.messages
          .filter((item) => item.role === "user" || item.role === "assistant")
          .map((item) => ({
            ...item,
            streaming: false,
            content: trimStoredText(item.content || "", MAX_STORED_CONTENT_LENGTH),
            parts: splitThinking(item.content || "").parts,
            citations: Array.isArray(item.citations) ? item.citations : [],
            feedback: item.feedback ?? null
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

<style scoped>
/* 会话历史区域 */
.conversation-history {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 280px;
  overflow-y: auto;
}

.history-empty {
  padding: 16px 8px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.history-item:hover,
.history-item.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.history-item-main {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-item-meta {
  display: flex;
  gap: 10px;
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-muted);
}

/* 压缩提示 */
.chat-compressed-tip {
  margin-top: 8px;
  padding: 2px 8px;
  font-size: 12px;
}

.chat-actions {
  gap: 6px;
}
</style>
