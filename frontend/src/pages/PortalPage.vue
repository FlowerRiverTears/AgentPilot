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

        <div v-if="!store.agents.length" class="portal-empty-panel">
          <h2>还没有可用智能体</h2>
          <p>请进入后台创建智能体后，再回到前台提供服务。</p>
          <n-button type="primary" @click="goAdmin">去后台创建</n-button>
        </div>

        <div v-else class="agent-list">
          <button
            v-for="agent in store.agents"
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

        <div class="chat-thread">
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
              <div class="chat-role">{{ messageItem.role === "user" ? "我" : selectedAgent?.name || "智能体" }}</div>
              <n-collapse v-if="messageItem.thinking" class="thinking-collapse">
                <n-collapse-item title="思考过程" name="thinking">
                  <div class="thinking-content">{{ messageItem.thinking }}</div>
                </n-collapse-item>
              </n-collapse>
              <div class="answer-render">
                <template v-for="(part, index) in messageItem.parts" :key="index">
                  <pre v-if="part.type === 'code'" class="answer-code"><code>{{ part.content }}</code></pre>
                  <div v-else class="chat-content">{{ part.content }}</div>
                </template>
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
import { computed, onMounted, ref } from "vue";
import { useMessage } from "naive-ui";
import { useRouter } from "vue-router";

import type { RetrievedChunk } from "../api/types";
import { useUiStore } from "../stores/ui";
import { useWorkspaceStore } from "../stores/workspace";
import { splitThinking, type AnswerPart } from "../utils/answerFormat";

interface PortalMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  parts: AnswerPart[];
  thinking?: string;
  citations?: RetrievedChunk[];
}

const message = useMessage();
const router = useRouter();
const ui = useUiStore();
const store = useWorkspaceStore();
const selectedAgentId = ref<string | null>(null);
const input = ref("");
const sending = ref(false);
const loadingAgents = ref(false);
const messages = ref<PortalMessage[]>([]);

const selectedAgent = computed(
  () => store.agents.find((agent) => agent.id === selectedAgentId.value) ?? null
);

function selectAgent(agentId: string) {
  selectedAgentId.value = agentId;
  messages.value = [];
}

function goAdmin() {
  router.push("/agents");
}

async function refreshAgents() {
  loadingAgents.value = true;
  try {
    await store.loadAgents();
    if (!selectedAgent.value) {
      selectedAgentId.value = store.agents[0]?.id ?? null;
    }
  } finally {
    loadingAgents.value = false;
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

  input.value = "";
  messages.value.push({
    id: crypto.randomUUID(),
    role: "user",
    content,
    parts: [{ type: "text", content }]
  });

  sending.value = true;
  try {
    const result = await store.runAgent(selectedAgentId.value, content);
    const parsedAnswer = splitThinking(result.answer);
    messages.value.push({
      id: result.run_id,
      role: "assistant",
      content: parsedAnswer.content,
      parts: parsedAnswer.parts,
      thinking: parsedAnswer.thinking,
      citations: result.citations
    });
  } catch (error) {
    message.error("智能体暂时无法回复，请检查后台智能体和模型配置");
    console.error(error);
  } finally {
    sending.value = false;
  }
}

function snippet(text: string, limit = 160) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit)}...`;
}

onMounted(refreshAgents);
</script>
