<template>
  <div class="page-grid">
    <div class="two-column">
      <n-card :title="t('knowledge.createKB')">
        <n-form label-placement="top">
          <n-form-item :label="t('common.name')" :feedback="nameFeedback" :validation-status="nameStatus">
            <n-input v-model:value="form.name" :placeholder="t('knowledge.kbNamePlaceholder')" @keyup.enter="submit" />
          </n-form-item>
          <n-form-item :label="t('common.description')">
            <n-input v-model:value="form.description" :placeholder="t('knowledge.kbDescPlaceholder')" />
          </n-form-item>
          <n-button type="primary" block :loading="creating" @click="submit">{{ t('knowledge.createKB') }}</n-button>
        </n-form>
      </n-card>
      <n-card :title="t('knowledge.kbList')">
        <n-alert v-if="selectedKnowledgeBase" type="success" class="selected-kb-tip">
          {{ t('knowledge.currentSelected') }}{{ selectedKnowledgeBase.name }}
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
      <n-card :title="t('knowledge.importDocs')">
        <n-alert type="info" class="selected-kb-tip">
          {{ t('knowledge.importDocsHint') }}
        </n-alert>
        <n-form label-placement="top">
          <n-form-item :label="t('knowledge.knowledgeBase')">
            <n-select v-model:value="selectedKbId" :options="kbOptions" :placeholder="t('knowledge.selectKB')" />
          </n-form-item>
          <n-form-item :label="t('knowledge.sampleDocument')">
            <n-select
              v-model:value="selectedSampleDocumentId"
              :options="sampleDocumentOptions"
              :placeholder="t('knowledge.selectSampleDoc')"
            />
          </n-form-item>
          <n-button
            type="primary"
            block
            :loading="importingSample"
            @click="importSample"
          >
            {{ t('knowledge.importSampleDoc') }}
          </n-button>
          <n-divider>{{ t('knowledge.orUploadLocal') }}</n-divider>
          <n-upload :max="1" :default-upload="false" @change="onFileChange">
            <n-button>{{ t('knowledge.selectDoc') }}</n-button>
          </n-upload>
          <n-button
            class="action-button"
            type="primary"
            block
            :loading="uploading"
            @click="upload"
          >
            {{ t('knowledge.uploadAndChunk') }}
          </n-button>
        </n-form>
      </n-card>

      <n-card :title="t('knowledge.retrievalTest')">
        <n-form label-placement="top">
          <n-form-item :label="t('knowledge.question')">
            <n-input
              v-model:value="query"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              :placeholder="t('knowledge.enterQuery')"
            />
          </n-form-item>
          <n-button type="primary" block :loading="retrieving" @click="retrieve">{{ t('knowledge.textRetrieval') }}</n-button>
          <n-divider>{{ t('knowledge.orUploadImage') }}</n-divider>
          <n-upload :max="1" :default-upload="false" accept="image/*" @change="onImageChange">
            <n-button>{{ t('knowledge.selectImage') }}</n-button>
          </n-upload>
          <n-button
            class="action-button"
            type="primary"
            block
            :loading="retrievingByImage"
            @click="retrieveByImage"
          >
            {{ t('knowledge.imageRetrieval') }}
          </n-button>
        </n-form>
      </n-card>
    </div>

    <n-card :title="t('knowledge.retrievalResults')">
      <div v-if="retrieved.length" class="retrieval-list">
        <n-card v-for="(chunk, index) in retrieved" :key="chunk.chunk_id" size="small" class="retrieval-item">
          <div class="retrieval-head">
            <div>
              <div class="retrieval-title">#{{ index + 1 }} {{ chunk.source }}</div>
              <div class="muted">{{ t('knowledge.similarity') }}{{ chunk.score.toFixed(3) }}</div>
            </div>
            <n-tag :type="chunk.content_type === 'image' ? 'warning' : 'info'" size="small">
              {{ chunk.content_type === 'image' ? t('knowledge.image') : t('knowledge.chunk') }}
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
            <n-collapse-item :title="t('knowledge.viewOriginal')" name="raw">
              <pre class="retrieval-raw">{{ chunk.content }}</pre>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </div>
      <n-empty v-else :description="t('knowledge.noResults')" />
    </n-card>

    <n-modal v-model:show="showDocuments" preset="card" :title="t('knowledge.docManagement')" style="max-width: 700px">
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
import { useI18n } from "vue-i18n";

import type { KnowledgeBase, RetrievedChunk } from "../api/types";
import { api } from "../api/client";
import { useWorkspaceStore } from "../stores/workspace";
import { useUiStore } from "../stores/ui";

const { t } = useI18n();
const message = useMessage();
const dialog = useDialog();
const store = useWorkspaceStore();
const ui = useUiStore();

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
  { title: t('knowledge.filename'), key: "filename" },
  { title: t('knowledge.chunkCount'), key: "chunk_count" },
  {
    title: t('knowledge.createdAt'),
    key: "created_at",
    render(row) {
      try { return new Date(row.created_at).toLocaleString(ui.locale === 'zh' ? 'zh-CN' : 'en-US'); } catch { return row.created_at; }
    }
  },
  {
    title: t('common.actions'),
    key: "actions",
    render(row) {
      return h(
        NButton,
        { size: "small", type: "error", secondary: true, onClick: () => confirmDeleteDocument(row) },
        { default: () => t('common.delete') }
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
  return t('knowledge.kbNameRequired');
});

const columns: DataTableColumns<KnowledgeBase> = [
  { type: "selection" },
  { title: t('common.name'), key: "name" },
  { title: t('common.description'), key: "description" },
  { title: t('knowledge.docCount'), key: "document_count" },
  {
    title: t('common.actions'),
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
              { default: () => (row.id === selectedKbId.value ? t('knowledge.selected') : t('knowledge.select')) }
            ),
            h(
              NButton,
              {
                size: "small",
                secondary: true,
                onClick: () => openDocuments(row)
              },
              { default: () => t('knowledge.documents') }
            ),
            h(
              NButton,
              {
                size: "small",
                type: "error",
                secondary: true,
                onClick: () => confirmDelete(row)
              },
              { default: () => t('common.delete') }
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
  message.info(`${t('knowledge.selected')}${row.name}`);
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
    message.warning(t('knowledge.fillKBName'));
    return;
  }

  creating.value = true;
  try {
    const created = await store.createKnowledgeBase({
      name,
      description: form.description.trim()
    });
    selectedKbId.value = created.id;
    message.success(t('knowledge.kbCreated'));
    form.name = "";
    form.description = "";
    triedSubmit.value = false;
  } catch (error) {
    message.error(t('knowledge.createFailed'));
    console.error(error);
  } finally {
    creating.value = false;
  }
}

async function upload() {
  if (!selectedKbId.value) {
    message.warning(t('knowledge.selectKBFirst'));
    return;
  }
  if (!selectedFile.value) {
    message.warning(t('knowledge.selectFileFirst'));
    return;
  }

  uploading.value = true;
  try {
    const chunks = await store.uploadKnowledgeDocument(selectedKbId.value, selectedFile.value);
    message.success(t('knowledge.uploadSuccess', { count: chunks.length }));
  } catch (error) {
    message.error(t('knowledge.uploadFailed'));
    console.error(error);
  } finally {
    uploading.value = false;
  }
}

async function importSample() {
  if (!selectedKbId.value) {
    message.warning(t('knowledge.selectKBFirst'));
    return;
  }
  if (!selectedSampleDocumentId.value) {
    message.warning(t('knowledge.selectSampleDocFirst'));
    return;
  }

  importingSample.value = true;
  try {
    const chunks = await store.importSampleDocument(selectedKbId.value, selectedSampleDocumentId.value);
    message.success(t('knowledge.importSampleSuccess', { count: chunks.length }));
  } catch (error) {
    message.error(t('knowledge.importSampleFailed'));
    console.error(error);
  } finally {
    importingSample.value = false;
  }
}

async function retrieve() {
  if (!selectedKbId.value) {
    message.warning(t('knowledge.selectKBFirst'));
    return;
  }
  if (!query.value.trim()) {
    message.warning(t('knowledge.enterQueryFirst'));
    return;
  }

  retrieving.value = true;
  try {
    retrieved.value = await store.retrieveKnowledge(selectedKbId.value, query.value.trim());
    if (!retrieved.value.length) {
      message.info(t('knowledge.noContentRetrieved'));
    }
  } catch (error) {
    message.error(t('knowledge.retrievalFailed'));
    console.error(error);
  } finally {
    retrieving.value = false;
  }
}

async function retrieveByImage() {
  if (!selectedKbId.value) {
    message.warning(t('knowledge.selectKBFirst'));
    return;
  }
  if (!selectedImageFile.value) {
    message.warning(t('knowledge.selectImageFirst'));
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
      message.info(t('knowledge.noImageContentRetrieved'));
    }
  } catch (error) {
    message.error(t('knowledge.imageRetrievalFailed'));
    console.error(error);
  } finally {
    retrievingByImage.value = false;
  }
}

function confirmDelete(row: KnowledgeBase) {
  dialog.warning({
    title: t('knowledge.deleteKB'),
    content: t('knowledge.confirmDeleteKB', { name: row.name }),
    positiveText: t('knowledge.confirmDeleteBtn'),
    negativeText: t('common.cancel'),
    onPositiveClick: async () => {
      await store.deleteKnowledgeBase(row.id);
      if (selectedKbId.value === row.id) {
        selectedKbId.value = store.knowledgeBases[0]?.id ?? null;
      }
      retrieved.value = [];
      message.success(t('knowledge.kbDeleted'));
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
    message.error(t('knowledge.loadDocsFailed'));
  } finally {
    loadingDocuments.value = false;
  }
}

function confirmDeleteDocument(doc: any) {
  dialog.warning({
    title: t('knowledge.deleteDoc'),
    content: t('knowledge.confirmDeleteDoc', { filename: doc.filename }),
    positiveText: t('knowledge.confirmDeleteBtn'),
    negativeText: t('common.cancel'),
    onPositiveClick: async () => {
      try {
        const currentKbId = selectedKbId.value;
        await api.delete(`/knowledge-bases/${currentKbId}/documents/${doc.id}`);
        message.success(t('knowledge.docDeleted'));
        documents.value = documents.value.filter((d: any) => d.id !== doc.id);
        await store.loadKnowledgeBases();
      } catch {
        message.error(t('knowledge.deleteDocFailed'));
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
