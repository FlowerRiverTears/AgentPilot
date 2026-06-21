<template>
  <div class="page-grid">
    <n-page-header title="智能体评测" subtitle="创建评测数据集，触发评测并查看准确率、耗时等指标报告" />

    <!-- 评测数据集管理 -->
    <n-card title="评测数据集">
      <template #header-extra>
        <n-button type="primary" @click="openCreateModal">创建数据集</n-button>
      </template>
      <n-spin :show="loadingDatasets">
        <n-empty v-if="!datasets.length" description="暂无评测数据集，点击右上角创建" />
        <n-list v-else bordered>
          <n-list-item v-for="ds in datasets" :key="ds.id">
            <n-thing>
              <template #header>{{ ds.name }}</template>
              <template #header-extra>
                <n-space size="small">
                  <n-button size="small" type="primary" :loading="runningId === ds.id" @click="runEval(ds)">
                    触发评测
                  </n-button>
                  <n-button size="small" secondary @click="viewDatasetResults(ds)">查看结果</n-button>
                  <n-button size="small" type="error" secondary @click="confirmDeleteDataset(ds)">删除</n-button>
                </n-space>
              </template>
              <template #description>
                <n-space size="small" align="center">
                  <n-tag size="small" type="info">关联智能体：{{ agentName(ds.agent_id) }}</n-tag>
                  <n-tag size="small">用例数：{{ ds.cases?.length ?? 0 }}</n-tag>
                  <n-tag size="small">{{ formatTime(ds.created_at) }}</n-tag>
                </n-space>
              </template>
              <div v-if="ds.description" class="dataset-desc">{{ ds.description }}</div>
            </n-thing>
          </n-list-item>
        </n-list>
      </n-spin>
    </n-card>

    <!-- 评测结果 -->
    <n-card title="评测结果">
      <template #header-extra>
        <n-space align="center">
          <n-select
            v-model:value="resultFilterDatasetId"
            :options="datasetFilterOptions"
            placeholder="全部数据集"
            clearable
            size="small"
            style="width: 200px"
            @update:value="loadResults"
          />
          <n-button size="small" secondary @click="loadResults">刷新</n-button>
        </n-space>
      </template>
      <n-spin :show="loadingResults">
        <n-empty v-if="!results.length" description="暂无评测结果" />
        <n-list v-else bordered>
          <n-list-item v-for="r in results" :key="r.id">
            <n-thing>
              <template #header>
                <n-space align="center" size="small">
                  <span>{{ datasetName(r.dataset_id) }}</span>
                  <n-tag :type="statusTagType(r.status)" size="small">{{ statusLabel(r.status) }}</n-tag>
                </n-space>
              </template>
              <template #header-extra>
                <n-button size="small" secondary @click="viewResultDetail(r)">查看详情</n-button>
              </template>
              <div class="result-summary">
                <div class="result-accuracy">
                  <span class="result-label">准确率</span>
                  <n-progress
                    type="line"
                    :percentage="accuracyPercent(r.accuracy)"
                    :status="progressStatus(r.accuracy)"
                    style="width: 200px"
                  />
                  <span class="result-value">{{ r.passed_cases }} / {{ r.total_cases }}</span>
                </div>
                <n-space size="small">
                  <n-tag size="small">平均耗时：{{ r.avg_duration_ms ? `${r.avg_duration_ms}ms` : "-" }}</n-tag>
                  <n-tag size="small">{{ formatTime(r.created_at) }}</n-tag>
                </n-space>
              </div>
            </n-thing>
          </n-list-item>
        </n-list>
      </n-spin>
    </n-card>

    <!-- 创建数据集弹窗 -->
    <n-modal v-model:show="showCreate" preset="card" title="创建评测数据集" style="max-width: 720px">
      <n-form label-placement="top">
        <n-form-item label="数据集名称" required>
          <n-input v-model:value="form.name" placeholder="请输入数据集名称" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input
            v-model:value="form.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="可选，描述该数据集的用途"
          />
        </n-form-item>
        <n-form-item label="关联智能体" required>
          <n-select v-model:value="form.agent_id" :options="agentOptions" placeholder="选择要评测的智能体" />
        </n-form-item>
        <n-form-item label="测试用例" required>
          <div class="cases-editor">
            <div v-for="(c, idx) in form.cases" :key="idx" class="case-item">
              <div class="case-head">
                <span class="case-index">用例 {{ idx + 1 }}</span>
                <n-button
                  size="tiny"
                  type="error"
                  secondary
                  :disabled="form.cases.length <= 1"
                  @click="removeCase(idx)"
                >
                  删除
                </n-button>
              </div>
              <n-input
                v-model:value="c.question"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 4 }"
                placeholder="输入测试问题"
              />
              <div class="case-keywords">
                <span class="case-label">期望关键词：</span>
                <n-dynamic-tags v-model:value="c.expected_keywords" />
              </div>
            </div>
            <n-button dashed block @click="addCase">+ 添加用例</n-button>
          </div>
        </n-form-item>
        <div class="form-actions">
          <n-button type="primary" block :loading="creating" @click="submitCreate">创建数据集</n-button>
        </div>
      </n-form>
    </n-modal>

    <!-- 评测结果详情 -->
    <n-modal v-model:show="showDetail" preset="card" title="评测结果详情" style="max-width: 900px">
      <template v-if="detail">
        <n-descriptions bordered :column="2" label-placement="left">
          <n-descriptions-item label="数据集">{{ datasetName(detail.dataset_id) }}</n-descriptions-item>
          <n-descriptions-item label="状态">
            <n-tag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="准确率">{{ accuracyPercent(detail.accuracy) }}%</n-descriptions-item>
          <n-descriptions-item label="通过数">{{ detail.passed_cases }} / {{ detail.total_cases }}</n-descriptions-item>
          <n-descriptions-item label="平均耗时">
            {{ detail.avg_duration_ms ? `${detail.avg_duration_ms}ms` : "-" }}
          </n-descriptions-item>
          <n-descriptions-item label="创建时间">{{ formatTime(detail.created_at) }}</n-descriptions-item>
        </n-descriptions>

        <n-divider>用例明细</n-divider>
        <n-list bordered>
          <n-list-item v-for="(d, idx) in detail.details" :key="idx">
            <n-thing>
              <template #header>
                <n-space align="center" size="small">
                  <span>用例 {{ idx + 1 }}</span>
                  <n-tag :type="d.passed ? 'success' : 'error'" size="small">
                    {{ d.passed ? "通过" : "未通过" }}
                  </n-tag>
                  <n-tag size="small">{{ d.duration_ms ? `${d.duration_ms}ms` : "-" }}</n-tag>
                </n-space>
              </template>
              <div class="detail-block">
                <div class="detail-row">
                  <span class="detail-label">问题：</span>
                  <span>{{ d.question }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">回答：</span>
                  <div class="detail-answer">{{ d.answer || "（无回答）" }}</div>
                </div>
                <div class="detail-row">
                  <span class="detail-label">期望关键词：</span>
                  <n-space size="small">
                    <n-tag v-for="k in d.expected_keywords" :key="k" size="small">{{ k }}</n-tag>
                    <span v-if="!d.expected_keywords?.length" class="muted">无</span>
                  </n-space>
                </div>
                <div class="detail-row">
                  <span class="detail-label">匹配关键词：</span>
                  <n-space size="small">
                    <n-tag v-for="k in d.matched_keywords" :key="k" size="small" type="success">{{ k }}</n-tag>
                    <span v-if="!d.matched_keywords?.length" class="muted">无</span>
                  </n-space>
                </div>
                <n-alert v-if="d.error" type="error" :bordered="false" class="detail-error">{{ d.error }}</n-alert>
              </div>
            </n-thing>
          </n-list-item>
        </n-list>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useDialog, useMessage } from "naive-ui";

import { api } from "../api/client";

const message = useMessage();
const dialog = useDialog();

// 评测相关类型定义
interface EvalCase {
  question: string;
  expected_keywords: string[];
}
interface EvalDataset {
  id: string;
  name: string;
  description: string;
  agent_id: string;
  cases: EvalCase[];
  created_at: string;
}
interface EvalCaseResult {
  question: string;
  answer: string;
  expected_keywords: string[];
  matched_keywords: string[];
  passed: boolean;
  duration_ms: number;
  error: string;
}
interface EvalResult {
  id: string;
  dataset_id: string;
  agent_id: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  accuracy: number;
  avg_duration_ms: number;
  details: EvalCaseResult[];
  created_at: string;
}

// 列表数据
const datasets = ref<EvalDataset[]>([]);
const results = ref<EvalResult[]>([]);
const agents = ref<Array<{ id: string; name: string }>>([]);
const loadingDatasets = ref(false);
const loadingResults = ref(false);
const runningId = ref<string | null>(null);

// 创建数据集弹窗状态
const showCreate = ref(false);
const creating = ref(false);
const form = reactive({
  name: "",
  description: "",
  agent_id: null as string | null,
  cases: [{ question: "", expected_keywords: [] as string[] }]
});

// 结果详情弹窗状态
const showDetail = ref(false);
const detail = ref<EvalResult | null>(null);

// 结果列表按数据集筛选
const resultFilterDatasetId = ref<string | null>(null);

const agentOptions = computed(() =>
  agents.value.map((a) => ({ label: a.name, value: a.id }))
);

const datasetFilterOptions = computed(() =>
  datasets.value.map((d) => ({ label: d.name, value: d.id }))
);

function agentName(agentId: string) {
  return agents.value.find((a) => a.id === agentId)?.name ?? agentId ?? "-";
}

function datasetName(datasetId: string) {
  return datasets.value.find((d) => d.id === datasetId)?.name ?? datasetId ?? "-";
}

function formatTime(t: string) {
  if (!t) return "-";
  try {
    return new Date(t).toLocaleString("zh-CN");
  } catch {
    return t;
  }
}

// 兼容 accuracy 为 0-1 或 0-100 两种返回格式
function accuracyPercent(accuracy: number) {
  if (accuracy == null) return 0;
  return accuracy > 1 ? Math.round(accuracy) : Math.round(accuracy * 100);
}

function progressStatus(accuracy: number) {
  const p = accuracyPercent(accuracy);
  if (p >= 80) return "success";
  if (p >= 50) return "warning";
  return "error";
}

function statusTagType(status: string) {
  if (status === "completed" || status === "success") return "success";
  if (status === "running" || status === "pending") return "info";
  if (status === "failed") return "error";
  return "default";
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    completed: "已完成",
    success: "成功",
    running: "运行中",
    pending: "等待中",
    failed: "失败"
  };
  return map[status] ?? status;
}

async function loadDatasets() {
  loadingDatasets.value = true;
  try {
    const res = await api.get<EvalDataset[]>("/eval/datasets");
    datasets.value = res.data;
  } catch (e: any) {
    message.error(e?.message || "加载数据集失败");
  } finally {
    loadingDatasets.value = false;
  }
}

async function loadAgents() {
  try {
    const res = await api.get<Array<{ id: string; name: string }>>("/agents");
    agents.value = res.data;
  } catch (e: any) {
    console.error("加载智能体失败", e);
  }
}

async function loadResults() {
  loadingResults.value = true;
  try {
    const params: Record<string, string> = {};
    if (resultFilterDatasetId.value) {
      params.dataset_id = resultFilterDatasetId.value;
    }
    const res = await api.get<EvalResult[]>("/eval/results", { params });
    results.value = res.data;
  } catch (e: any) {
    message.error(e?.message || "加载评测结果失败");
  } finally {
    loadingResults.value = false;
  }
}

function openCreateModal() {
  form.name = "";
  form.description = "";
  form.agent_id = agents.value[0]?.id ?? null;
  form.cases = [{ question: "", expected_keywords: [] }];
  showCreate.value = true;
}

function addCase() {
  form.cases.push({ question: "", expected_keywords: [] });
}

function removeCase(idx: number) {
  form.cases.splice(idx, 1);
}

async function submitCreate() {
  if (!form.name.trim()) {
    message.warning("请填写数据集名称");
    return;
  }
  if (!form.agent_id) {
    message.warning("请选择关联智能体");
    return;
  }
  const validCases = form.cases.filter((c) => c.question.trim());
  if (!validCases.length) {
    message.warning("至少需要 1 条测试用例（需填写问题）");
    return;
  }
  creating.value = true;
  try {
    await api.post("/eval/datasets", {
      name: form.name.trim(),
      description: form.description.trim(),
      agent_id: form.agent_id,
      cases: validCases.map((c) => ({
        question: c.question.trim(),
        expected_keywords: c.expected_keywords
      }))
    });
    message.success("数据集已创建");
    showCreate.value = false;
    await loadDatasets();
  } catch (e: any) {
    message.error(e?.message || "创建数据集失败");
  } finally {
    creating.value = false;
  }
}

async function runEval(ds: EvalDataset) {
  runningId.value = ds.id;
  message.info(`正在评测「${ds.name}」，可能耗时较长，请耐心等待...`);
  try {
    await api.post(`/eval/datasets/${ds.id}/run`);
    message.success("评测完成");
    await loadResults();
  } catch (e: any) {
    message.error(e?.message || "触发评测失败");
  } finally {
    runningId.value = null;
  }
}

function viewDatasetResults(ds: EvalDataset) {
  resultFilterDatasetId.value = ds.id;
  loadResults();
}

async function viewResultDetail(r: EvalResult) {
  try {
    const res = await api.get<EvalResult>(`/eval/results/${r.id}`);
    detail.value = res.data;
    showDetail.value = true;
  } catch (e: any) {
    message.error(e?.message || "获取评测详情失败");
  }
}

function confirmDeleteDataset(ds: EvalDataset) {
  dialog.warning({
    title: "删除数据集",
    content: `确认删除评测数据集「${ds.name}」吗？关联的评测结果可能也会被清除。`,
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await api.delete(`/eval/datasets/${ds.id}`);
        message.success("数据集已删除");
        if (resultFilterDatasetId.value === ds.id) {
          resultFilterDatasetId.value = null;
        }
        await Promise.all([loadDatasets(), loadResults()]);
      } catch (e: any) {
        message.error(e?.message || "删除数据集失败");
      }
    }
  });
}

onMounted(async () => {
  await Promise.all([loadDatasets(), loadAgents(), loadResults()]);
});
</script>

<style scoped>
.dataset-desc {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.result-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-accuracy {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-label {
  color: var(--text-muted);
  font-size: 13px;
  white-space: nowrap;
}

.result-value {
  color: var(--text-strong);
  font-weight: 600;
  font-size: 13px;
}

.cases-editor {
  width: 100%;
  display: grid;
  gap: 12px;
}

.case-item {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-soft);
  display: grid;
  gap: 8px;
}

.case-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.case-index {
  font-weight: 600;
  color: var(--text-strong);
  font-size: 13px;
}

.case-keywords {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
}

.case-label {
  color: var(--text-muted);
  font-size: 13px;
  white-space: nowrap;
  line-height: 28px;
}

.detail-block {
  display: grid;
  gap: 8px;
}

.detail-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.7;
}

.detail-label {
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}

.detail-answer {
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
}

.detail-error {
  margin-top: 4px;
}

.muted {
  color: var(--text-muted);
  font-size: 13px;
}
</style>
