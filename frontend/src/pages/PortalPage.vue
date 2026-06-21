<template>
  <div class="portal-shell">
    <header class="portal-topbar">
      <div>
        <div class="portal-brand">AgentPilot</div>
        <div class="portal-subtitle">{{ t('portal.brand') }}</div>
      </div>
      <div class="topbar-actions">
        <n-button secondary @click="toggleLocale">{{ ui.locale === 'zh' ? 'EN' : '中' }}</n-button>
        <n-button secondary @click="ui.toggleTheme">
          {{ ui.theme === "dark" ? t('common.light') : t('common.dark') }}
        </n-button>
        <n-button secondary @click="goAdmin">{{ t('common.goBackend') }}</n-button>
      </div>
    </header>

    <main class="portal-page">
      <section class="portal-sidebar">
        <div class="portal-heading">
          <div>
            <p class="portal-kicker">{{ t('portal.selectService') }}</p>
            <h1>{{ t('portal.whatToAsk') }}</h1>
          </div>
          <n-button text size="small" :loading="loadingAgents" @click="refreshAgents">{{ t('common.refresh') }}</n-button>
        </div>

        <div v-if="!publishedAgents.length" class="portal-empty-panel">
          <h2>{{ t('portal.noAgents') }}</h2>
          <p>{{ t('portal.noAgentsHint') }}</p>
          <n-button type="primary" @click="goAdmin">{{ t('portal.createInBackend') }}</n-button>
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
            <span class="agent-choice-desc">{{ agent.description || t('portal.agentDefaultDesc') }}</span>
          </button>
        </div>

        <!-- 会话历史区域 -->
        <div v-if="selectedAgentId" class="conversation-history">
          <div class="history-header">
            <p class="portal-kicker">{{ t('portal.history') }}</p>
            <n-button size="tiny" type="primary" secondary @click="startNewConversation">
              {{ t('portal.newConversation') }}
            </n-button>
          </div>
          <n-input
            v-model:value="searchKeyword"
            size="small"
            :placeholder="t('portal.searchPlaceholder')"
            clearable
            :loading="loadingHistory"
            @update:value="handleSearch"
            @keydown.enter="handleSearch"
          />
          <div class="history-list">
            <div v-if="loadingHistory && !conversationHistory.length" class="history-empty">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="!conversationHistory.length" class="history-empty">
              {{ t('portal.noHistory') }}
            </div>
            <div
              v-for="item in conversationHistory"
              :key="item.id"
              class="history-item"
              :class="{ active: activeConversation?.conversationId === item.id }"
              @click="restoreConversationFromHistory(item)"
            >
              <div class="history-item-main">
                <div class="history-item-title">{{ item.title || t('portal.untitled') }}</div>
                <div class="history-item-meta">
                  <span>{{ item.message_count }} {{ t('portal.messages') }}</span>
                  <span>{{ formatHistoryTime(item.updated_at) }}</span>
                </div>
              </div>
              <n-button
                size="tiny"
                quaternary
                type="error"
                @click="deleteHistoryConversation(item, $event)"
              >
                {{ t('common.delete') }}
              </n-button>
            </div>
          </div>
        </div>
      </section>

      <section class="portal-chat">
        <div class="chat-header">
          <div>
            <p class="portal-kicker">{{ t('portal.currentService') }}</p>
            <h2>{{ selectedAgent?.name || t('portal.selectAgent') }}</h2>
            <p>{{ selectedAgent?.description || t('portal.selectAgentHint') }}</p>
          </div>
          <div class="chat-header-right">
            <div v-if="wsMode" class="ws-status" :class="wsStatusClass">
              <span class="ws-status-dot"></span>
              <span class="ws-status-text">{{ wsStatusText }}</span>
            </div>
            <n-button size="small" secondary @click="toggleWsMode">
              {{ wsMode ? t('portal.wsMode') : t('portal.sseMode') }}
            </n-button>
            <n-tag v-if="selectedAgent" type="success" round>{{ t('portal.online') }}</n-tag>
          </div>
        </div>

        <div ref="chatThreadRef" class="chat-thread">
          <div v-if="!messages.length" class="chat-empty">
            <h3>{{ t('portal.startConversation') }}</h3>
            <p>{{ t('portal.startHint') }}</p>
          </div>

          <article
            v-for="messageItem in messages"
            :key="messageItem.id"
            class="chat-message"
            :class="messageItem.role"
          >
            <div class="chat-bubble">
              <div class="chat-role">
                {{ messageItem.role === "user" ? t('portal.me') : messageItem.agentName || selectedAgent?.name || t('portal.agent') }}
              </div>
              <n-collapse v-if="messageItem.thinking" class="thinking-collapse">
                <n-collapse-item :title="t('portal.thinking')" name="thinking">
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
              <div v-if="messageItem.toolProgress && messageItem.streaming" class="tool-progress">
                <span class="tool-progress-icon">&#9881;</span>
                {{ messageItem.toolProgress }}
              </div>
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
              {{ t('portal.contextCompressed') }}
            </n-alert>
            <div v-if="messageItem.role === 'assistant' && !messageItem.streaming && (messageItem.content || messageItem.error)" class="chat-actions">
              <n-button size="tiny" secondary :disabled="sending" @click="retry(messageItem)">
                {{ t('portal.retryAnswer') }}
              </n-button>
              <n-button
                v-if="messageItem.runId"
                size="tiny"
                :type="messageItem.feedback === 'like' ? 'primary' : 'default'"
                :secondary="messageItem.feedback !== 'like'"
                @click="submitFeedback(messageItem, 'like')"
              >
                {{ messageItem.feedback === 'like' ? t('portal.liked') : t('portal.like') }}
              </n-button>
              <n-button
                v-if="messageItem.runId"
                size="tiny"
                :type="messageItem.feedback === 'dislike' ? 'error' : 'default'"
                :secondary="messageItem.feedback !== 'dislike'"
                @click="submitFeedback(messageItem, 'dislike')"
              >
                {{ messageItem.feedback === 'dislike' ? t('portal.disliked') : t('portal.dislike') }}
              </n-button>
            </div>
            <div v-if="messageItem.citations?.length" class="chat-citations">
                <n-collapse>
                  <n-collapse-item :title="t('portal.citations')" name="citations">
                    <n-list>
                      <n-list-item v-for="chunk in messageItem.citations" :key="chunk.chunk_id">
                        <n-thing :title="chunk.source" :description="`${t('common.similarity')}${chunk.score.toFixed(3)}`">
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
          <div class="composer-input-wrap">
            <div v-if="uploadedFile" class="file-tag">
              <span class="file-tag-text">
                📎 {{ uploadedFile.name }}
                <template v-if="uploadedFile.isImage">{{ t('portal.imageNotSupportedTip') }}</template>
                <template v-else>{{ t('portal.charCountTip', { n: uploadedFile.charCount }) }}</template>
              </span>
              <n-button size="tiny" quaternary type="error" @click="removeFile">×</n-button>
            </div>
            <n-input
              v-model:value="input"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              :placeholder="t('portal.inputPlaceholder')"
              :disabled="!selectedAgent || sending"
              @keydown.enter.exact.prevent="send"
            />
          </div>
          <n-button
            :loading="uploading"
            :disabled="!selectedAgent || sending"
            :title="t('portal.uploadFile')"
            @click="triggerFileUpload"
          >
            📎
          </n-button>
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf,.txt,.md,.png,.jpg,.jpeg"
            hidden
            @change="handleFileChange"
          />
          <n-button type="primary" :loading="sending" :disabled="!selectedAgent" @click="send">
            {{ t('portal.send') }}
          </n-button>
          <n-button v-if="wsMode && sending" type="warning" @click="stopWsGeneration">
            {{ t('portal.wsStop') }}
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
import { useI18n } from "vue-i18n";
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
  toolProgress?: string; // WebSocket 模式下的工具调用进度文本
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

interface UploadedFile {
  name: string;
  content: string; // 后端解析出的文本内容
  charCount: number;
  isImage: boolean;
}

interface FileUploadResponse {
  file_id: string;
  filename: string;
  content_type: string;
  text_content: string;
  char_count: number;
  message: string;
}

const STORAGE_KEY = "agentpilot-portal-conversation";
const MAX_STORED_MESSAGES = 40;
const MAX_STORED_CONTENT_LENGTH = 12000;
const MAX_STORED_CITATIONS = 3;
const MAX_STORED_CITATION_LENGTH = 600;

const message = useMessage();
const router = useRouter();
const ui = useUiStore();
const { t, locale } = useI18n();
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

// ===== 文件上传 =====
const uploadedFile = ref<UploadedFile | null>(null);
const uploading = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"];

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

function toggleLocale() {
  ui.toggleLocale();
  locale.value = ui.locale;
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
  message.success(t('portal.newSessionStarted'));
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
    message.error(t('portal.restoreFailed'));
  }
}

async function deleteHistoryConversation(item: ConversationHistoryItem, event: Event) {
  event.stopPropagation();
  try {
    await api.delete(`/conversations/${item.id}`);
    conversationHistory.value = conversationHistory.value.filter((c) => c.id !== item.id);
    message.success(t('portal.deleted'));
  } catch (error) {
    console.error("删除会话失败", error);
    message.error(t('portal.deleteFailed'));
  }
}

async function saveCurrentConversation(agentId: string) {
  const conv = conversations[agentId];
  if (!conv || !conv.chatHistory.length) return;

  const firstUserMsg = conv.messages.find((m) => m.role === "user");
  const title = (firstUserMsg?.content || t('portal.newConv')).slice(0, 50);
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
    message.warning(t('portal.noRunForFeedback'));
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
    message.error(t('portal.feedbackFailed'));
  }
}

function formatHistoryTime(iso: string): string {
  if (!iso) return "";
  try {
    const date = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return t('portal.justNow');
    if (minutes < 60) return t('portal.minutesAgo', { n: minutes });
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return t('portal.hoursAgo', { n: hours });
    const days = Math.floor(hours / 24);
    if (days < 7) return t('portal.daysAgo', { n: days });
    return date.toLocaleDateString(ui.locale === 'zh' ? 'zh-CN' : 'en-US');
  } catch {
    return iso;
  }
}

// ===== 文件上传 =====

function triggerFileUpload() {
  if (!selectedAgent.value || sending.value || uploading.value) return;
  fileInputRef.value?.click();
}

function removeFile() {
  uploadedFile.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
}

function isImageFile(filename: string): boolean {
  const lower = filename.toLowerCase();
  return IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

async function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  // 重置 input 的 value，便于重复选择同一文件
  target.value = "";

  // 文件大小校验
  if (file.size > MAX_FILE_SIZE) {
    message.error(t('portal.fileTooLarge'));
    return;
  }

  // 图片文件不支持内容提取
  if (isImageFile(file.name)) {
    message.warning(t('portal.imageNotSupported'));
    return;
  }

  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post<FileUploadResponse>("/files/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    const data = response.data;
    uploadedFile.value = {
      name: data.filename || file.name,
      content: data.text_content || "",
      charCount: data.char_count ?? data.text_content?.length ?? 0,
      isImage: false
    };
    message.success(t('portal.uploadSuccess'));
  } catch (error) {
    console.error("文件上传失败", error);
    message.error(t('portal.uploadFailed'));
  } finally {
    uploading.value = false;
  }
}

// ===== WebSocket 实时通信 =====
// 作为 SSE 的可选替代方案，支持双向通信、自动重连与心跳保活

type WsConnectionState = "connected" | "disconnected" | "connecting";

const wsMode = ref(false); // 默认使用 SSE，保持兼容
const wsConnectionState = ref<WsConnectionState>("disconnected");
const wsReconnecting = ref(false); // 是否正在重连

let wsInstance: WebSocket | null = null;
let wsReconnectCount = 0;
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let wsHeartbeatTimer: ReturnType<typeof setInterval> | null = null;

const WS_MAX_RECONNECT = 5; // 最多重连次数
const WS_RECONNECT_INTERVAL = 3000; // 断开后 3 秒重试
const WS_HEARTBEAT_INTERVAL = 30000; // 每 30 秒发送 ping

// 当前 WebSocket 流式回答的上下文，供消息回调更新 UI
interface WsStreamContext {
  agentId: string;
  conversation: AgentConversation;
  assistantMsg: PortalMessage;
  fullAnswer: string;
  resolve: () => void;
}
let wsStreamContext: WsStreamContext | null = null;

// 根据当前环境动态构建 WebSocket 地址
function buildWsUrl(): string {
  // 开发环境（Vite 默认端口 5173）直连后端 8000
  if (window.location.port === "5173") {
    return "ws://localhost:8000/ws/chat";
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/chat`;
}

function connectWebSocket() {
  if (
    wsInstance &&
    (wsInstance.readyState === WebSocket.OPEN ||
      wsInstance.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }
  wsConnectionState.value = "connecting";
  try {
    wsInstance = new WebSocket(buildWsUrl());
  } catch (error) {
    console.error("WebSocket 创建失败", error);
    wsConnectionState.value = "disconnected";
    scheduleReconnect();
    return;
  }

  wsInstance.onopen = () => {
    wsConnectionState.value = "connected";
    wsReconnectCount = 0;
    wsReconnecting.value = false;
    startHeartbeat();
  };

  wsInstance.onclose = () => {
    wsConnectionState.value = "disconnected";
    stopHeartbeat();
    wsInstance = null;
    // 流式回答过程中断开，结束当前回答并提示
    if (wsStreamContext) {
      const ctx = wsStreamContext;
      ctx.assistantMsg.streaming = false;
      if (!ctx.assistantMsg.error) {
        ctx.assistantMsg.error = t('portal.wsDisconnected');
      }
      persistConversation();
      finishWsStream();
    }
    // 仅在 WebSocket 模式下尝试自动重连
    if (wsMode.value) {
      scheduleReconnect();
    }
  };

  wsInstance.onerror = () => {
    console.error("WebSocket 连接错误");
  };

  wsInstance.onmessage = handleWsMessage;
}

function disconnectWebSocket() {
  wsMode.value = false;
  stopHeartbeat();
  clearReconnectTimer();
  wsReconnectCount = 0;
  wsReconnecting.value = false;
  if (wsInstance) {
    // 屏蔽 onclose，避免触发重连
    wsInstance.onclose = null;
    try {
      wsInstance.close();
    } catch { /* ignore */ }
    wsInstance = null;
  }
  wsConnectionState.value = "disconnected";
}

function scheduleReconnect() {
  if (wsReconnectCount >= WS_MAX_RECONNECT) {
    wsReconnecting.value = false;
    wsConnectionState.value = "disconnected";
    message.warning(t('portal.wsReconnectFailed'));
    return;
  }
  wsReconnecting.value = true;
  wsReconnectCount += 1;
  clearReconnectTimer();
  wsReconnectTimer = setTimeout(() => {
    if (!wsMode.value) return;
    connectWebSocket();
  }, WS_RECONNECT_INTERVAL);
}

function clearReconnectTimer() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
}

function startHeartbeat() {
  stopHeartbeat();
  wsHeartbeatTimer = setInterval(() => {
    if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
      try {
        wsInstance.send(JSON.stringify({ type: "ping" }));
      } catch { /* ignore */ }
    }
  }, WS_HEARTBEAT_INTERVAL);
}

function stopHeartbeat() {
  if (wsHeartbeatTimer) {
    clearInterval(wsHeartbeatTimer);
    wsHeartbeatTimer = null;
  }
}

// 等待 WebSocket 连接就绪，超时返回 false
function waitForWsOpen(timeoutMs = 5000): Promise<boolean> {
  return new Promise((resolve) => {
    if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
      resolve(true);
      return;
    }
    const interval = setInterval(() => {
      if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
        clearInterval(interval);
        clearTimeout(timer);
        resolve(true);
      }
    }, 100);
    const timer = setTimeout(() => {
      clearInterval(interval);
      resolve(false);
    }, timeoutMs);
  });
}

// 解析并分发 WebSocket 消息
function handleWsMessage(event: MessageEvent) {
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(event.data) as Record<string, unknown>;
  } catch {
    return;
  }
  const evt = data.event as string | undefined;
  const ctx = wsStreamContext;

  switch (evt) {
    case "tool_progress": {
      if (!ctx) break;
      const tpData = data.data as { tool_names?: string[]; status?: string } | undefined;
      if (tpData) {
        if (tpData.status === "running") {
          ctx.assistantMsg.toolProgress = t('portal.wsToolCalling');
        } else {
          ctx.assistantMsg.toolProgress = undefined;
        }
      }
      break;
    }
    case "steps":
      // 步骤面板更新（PortalPage 暂不展示执行步骤，忽略）
      break;
    case "citations":
      if (ctx) {
        const citations = (data.citations ?? data.data) as RetrievedChunk[] | undefined;
        if (citations) {
          ctx.assistantMsg.citations = citations;
        }
      }
      break;
    case "token": {
      if (!ctx) break;
      const token = (data.token as string) || "";
      ctx.fullAnswer += token;
      ctx.assistantMsg.content = ctx.fullAnswer;
      const parsed = splitThinking(ctx.fullAnswer);
      ctx.assistantMsg.parts = parsed.parts;
      ctx.assistantMsg.thinking = parsed.thinking;
      persistConversation();
      scrollToBottom();
      break;
    }
    case "cancelled":
      if (ctx) {
        ctx.assistantMsg.streaming = false;
        ctx.assistantMsg.toolProgress = undefined;
        if (ctx.fullAnswer && !ctx.assistantMsg.error) {
          ctx.conversation.chatHistory.push({ role: "assistant", content: ctx.fullAnswer });
          trimHistory(ctx.conversation);
        }
        persistConversation();
        void saveCurrentConversation(ctx.agentId);
        finishWsStream();
      }
      break;
    case "error":
      if (ctx) {
        ctx.assistantMsg.error = (data.message as string) || t('portal.errorModel');
        ctx.assistantMsg.streaming = false;
        persistConversation();
        finishWsStream();
      } else {
        message.error((data.message as string) || t('portal.errorModel'));
      }
      break;
    case "done":
      if (ctx) {
        if (data.run_id) {
          ctx.assistantMsg.runId = data.run_id as string;
        }
        if (data.compressed) {
          ctx.assistantMsg.compressed = true;
        }
        ctx.assistantMsg.content = ctx.fullAnswer;
        const parsed = splitThinking(ctx.fullAnswer);
        ctx.assistantMsg.parts = parsed.parts;
        ctx.assistantMsg.thinking = parsed.thinking;
        ctx.assistantMsg.streaming = false;
        if (ctx.fullAnswer && !ctx.assistantMsg.error) {
          ctx.conversation.chatHistory.push({ role: "assistant", content: ctx.fullAnswer });
          trimHistory(ctx.conversation);
        }
        persistConversation();
        // 保存会话到后端
        void saveCurrentConversation(ctx.agentId);
        finishWsStream();
      }
      break;
    case "pong":
      // 心跳响应，忽略
      break;
    default:
      break;
  }
}

// 结束当前 WebSocket 流式回答，释放上下文
function finishWsStream() {
  const ctx = wsStreamContext;
  if (ctx) {
    wsStreamContext = null;
    sending.value = false;
    ctx.resolve();
  }
}

// 切换 SSE / WebSocket 通信模式
function toggleWsMode() {
  if (!wsMode.value) {
    wsMode.value = true;
    wsReconnectCount = 0;
    connectWebSocket();
  } else {
    disconnectWebSocket();
  }
}

// 停止 WebSocket 模式下的生成
function stopWsGeneration() {
  if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
    try {
      wsInstance.send(JSON.stringify({ action: "cancel" }));
    } catch { /* ignore */ }
  }
}

const wsStatusClass = computed(() => {
  if (wsReconnecting.value) return "ws-disconnected";
  switch (wsConnectionState.value) {
    case "connected":
      return "ws-connected";
    case "connecting":
      return "ws-connecting";
    default:
      return "ws-disconnected";
  }
});

const wsStatusText = computed(() => {
  if (wsReconnecting.value) return t('portal.wsReconnecting');
  switch (wsConnectionState.value) {
    case "connected":
      return t('portal.wsConnected');
    case "connecting":
      return t('portal.wsConnecting');
    default:
      return t('portal.wsDisconnected');
  }
});

// WebSocket 模式下的流式请求
async function streamRequestWs(
  agentId: string,
  content: string,
  conversation: AgentConversation,
  assistantMsg: PortalMessage,
  fileContent?: string,
  fileName?: string
) {
  sending.value = true;
  assistantMsg.streaming = true;

  // 确保连接已建立
  if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
    connectWebSocket();
    const opened = await waitForWsOpen(5000);
    if (!opened) {
      assistantMsg.streaming = false;
      assistantMsg.error = t('portal.wsConnectTimeout');
      persistConversation();
      sending.value = false;
      return;
    }
  }

  await new Promise<void>((resolve) => {
    wsStreamContext = {
      agentId,
      conversation,
      assistantMsg,
      fullAnswer: "",
      resolve
    };

    const payload: Record<string, unknown> = {
      agent_id: agentId,
      input: content,
      messages: conversation.chatHistory.slice(0, -1),
      file_content: fileContent || "",
      file_name: fileName || ""
    };

    try {
      wsInstance?.send(JSON.stringify(payload));
    } catch (err) {
      assistantMsg.streaming = false;
      assistantMsg.error = (err as Error).message || t('portal.wsNotConnected');
      persistConversation();
      finishWsStream();
    }
  });
}

async function streamRequest(
  agentId: string,
  content: string,
  conversation: AgentConversation,
  assistantMsg: PortalMessage,
  fileContent?: string,
  fileName?: string
) {
  sending.value = true;
  assistantMsg.streaming = true;
  try {
    const payload: Record<string, unknown> = {
      agent_id: agentId,
      input: content,
      messages: conversation.chatHistory.slice(0, -1)
    };
    if (fileContent && fileName) {
      payload.file_content = fileContent;
      payload.file_name = fileName;
    }
    const response = await fetch("/api/runs/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok || !response.body) {
      throw new Error(t('portal.errorHttp', { n: response.status }));
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
              assistantMsg.error = errData.message || t('portal.errorModel');
            } catch {
              assistantMsg.error = t('portal.errorModel');
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
      assistantMsg.error = t('portal.errorNetwork');
    } else if (err.message.includes("timeout") || err.message.includes("Timeout")) {
      assistantMsg.error = t('portal.errorTimeout');
    } else {
      assistantMsg.error = err.message || t('portal.errorGeneric');
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
    message.warning(t('portal.selectAgentFirst'));
    return;
  }
  if (!content) {
    message.warning(t('portal.enterQuestion'));
    return;
  }

  const agentId = selectedAgentId.value;
  const agentName = selectedAgent.value?.name || t('portal.agent');
  const conversation = ensureConversation(agentId);

  // 捕获当前上传的文件内容，发送后清空
  const fileContent = uploadedFile.value?.content || "";
  const fileName = uploadedFile.value?.name || "";

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

  // 文件内容已注入对话，清空文件状态
  removeFile();

  if (wsMode.value) {
    await streamRequestWs(agentId, content, conversation, assistantMsg, fileContent, fileName);
  } else {
    await streamRequest(agentId, content, conversation, assistantMsg, fileContent, fileName);
  }
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

  if (wsMode.value) {
    await streamRequestWs(agentId, content, conversation, assistantMsg);
  } else {
    await streamRequest(agentId, content, conversation, assistantMsg);
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
  // 关闭 WebSocket 连接，清理定时器
  disconnectWebSocket();
});
</script>

<style scoped>
/* 输入区包裹层：承载文件标签与输入框 */
.composer-input-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 已上传文件标签 */
.file-tag {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 10px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent-soft);
  font-size: 12px;
  color: var(--text-strong);
}

.file-tag-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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

/* 对话头部右侧操作区 */
.chat-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* WebSocket 连接状态指示灯 */
.ws-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface-soft);
  font-size: 12px;
  color: var(--text-muted);
}

.ws-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.ws-status-text {
  white-space: nowrap;
}

/* 已连接：绿色 */
.ws-status.ws-connected .ws-status-dot {
  background: #18a058;
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.18);
}

/* 连接中：黄色 */
.ws-status.ws-connecting .ws-status-dot {
  background: #f0a020;
  box-shadow: 0 0 0 2px rgba(240, 160, 32, 0.18);
  animation: ws-blink 1s ease-in-out infinite;
}

/* 已断开：红色 */
.ws-status.ws-disconnected .ws-status-dot {
  background: #d03050;
  box-shadow: 0 0 0 2px rgba(208, 48, 80, 0.18);
}

@keyframes ws-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 工具调用进度指示器 */
.tool-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 12px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent-soft);
  font-size: 13px;
  color: var(--text-strong);
}

.tool-progress-icon {
  animation: ws-blink 1.2s ease-in-out infinite;
  font-size: 14px;
}
</style>
