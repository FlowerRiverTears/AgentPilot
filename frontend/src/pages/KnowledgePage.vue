<template>
  <div class="page-grid">
    <div class="two-column">
      <n-card title="创建知识库">
        <n-form label-placement="top">
          <n-form-item label="名称" :feedback="nameFeedback" :validation-status="nameStatus">
            <n-input v-model:value="form.name" placeholder="产品文档库" @keyup.enter="submit" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input v-model:value="form.description" placeholder="产品、售后和政策资料" />
          </n-form-item>
          <n-button type="primary" block :loading="creating" @click="submit">创建知识库</n-button>
        </n-form>
      </n-card>
      <n-card title="知识库列表">
        <n-alert v-if="selectedKnowledgeBase" type="success" class="selected-kb-tip">
          当前已选择：{{ selectedKnowledgeBase.name }}
        </n-alert>
        <n-data-table
          :columns="columns"
          :data="store.knowledgeBases"
          :bordered="false"
          :row-key="rowKey"
          :row-props="rowProps"
          @update:checked-row-keys="onChecked"
        />
      </n-card>
    </div>

    <div class="two-column">
      <n-card title="导入文档">
        <n-alert type="info" class="selected-kb-tip">
          可以直接选择内置标准文档导入知识库，也可以上传自己的 PDF、Markdown 或文本文件。
        </n-alert>
        <n-form label-placement="top">
          <n-form-item label="知识库">
            <n-select v-model:value="selectedKbId" :options="kbOptions" placeholder="选择知识库" />
          </n-form-item>
          <n-form-item label="示例文档">
            <n-select
              v-model:value="selectedSampleDocumentId"
              :options="sampleDocumentOptions"
              placeholder="选择一份内置示例文档"
            />
          </n-form-item>
          <n-button
            type="primary"
            block
            :loading="importingSample"
            @click="importSample"
          >
            导入示例文档
          </n-button>
          <n-divider>或上传本地文档</n-divider>
          <n-upload :max="1" :default-upload="false" @change="onFileChange">
            <n-button>选择文档</n-button>
          </n-upload>
          <n-button
            class="action-button"
            type="primary"
            block
            :loading="uploading"
            @click="upload"
          >
            上传并切块
          </n-button>
        </n-form>
      </n-card>

      <n-card title="检索测试">
        <n-form label-placement="top">
          <n-form-item label="问题">
            <n-input
              v-model:value="query"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              placeholder="输入要检索的问题"
            />
          </n-form-item>
          <n-button type="primary" block :loading="retrieving" @click="retrieve">文本检索</n-button>
          <n-divider>或上传图片检索（跨模态）</n-divider>
          <n-upload :max="1" :default-upload="false" accept="image/*" @change="onImageChange">
            <n-button>选择图片</n-button>
          </n-upload>
          <n-button
            class="action-button"
            type="primary"
            block
            :loading="retrievingByImage"
            @click="retrieveByImage"
          >
            图片检索
          </n-button>
        </n-form>
      </n-card>
    </div>

    <n-card title="检索结果">
      <div v-if="retrieved.length" class="retrieval-list">
        <n-card v-for="(chunk, index) in retrieved" :key="chunk.chunk_id" size="small" class="retrieval-item">
          <div class="retrieval-head">
            <div>
              <div class="retrieval-title">#{{ index + 1 }} {{ chunk.source }}</div>
              <div class="muted">相似度：{{ chunk.score.toFixed(3) }}</div>
            </div>
            <n-tag :type="chunk.content_type === 'image' ? 'warning' : 'info'" size="small">
              {{ chunk.content_type === 'image' ? '图片' : '切片' }}
            </n-tag>
          </div>
          <div v-if="chunk.content_type === 'image' && chunk.image_url" class="retrieval-image">
            <img :src="minioImageUrl(chunk.image_url)" :alt="chunk.content" class="retrieved-img" />
            <div class="muted">{{ chunk.content }}</div>
          </div>
          <div v-else class="retrieval-snippet">
            {{ snippet(chunk.content) }}
          </div>
          <n-collapse v-if="chunk.content_type !== 'image'">
            <n-collapse-item title="查看原文" name="raw">
              <pre class="retrieval-raw">{{ chunk.content }}</pre>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </div>
      <n-empty v-else description="暂无检索结果" />
    </n-card>

    <n-modal v-model:show="showDocuments" preset="card" title="文档管理" style="max-width: 700px">
      <n-data-table
        :columns="documentColumns"
        :data="documents"
        :bordered="false"
        :loading="loadingDocuments"
      />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from "vue";
import { NButton, NSpace, useDialog, useMessage, type DataTableColumns, type UploadFileInfo } from "naive-ui";

import type { KnowledgeBase, RetrievedChunk } from "../api/types";
import { api } from "../api/client";
import { useWorkspaceStore } from "../stores/workspace";

const message = useMessage();
const dialog = useDialog();
const store = useWorkspaceStore();

const form = reactive({ name: "", description: "" });
const creating = ref(false);
const uploading = ref(false);
const importingSample = ref(false);
const retrieving = ref(false);
const retrievingByImage = ref(false);
const selectedImageFile = ref<File | null>(null);
const selectedKbId = ref<string | null>(null);
const selectedSampleDocumentId = ref<string | null>(null);
const selectedFile = ref<File | null>(null);
const query = ref("");
const retrieved = ref<RetrievedChunk[]>([]);
const triedSubmit = ref(false);
const showDocuments = ref(false);
const documents = ref<any[]>([]);
const loadingDocuments = ref(false);

const documentColumns: DataTableColumns<any> = [
  { title: "文件名", key: "filename" },
  { title: "切片数", key: "chunk_count" },
  {
    title: "创建时间",
    key: "created_at",
    render(row) {
      try { return new Date(row.created_at).toLocaleString("zh-CN"); } catch { return row.created_at; }
    }
  },
  {
    title: "操作",
    key: "actions",
    render(row) {
      return h(
        NButton,
        { size: "small", type: "error", secondary: true, onClick: () => confirmDeleteDocument(row) },
        { default: () => "删除" }
      );
    }
  }
];

const kbOptions = computed(() =>
  store.knowledgeBases.map((item) => ({ label: item.name, value: item.id }))
);

const selectedKnowledgeBase = computed(() =>
  store.knowledgeBases.find((item) => item.id === selectedKbId.value)
);

const sampleDocumentOptions = computed(() =>
  store.sampleDocuments.map((item) => ({
    label: `${item.title}（${item.filename}）`,
    value: item.id
  }))
);

const nameStatus = computed(() => {
  if (!triedSubmit.value || form.name.trim()) {
    return undefined;
  }
  return "error";
});

const nameFeedback = computed(() => {
  if (!triedSubmit.value || form.name.trim()) {
    return "";
  }
  return "知识库名称不能为空";
});

const columns: DataTableColumns<KnowledgeBase> = [
  { type: "selection" },
  { title: "名称", key: "name" },
  { title: "描述", key: "description" },
  { title: "文档数", key: "document_count" },
  {
    title: "操作",
    key: "actions",
    render(row) {
      return h(
        NSpace,
        { size: 8 },
        {
          default: () => [
            h(
              NButton,
              {
                size: "small",
                type: row.id === selectedKbId.value ? "primary" : "default",
                onClick: () => {
                  selectKnowledgeBase(row);
                }
              },
              { default: () => (row.id === selectedKbId.value ? "已选择" : "选择") }
            ),
            h(
              NButton,
              {
                size: "small",
                secondary: true,
                onClick: () => openDocuments(row)
              },
              { default: () => "文档" }
            ),
            h(
              NButton,
              {
                size: "small",
                type: "error",
                secondary: true,
                onClick: () => confirmDelete(row)
              },
              { default: () => "删除" }
            )
          ]
        }
      );
    }
  }
];

function rowKey(row: KnowledgeBase) {
  return row.id;
}

function selectKnowledgeBase(row: KnowledgeBase) {
  selectedKbId.value = row.id;
  message.info(`已选择：${row.name}`);
}

function rowProps(row: KnowledgeBase) {
  return {
    class: row.id === selectedKbId.value ? "selected-row" : "",
    style: "cursor: pointer;",
    onClick: () => selectKnowledgeBase(row)
  };
}

function onChecked(keys: Array<string | number>) {
  selectedKbId.value = keys.length ? String(keys[0]) : null;
}

function onFileChange(options: { fileList: UploadFileInfo[] }) {
  selectedFile.value = (options.fileList[0]?.file as File | undefined) ?? null;
}

function onImageChange(options: { fileList: UploadFileInfo[] }) {
  selectedImageFile.value = (options.fileList[0]?.file as File | undefined) ?? null;
}

function snippet(text: string, limit = 220) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit)}...`;
}

function minioImageUrl(path: string) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base = window.location.port === "5173" ? "http://localhost:19000" : "http://localhost:9000";
  return `${base}${path}`;
}

async function submit() {
  triedSubmit.value = true;
  const name = form.name.trim();
  if (!name) {
    message.warning("请先填写知识库名称");
    return;
  }

  creating.value = true;
  try {
    const created = await store.createKnowledgeBase({
      name,
      description: form.description.trim()
    });
    selectedKbId.value = created.id;
    message.success("知识库已创建");
    form.name = "";
    form.description = "";
    triedSubmit.value = false;
  } catch (error) {
    message.error("创建失败，请检查后端服务或输入内容");
    console.error(error);
  } finally {
    creating.value = false;
  }
}

async function upload() {
  if (!selectedKbId.value) {
    message.warning("请先选择知识库");
    return;
  }
  if (!selectedFile.value) {
    message.warning("请先选择文件");
    return;
  }

  uploading.value = true;
  try {
    const chunks = await store.uploadKnowledgeDocument(selectedKbId.value, selectedFile.value);
    message.success(`上传成功，生成 ${chunks.length} 个切片`);
  } catch (error) {
    message.error("上传失败，请确认文件内容可读取");
    console.error(error);
  } finally {
    uploading.value = false;
  }
}

async function importSample() {
  if (!selectedKbId.value) {
    message.warning("请先选择知识库");
    return;
  }
  if (!selectedSampleDocumentId.value) {
    message.warning("请先选择示例文档");
    return;
  }

  importingSample.value = true;
  try {
    const chunks = await store.importSampleDocument(selectedKbId.value, selectedSampleDocumentId.value);
    message.success(`导入成功，生成 ${chunks.length} 个切片`);
  } catch (error) {
    message.error("导入失败，请检查后端服务");
    console.error(error);
  } finally {
    importingSample.value = false;
  }
}

async function retrieve() {
  if (!selectedKbId.value) {
    message.warning("请先选择知识库");
    return;
  }
  if (!query.value.trim()) {
    message.warning("请输入检索问题");
    return;
  }

  retrieving.value = true;
  try {
    retrieved.value = await store.retrieveKnowledge(selectedKbId.value, query.value.trim());
    if (!retrieved.value.length) {
      message.info("没有检索到内容，请先上传文档");
    }
  } catch (error) {
    message.error("检索失败");
    console.error(error);
  } finally {
    retrieving.value = false;
  }
}

async function retrieveByImage() {
  if (!selectedKbId.value) {
    message.warning("请先选择知识库");
    return;
  }
  if (!selectedImageFile.value) {
    message.warning("请先选择图片");
    return;
  }

  retrievingByImage.value = true;
  try {
    const formData = new FormData();
    formData.append("file", selectedImageFile.value);
    const response = await api.post<RetrievedChunk[]>(
      `/knowledge-bases/${selectedKbId.value}/retrieve-by-image`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    retrieved.value = response.data;
    if (!retrieved.value.length) {
      message.info("没有检索到内容，请先上传含图片的文档");
    }
  } catch (error) {
    message.error("图片检索失败，请确认已配置多模态 Embedding 服务");
    console.error(error);
  } finally {
    retrievingByImage.value = false;
  }
}

function confirmDelete(row: KnowledgeBase) {
  dialog.warning({
    title: "删除知识库",
    content: `确认删除「${row.name}」吗？删除后该知识库的文档切片和检索结果也会被清除。`,
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await store.deleteKnowledgeBase(row.id);
      if (selectedKbId.value === row.id) {
        selectedKbId.value = store.knowledgeBases[0]?.id ?? null;
      }
      retrieved.value = [];
      message.success("知识库已删除");
    }
  });
}

async function openDocuments(kb: KnowledgeBase) {
  showDocuments.value = true;
  loadingDocuments.value = true;
  try {
    const response = await api.get(`/knowledge-bases/${kb.id}/documents`);
    documents.value = response.data;
  } catch {
    message.error("加载文档列表失败");
  } finally {
    loadingDocuments.value = false;
  }
}

function confirmDeleteDocument(doc: any) {
  dialog.warning({
    title: "删除文档",
    content: `确认删除「${doc.filename}」吗？该文档的所有切片将被清除。`,
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        const currentKbId = selectedKbId.value;
        await api.delete(`/knowledge-bases/${currentKbId}/documents/${doc.id}`);
        message.success("文档已删除");
        documents.value = documents.value.filter((d: any) => d.id !== doc.id);
        await store.loadKnowledgeBases();
      } catch {
        message.error("删除文档失败");
      }
    }
  });
}

onMounted(async () => {
  await Promise.all([store.loadKnowledgeBases(), store.loadSampleDocuments()]);
  selectedKbId.value = store.knowledgeBases[0]?.id ?? null;
  selectedSampleDocumentId.value = store.sampleDocuments[0]?.id ?? null;
});
</script>

<style scoped>
.action-button {
  margin-top: 16px;
}

.selected-kb-tip {
  margin-bottom: 12px;
}

:deep(.selected-row td) {
  background: #eef6ff;
}

.retrieval-image {
  margin-top: 8px;
}

.retrieved-img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 6px;
  object-fit: contain;
  margin-bottom: 8px;
}
</style>
