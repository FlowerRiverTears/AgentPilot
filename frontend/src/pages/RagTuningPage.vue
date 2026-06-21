<template>
  <div class="page-grid">
    <n-page-header title="RAG 调优面板" subtitle="调整知识库的分块与检索参数，并实时测试检索效果" />

    <!-- 知识库 RAG 配置列表 -->
    <n-card title="知识库 RAG 配置">
      <template #header-extra>
        <n-button size="small" secondary @click="loadConfigs">刷新</n-button>
      </template>
      <n-spin :show="loadingConfigs">
        <n-empty v-if="!configs.length" description="暂无知识库 RAG 配置" />
        <n-list v-else bordered>
          <n-list-item v-for="cfg in configs" :key="cfg.knowledge_base_id">
            <n-thing>
              <template #header>{{ cfg.knowledge_base_name || cfg.knowledge_base_id }}</template>
              <template #header-extra>
                <n-button size="small" secondary @click="openEditModal(cfg)">编辑</n-button>
              </template>
              <template #description>
                <n-space size="small" align="center">
                  <n-tag size="small">chunk_size：{{ cfg.chunk_size }}</n-tag>
                  <n-tag size="small">chunk_overlap：{{ cfg.chunk_overlap }}</n-tag>
                  <n-tag size="small">top_k：{{ cfg.top_k }}</n-tag>
                  <n-tag size="small">score_threshold：{{ cfg.score_threshold }}</n-tag>
                  <n-tag size="small" type="info">向量权重：{{ cfg.retrieval_weight_vector }}</n-tag>
                  <n-tag size="small" type="info">关键词权重：{{ cfg.retrieval_weight_lexical }}</n-tag>
                </n-space>
              </template>
            </n-thing>
          </n-list-item>
        </n-list>
      </n-spin>
    </n-card>

    <!-- 检索测试 -->
    <n-card title="检索测试">
      <n-form label-placement="top">
        <n-form-item label="知识库" required>
          <n-select
            v-model:value="testForm.knowledge_base_id"
            :options="kbOptions"
            placeholder="选择要测试的知识库"
          />
        </n-form-item>
        <n-form-item label="测试问题" required>
          <n-input
            v-model:value="testForm.query"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="请输入测试问题"
          />
        </n-form-item>
        <n-grid :cols="2" :x-gap="16">
          <n-form-item label="覆盖 top_k（可选）">
            <n-input-number
              v-model:value="testForm.top_k"
              :min="1"
              :max="20"
              placeholder="留空使用知识库默认值"
              style="width: 100%"
            />
          </n-form-item>
          <n-form-item label="覆盖 score_threshold（可选）">
            <n-input-number
              v-model:value="testForm.score_threshold"
              :min="0"
              :max="1"
              :step="0.05"
              placeholder="留空使用知识库默认值"
              style="width: 100%"
            />
          </n-form-item>
        </n-grid>
        <n-button type="primary" block :loading="testing" @click="runTest">检索测试</n-button>
      </n-form>

      <template v-if="testResults.length">
        <n-divider>检索结果（共 {{ testResults.length }} 条）</n-divider>
        <n-list bordered>
          <n-list-item v-for="(chunk, idx) in testResults" :key="idx">
            <n-thing>
              <template #header>
                <n-space align="center" size="small">
                  <span>{{ chunk.source || '未知来源' }}</span>
                  <n-tag size="small" type="success">相似度：{{ formatScore(chunk.score) }}</n-tag>
                  <n-tag v-if="chunk.page != null" size="small">页码：{{ chunk.page }}</n-tag>
                </n-space>
              </template>
              <div class="chunk-content">{{ chunk.content }}</div>
            </n-thing>
          </n-list-item>
        </n-list>
      </template>
      <n-empty v-else-if="testedEmpty" description="未检索到相关文档切片" style="margin-top: 16px" />
    </n-card>

    <!-- 配置编辑弹窗 -->
    <n-modal v-model:show="showEditor" preset="card" :title="`编辑 RAG 配置 - ${editingName}`" style="max-width: 640px">
      <n-form label-placement="top">
        <n-form-item label="chunk_size">
          <div class="slider-row">
            <n-slider
              v-model:value="editForm.chunk_size"
              :min="100"
              :max="2000"
              :step="50"
              :tooltip="false"
              style="flex: 1"
            />
            <n-input-number v-model:value="editForm.chunk_size" :min="100" :max="2000" :step="50" style="width: 140px" />
          </div>
        </n-form-item>
        <n-form-item label="chunk_overlap">
          <div class="slider-row">
            <n-slider
              v-model:value="editForm.chunk_overlap"
              :min="0"
              :max="500"
              :step="10"
              :tooltip="false"
              style="flex: 1"
            />
            <n-input-number v-model:value="editForm.chunk_overlap" :min="0" :max="500" :step="10" style="width: 140px" />
          </div>
        </n-form-item>
        <n-form-item label="top_k">
          <div class="slider-row">
            <n-slider
              v-model:value="editForm.top_k"
              :min="1"
              :max="20"
              :step="1"
              :tooltip="false"
              style="flex: 1"
            />
            <n-input-number v-model:value="editForm.top_k" :min="1" :max="20" :step="1" style="width: 140px" />
          </div>
        </n-form-item>
        <n-form-item label="score_threshold">
          <div class="slider-row">
            <n-slider
              v-model:value="editForm.score_threshold"
              :min="0"
              :max="1"
              :step="0.05"
              :tooltip="false"
              style="flex: 1"
            />
            <n-input-number
              v-model:value="editForm.score_threshold"
              :min="0"
              :max="1"
              :step="0.05"
              style="width: 140px"
            />
          </div>
        </n-form-item>
        <n-form-item label="retrieval_weight_vector（向量权重）">
          <n-slider
            v-model:value="editForm.retrieval_weight_vector"
            :min="0"
            :max="1"
            :step="0.05"
            :tooltip="false"
          />
        </n-form-item>
        <n-form-item label="retrieval_weight_lexical（关键词权重）">
          <n-slider
            v-model:value="editForm.retrieval_weight_lexical"
            :min="0"
            :max="1"
            :step="0.05"
            :tooltip="false"
          />
        </n-form-item>
        <div class="weight-hint">
          当前权重和：{{ weightSum.toFixed(2) }}
          <span v-if="Math.abs(weightSum - 1) > 0.001" class="weight-warn">（建议向量与关键词权重之和为 1）</span>
        </div>
        <div class="form-actions">
          <n-button type="primary" block :loading="saving" @click="submitConfig">保存配置</n-button>
        </div>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useMessage } from "naive-ui";

import { api } from "../api/client";

const message = useMessage();

// RAG 配置相关类型定义
interface RagConfig {
  knowledge_base_id: string;
  knowledge_base_name?: string;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  score_threshold: number;
  retrieval_weight_vector: number;
  retrieval_weight_lexical: number;
}
interface RetrievalChunk {
  content: string;
  source: string;
  score: number;
  page: number | null;
}

// 配置列表
const configs = ref<RagConfig[]>([]);
const loadingConfigs = ref(false);

// 检索测试状态
const testing = ref(false);
const testResults = ref<RetrievalChunk[]>([]);
const testedEmpty = ref(false);
const testForm = reactive({
  knowledge_base_id: null as string | null,
  query: "",
  top_k: null as number | null,
  score_threshold: null as number | null
});

// 编辑弹窗状态
const showEditor = ref(false);
const saving = ref(false);
const editingId = ref<string | null>(null);
const editingName = ref("");
const editForm = reactive({
  chunk_size: 500,
  chunk_overlap: 50,
  top_k: 5,
  score_threshold: 0.5,
  retrieval_weight_vector: 0.7,
  retrieval_weight_lexical: 0.3
});

const kbOptions = computed(() =>
  configs.value.map((c) => ({
    label: c.knowledge_base_name || c.knowledge_base_id,
    value: c.knowledge_base_id
  }))
);

const weightSum = computed(
  () => (editForm.retrieval_weight_vector ?? 0) + (editForm.retrieval_weight_lexical ?? 0)
);

function formatScore(score: number) {
  if (score == null) return "-";
  return Number(score).toFixed(3);
}

async function loadConfigs() {
  loadingConfigs.value = true;
  try {
    const res = await api.get<RagConfig[]>("/rag-tuning/configs");
    configs.value = res.data;
  } catch (e: any) {
    message.error(e?.message || "加载 RAG 配置失败");
  } finally {
    loadingConfigs.value = false;
  }
}

function openEditModal(cfg: RagConfig) {
  editingId.value = cfg.knowledge_base_id;
  editingName.value = cfg.knowledge_base_name || cfg.knowledge_base_id;
  editForm.chunk_size = cfg.chunk_size;
  editForm.chunk_overlap = cfg.chunk_overlap;
  editForm.top_k = cfg.top_k;
  editForm.score_threshold = cfg.score_threshold;
  editForm.retrieval_weight_vector = cfg.retrieval_weight_vector;
  editForm.retrieval_weight_lexical = cfg.retrieval_weight_lexical;
  showEditor.value = true;
}

async function submitConfig() {
  if (!editingId.value) return;
  saving.value = true;
  try {
    await api.put(`/rag-tuning/configs/${editingId.value}`, {
      chunk_size: editForm.chunk_size,
      chunk_overlap: editForm.chunk_overlap,
      top_k: editForm.top_k,
      score_threshold: editForm.score_threshold,
      retrieval_weight_vector: editForm.retrieval_weight_vector,
      retrieval_weight_lexical: editForm.retrieval_weight_lexical
    });
    message.success("RAG 配置已保存");
    showEditor.value = false;
    await loadConfigs();
  } catch (e: any) {
    message.error(e?.message || "保存 RAG 配置失败");
  } finally {
    saving.value = false;
  }
}

async function runTest() {
  if (!testForm.knowledge_base_id) {
    message.warning("请选择知识库");
    return;
  }
  if (!testForm.query.trim()) {
    message.warning("请输入测试问题");
    return;
  }
  testing.value = true;
  testResults.value = [];
  testedEmpty.value = false;
  const payload: Record<string, unknown> = {
    knowledge_base_id: testForm.knowledge_base_id,
    query: testForm.query.trim()
  };
  if (testForm.top_k != null) payload.top_k = testForm.top_k;
  if (testForm.score_threshold != null) payload.score_threshold = testForm.score_threshold;
  try {
    const res = await api.post<RetrievalChunk[]>("/rag-tuning/test", payload);
    testResults.value = res.data ?? [];
    if (!testResults.value.length) testedEmpty.value = true;
  } catch (e: any) {
    message.error(e?.message || "检索测试失败");
  } finally {
    testing.value = false;
  }
}

onMounted(async () => {
  await loadConfigs();
});
</script>

<style scoped>
.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.weight-hint {
  margin: -4px 0 12px;
  font-size: 13px;
  color: var(--text-muted);
}

.weight-warn {
  color: var(--warning-color, #d97706);
  margin-left: 4px;
}

.form-actions {
  margin-top: 8px;
}

.chunk-content {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  padding: 8px;
  background: var(--surface-soft);
  border-radius: 4px;
}
</style>
