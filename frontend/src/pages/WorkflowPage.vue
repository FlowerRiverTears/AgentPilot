<template>
  <div class="page-grid">
    <n-page-header title="工作流画布" subtitle="编排智能体、工具与知识库节点，构建可执行的多步工作流" />

    <!-- 工作流列表 -->
    <n-card title="工作流列表">
      <template #header-extra>
        <n-button type="primary" @click="openCreateModal">创建工作流</n-button>
      </template>
      <n-spin :show="loading">
        <n-empty v-if="!workflows.length" description="暂无工作流，点击右上角创建" />
        <n-list v-else bordered>
          <n-list-item v-for="wf in workflows" :key="wf.id">
            <n-thing>
              <template #header>
                <n-space align="center" size="small">
                  <span>{{ wf.name }}</span>
                  <n-tag :type="statusTagType(wf.status)" size="small">{{ statusLabel(wf.status) }}</n-tag>
                </n-space>
              </template>
              <template #header-extra>
                <n-space size="small">
                  <n-button size="small" secondary @click="openEditModal(wf)">编辑</n-button>
                  <n-button size="small" type="primary" secondary @click="openRunModal(wf)">执行</n-button>
                  <n-button size="small" type="error" secondary @click="confirmDelete(wf)">删除</n-button>
                </n-space>
              </template>
              <template #description>
                <n-space size="small" align="center">
                  <n-tag size="small" type="info">节点数：{{ wf.nodes?.length ?? 0 }}</n-tag>
                  <n-tag size="small">连线数：{{ wf.edges?.length ?? 0 }}</n-tag>
                  <n-tag size="small">{{ formatTime(wf.created_at) }}</n-tag>
                </n-space>
              </template>
              <div v-if="wf.description" class="wf-desc">{{ wf.description }}</div>
            </n-thing>
          </n-list-item>
        </n-list>
      </n-spin>
    </n-card>

    <!-- 创建/编辑工作流弹窗 -->
    <n-modal v-model:show="showEditor" preset="card" :title="editingId ? '编辑工作流' : '创建工作流'" style="max-width: 900px">
      <n-form label-placement="top">
        <n-form-item label="工作流名称" required>
          <n-input v-model:value="form.name" placeholder="请输入工作流名称" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input
            v-model:value="form.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="可选，描述该工作流的用途"
          />
        </n-form-item>

        <!-- 节点编辑器 -->
        <n-form-item label="节点">
          <div class="editor-block">
            <div v-for="(node, idx) in form.nodes" :key="node.id" class="node-item">
              <div class="node-head">
                <n-space align="center" size="small">
                  <span class="node-index">{{ node.id }}</span>
                  <n-tag :type="nodeTagType(node.type)" size="small">{{ nodeTypeLabel(node.type) }}</n-tag>
                </n-space>
                <n-button
                  size="tiny"
                  type="error"
                  secondary
                  :disabled="form.nodes.length <= 1"
                  @click="removeNode(idx)"
                >
                  删除节点
                </n-button>
              </div>
              <n-space vertical size="small">
                <n-select
                  v-model:value="node.type"
                  :options="nodeTypeOptions"
                  size="small"
                  placeholder="节点类型"
                />
                <n-input v-model:value="node.label" size="small" placeholder="节点标签" />
                <!-- agent 节点 -->
                <template v-if="node.type === 'agent'">
                  <n-select
                    v-model:value="node.config.agent_id"
                    :options="agentOptions"
                    size="small"
                    placeholder="选择智能体"
                  />
                </template>
                <!-- tool 节点 -->
                <template v-else-if="node.type === 'tool'">
                  <n-select
                    v-model:value="node.config.tool_id"
                    :options="toolOptions"
                    size="small"
                    placeholder="选择工具"
                  />
                </template>
                <!-- knowledge 节点 -->
                <template v-else-if="node.type === 'knowledge'">
                  <n-select
                    v-model:value="node.config.knowledge_base_id"
                    :options="kbOptions"
                    size="small"
                    placeholder="选择知识库"
                  />
                  <n-input-number
                    v-model:value="node.config.top_k"
                    :min="1"
                    :max="20"
                    size="small"
                    placeholder="top_k"
                    style="width: 100%"
                  />
                </template>
                <!-- condition 节点 -->
                <template v-else-if="node.type === 'condition'">
                  <div class="condition-rules">
                    <div v-for="(rule, rIdx) in node.config.rules" :key="rIdx" class="rule-row">
                      <n-input
                        v-model:value="rule.keyword"
                        size="small"
                        placeholder="关键词"
                        style="flex: 1"
                      />
                      <n-select
                        v-model:value="rule.target"
                        :options="nodeTargetOptions(node.id)"
                        size="small"
                        placeholder="目标节点"
                        style="flex: 1"
                      />
                      <n-button size="tiny" type="error" secondary @click="removeRule(node, rIdx)">×</n-button>
                    </div>
                    <n-button size="tiny" dashed block @click="addRule(node)">+ 添加条件规则</n-button>
                  </div>
                </template>
              </n-space>
            </div>
            <n-button dashed block @click="addNode">+ 添加节点</n-button>
          </div>
        </n-form-item>

        <!-- 连线编辑器 -->
        <n-form-item label="连线">
          <div class="editor-block">
            <div v-for="(edge, idx) in form.edges" :key="idx" class="edge-row">
              <n-select
                v-model:value="edge.source"
                :options="nodeOptions"
                size="small"
                placeholder="源节点"
                style="flex: 1"
              />
              <span class="edge-arrow">→</span>
              <n-select
                v-model:value="edge.target"
                :options="nodeOptions"
                size="small"
                placeholder="目标节点"
                style="flex: 1"
              />
              <n-button size="tiny" type="error" secondary @click="removeEdge(idx)">×</n-button>
            </div>
            <n-button dashed block @click="addEdge">+ 添加连线</n-button>
          </div>
        </n-form-item>

        <div class="form-actions">
          <n-button type="primary" block :loading="saving" @click="submitWorkflow">
            {{ editingId ? '保存修改' : '创建工作流' }}
          </n-button>
        </div>
      </n-form>
    </n-modal>

    <!-- 执行工作流弹窗 -->
    <n-modal v-model:show="showRunner" preset="card" title="执行工作流" style="max-width: 800px">
      <n-form label-placement="top">
        <n-form-item label="用户问题" required>
          <n-input
            v-model:value="runInput"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="请输入要交给工作流处理的问题"
          />
        </n-form-item>
        <n-button type="primary" block :loading="running" @click="runWorkflow">执行工作流</n-button>
      </n-form>

      <template v-if="runResult">
        <n-divider>执行结果</n-divider>
        <div class="run-output">
          <div class="run-output-label">输出：</div>
          <div class="run-output-text">{{ runResult.output || '（无输出）' }}</div>
        </div>
        <n-divider v-if="runResult.steps?.length">节点执行明细</n-divider>
        <n-list v-if="runResult.steps?.length" bordered>
          <n-list-item v-for="step in runResult.steps" :key="step.node_id">
            <n-thing>
              <template #header>
                <n-space align="center" size="small">
                  <span>{{ step.node_label || step.node_id }}</span>
                  <n-tag :type="step.status === 'success' ? 'success' : 'error'" size="small">
                    {{ statusLabel(step.status) }}
                  </n-tag>
                  <n-tag size="small">{{ step.duration_ms != null ? `${step.duration_ms}ms` : '-' }}</n-tag>
                </n-space>
              </template>
              <div class="step-output">{{ step.output || '（无输出）' }}</div>
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

// 工作流相关类型定义
type NodeType = "start" | "agent" | "tool" | "knowledge" | "condition" | "end";

interface ConditionRule {
  keyword: string;
  target: string;
}
interface WorkflowNode {
  id: string;
  type: NodeType;
  label: string;
  config: {
    agent_id?: string | null;
    tool_id?: string | null;
    knowledge_base_id?: string | null;
    top_k?: number | null;
    rules?: ConditionRule[];
  };
}
interface WorkflowEdge {
  source: string;
  target: string;
}
interface Workflow {
  id: string;
  name: string;
  description: string;
  status: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created_at: string;
}
interface RunStep {
  node_id: string;
  node_label?: string;
  status: string;
  output: string;
  duration_ms: number | null;
}
interface RunResult {
  output: string;
  steps: RunStep[];
}

// 列表数据
const workflows = ref<Workflow[]>([]);
const loading = ref(false);

// 选项数据
const agents = ref<Array<{ id: string; name: string }>>([]);
const tools = ref<Array<{ id: string; name: string }>>([]);
const knowledgeBases = ref<Array<{ id: string; name: string }>>([]);

// 编辑弹窗状态
const showEditor = ref(false);
const saving = ref(false);
const editingId = ref<string | null>(null);
const form = reactive({
  name: "",
  description: "",
  nodes: [] as WorkflowNode[],
  edges: [] as WorkflowEdge[]
});

// 执行弹窗状态
const showRunner = ref(false);
const running = ref(false);
const runInput = ref("");
const runningWorkflowId = ref<string | null>(null);
const runResult = ref<RunResult | null>(null);

const nodeTypeOptions = [
  { label: "开始 (start)", value: "start" },
  { label: "智能体 (agent)", value: "agent" },
  { label: "工具 (tool)", value: "tool" },
  { label: "知识库 (knowledge)", value: "knowledge" },
  { label: "条件 (condition)", value: "condition" },
  { label: "结束 (end)", value: "end" }
];

const agentOptions = computed(() =>
  agents.value.map((a) => ({ label: a.name, value: a.id }))
);
const toolOptions = computed(() =>
  tools.value.map((t) => ({ label: t.name, value: t.id }))
);
const kbOptions = computed(() =>
  knowledgeBases.value.map((k) => ({ label: k.name, value: k.id }))
);
const nodeOptions = computed(() =>
  form.nodes.map((n) => ({ label: `${n.id} - ${n.label || n.type}`, value: n.id }))
);

function nodeTargetOptions(excludeId: string) {
  return form.nodes.filter((n) => n.id !== excludeId).map((n) => ({
    label: `${n.id} - ${n.label || n.type}`,
    value: n.id
  }));
}

function nodeTypeLabel(type: NodeType) {
  const map: Record<NodeType, string> = {
    start: "开始",
    agent: "智能体",
    tool: "工具",
    knowledge: "知识库",
    condition: "条件",
    end: "结束"
  };
  return map[type] ?? type;
}

function nodeTagType(type: NodeType) {
  const map: Record<NodeType, "default" | "success" | "info" | "warning" | "error"> = {
    start: "success",
    agent: "info",
    tool: "info",
    knowledge: "info",
    condition: "warning",
    end: "error"
  };
  return map[type] ?? "default";
}

function statusTagType(status: string) {
  if (status === "published" || status === "active") return "success";
  if (status === "running") return "info";
  if (status === "failed") return "error";
  if (status === "draft") return "default";
  return "default";
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    published: "已发布",
    active: "已发布",
    draft: "草稿",
    running: "运行中",
    success: "成功",
    failed: "失败",
    pending: "等待中"
  };
  return map[status] ?? status;
}

function formatTime(t: string) {
  if (!t) return "-";
  try {
    return new Date(t).toLocaleString("zh-CN");
  } catch {
    return t;
  }
}

function nextNodeId() {
  const nums = form.nodes
    .map((n) => parseInt(n.id.replace("node-", ""), 10))
    .filter((n) => !Number.isNaN(n));
  const max = nums.length ? Math.max(...nums) : 0;
  return `node-${max + 1}`;
}

function emptyConfig(type: NodeType): WorkflowNode["config"] {
  switch (type) {
    case "agent":
      return { agent_id: null };
    case "tool":
      return { tool_id: null };
    case "knowledge":
      return { knowledge_base_id: null, top_k: 5 };
    case "condition":
      return { rules: [{ keyword: "", target: "" }] };
    default:
      return {};
  }
}

function addNode() {
  const id = nextNodeId();
  form.nodes.push({
    id,
    type: "agent",
    label: "",
    config: emptyConfig("agent")
  });
}

function removeNode(idx: number) {
  const removedId = form.nodes[idx].id;
  form.nodes.splice(idx, 1);
  // 清理涉及该节点的连线
  form.edges = form.edges.filter((e) => e.source !== removedId && e.target !== removedId);
}

function addRule(node: WorkflowNode) {
  if (!node.config.rules) node.config.rules = [];
  node.config.rules.push({ keyword: "", target: "" });
}

function removeRule(node: WorkflowNode, idx: number) {
  node.config.rules?.splice(idx, 1);
}

function addEdge() {
  form.edges.push({ source: "", target: "" });
}

function removeEdge(idx: number) {
  form.edges.splice(idx, 1);
}

async function loadWorkflows() {
  loading.value = true;
  try {
    const res = await api.get<Workflow[]>("/workflows");
    workflows.value = res.data;
  } catch (e: any) {
    message.error(e?.message || "加载工作流列表失败");
  } finally {
    loading.value = false;
  }
}

async function loadOptions() {
  try {
    const [a, t, k] = await Promise.all([
      api.get<Array<{ id: string; name: string }>>("/agents").catch(() => ({ data: [] })),
      api.get<Array<{ id: string; name: string }>>("/tools").catch(() => ({ data: [] })),
      api.get<Array<{ id: string; name: string }>>("/knowledge-bases").catch(() => ({ data: [] }))
    ]);
    agents.value = a.data;
    tools.value = t.data;
    knowledgeBases.value = k.data;
  } catch {
    // 单独失败已在上层 catch 兜底
  }
}

function openCreateModal() {
  editingId.value = null;
  form.name = "";
  form.description = "";
  form.nodes = [
    { id: "node-1", type: "start", label: "开始", config: {} },
    { id: "node-2", type: "end", label: "结束", config: {} }
  ];
  form.edges = [{ source: "node-1", target: "node-2" }];
  showEditor.value = true;
}

async function openEditModal(wf: Workflow) {
  editingId.value = wf.id;
  try {
    const res = await api.get<Workflow>(`/workflows/${wf.id}`);
    const detail = res.data;
    form.name = detail.name;
    form.description = detail.description;
    form.nodes = (detail.nodes ?? []).map((n) => ({
      id: n.id,
      type: n.type,
      label: n.label ?? "",
      config: { ...emptyConfig(n.type), ...n.config }
    }));
    form.edges = (detail.edges ?? []).map((e) => ({ source: e.source, target: e.target }));
    showEditor.value = true;
  } catch (e: any) {
    message.error(e?.message || "加载工作流详情失败");
  }
}

function validateForm(): string | null {
  if (!form.name.trim()) return "请填写工作流名称";
  if (!form.nodes.length) return "至少需要 1 个节点";
  for (const n of form.nodes) {
    if (!n.label.trim()) return `节点 ${n.id} 缺少标签`;
    if (n.type === "agent" && !n.config.agent_id) return `节点 ${n.id} 需选择智能体`;
    if (n.type === "tool" && !n.config.tool_id) return `节点 ${n.id} 需选择工具`;
    if (n.type === "knowledge" && !n.config.knowledge_base_id) return `节点 ${n.id} 需选择知识库`;
  }
  for (const e of form.edges) {
    if (!e.source || !e.target) return "每条连线需指定源节点和目标节点";
  }
  return null;
}

async function submitWorkflow() {
  const err = validateForm();
  if (err) {
    message.warning(err);
    return;
  }
  saving.value = true;
  const payload = {
    name: form.name.trim(),
    description: form.description.trim(),
    nodes: form.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      label: n.label.trim(),
      config: cleanConfig(n)
    })),
    edges: form.edges.map((e) => ({ source: e.source, target: e.target }))
  };
  try {
    if (editingId.value) {
      await api.put(`/workflows/${editingId.value}`, payload);
      message.success("工作流已更新");
    } else {
      await api.post("/workflows", payload);
      message.success("工作流已创建");
    }
    showEditor.value = false;
    await loadWorkflows();
  } catch (e: any) {
    message.error(e?.message || "保存工作流失败");
  } finally {
    saving.value = false;
  }
}

function cleanConfig(node: WorkflowNode) {
  const cfg: Record<string, unknown> = {};
  const c = node.config;
  if (node.type === "agent" && c.agent_id) cfg.agent_id = c.agent_id;
  if (node.type === "tool" && c.tool_id) cfg.tool_id = c.tool_id;
  if (node.type === "knowledge") {
    if (c.knowledge_base_id) cfg.knowledge_base_id = c.knowledge_base_id;
    if (c.top_k != null) cfg.top_k = c.top_k;
  }
  if (node.type === "condition" && c.rules) {
    cfg.rules = c.rules.filter((r) => r.keyword.trim() && r.target);
  }
  return cfg;
}

function confirmDelete(wf: Workflow) {
  dialog.warning({
    title: "删除工作流",
    content: `确认删除工作流「${wf.name}」吗？此操作不可恢复。`,
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await api.delete(`/workflows/${wf.id}`);
        message.success("工作流已删除");
        await loadWorkflows();
      } catch (e: any) {
        message.error(e?.message || "删除工作流失败");
      }
    }
  });
}

function openRunModal(wf: Workflow) {
  runningWorkflowId.value = wf.id;
  runInput.value = "";
  runResult.value = null;
  showRunner.value = true;
}

async function runWorkflow() {
  if (!runningWorkflowId.value) return;
  if (!runInput.value.trim()) {
    message.warning("请输入用户问题");
    return;
  }
  running.value = true;
  runResult.value = null;
  try {
    const res = await api.post<RunResult>("/workflows/run", {
      workflow_id: runningWorkflowId.value,
      input: runInput.value.trim()
    });
    runResult.value = res.data;
    message.success("工作流执行完成");
  } catch (e: any) {
    message.error(e?.message || "执行工作流失败");
  } finally {
    running.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadWorkflows(), loadOptions()]);
});
</script>

<style scoped>
.wf-desc {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.editor-block {
  width: 100%;
  display: grid;
  gap: 12px;
}

.node-item {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-soft);
  display: grid;
  gap: 8px;
}

.node-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.node-index {
  font-weight: 600;
  color: var(--text-strong);
  font-size: 13px;
}

.condition-rules {
  display: grid;
  gap: 6px;
}

.rule-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.edge-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edge-arrow {
  color: var(--text-muted);
  font-size: 14px;
  flex-shrink: 0;
}

.form-actions {
  margin-top: 8px;
}

.run-output {
  display: grid;
  gap: 6px;
}

.run-output-label {
  color: var(--text-muted);
  font-size: 13px;
}

.run-output-text {
  white-space: pre-wrap;
  word-break: break-word;
  padding: 8px;
  background: var(--surface-soft);
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
}

.step-output {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  padding: 8px;
  background: var(--surface-soft);
  border-radius: 4px;
}
</style>
