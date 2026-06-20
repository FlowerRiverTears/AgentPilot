<template>
  <div class="mermaid-block">
    <div v-if="error" class="mermaid-error">
      <n-alert type="warning" title="图表渲染失败" :show-icon="true">
        <pre class="mermaid-source">{{ source }}</pre>
      </n-alert>
    </div>
    <div v-else class="mermaid-render" v-html="svg" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useUiStore } from "../stores/ui";

const props = defineProps<{ source: string }>();

const ui = useUiStore();
const svg = ref("");
const error = ref(false);

let mermaidInstance: any = null;

async function loadMermaid() {
  if (!mermaidInstance) {
    const mermaid = await import("mermaid");
    mermaidInstance = mermaid.default ?? mermaid;
  }
  return mermaidInstance;
}

async function render() {
  if (!props.source?.trim()) {
    error.value = false;
    svg.value = "";
    return;
  }
  try {
    const mermaid = await loadMermaid();
    mermaid.initialize({
      startOnLoad: false,
      theme: ui.theme === "dark" ? "dark" : "default",
      securityLevel: "loose",
      fontFamily: "inherit"
    });
    const id = `mermaid-${Math.random().toString(36).slice(2, 10)}`;
    const result = await mermaid.render(id, props.source);
    svg.value = result.svg;
    error.value = false;
  } catch {
    error.value = true;
    svg.value = "";
  }
}

onMounted(render);
watch(() => props.source, render);
watch(() => ui.theme, render);
</script>

<style scoped>
.mermaid-block {
  margin: 12px 0;
}

.mermaid-render {
  display: flex;
  justify-content: center;
  background: var(--n-color, transparent);
  border-radius: 6px;
  padding: 8px;
  overflow-x: auto;
}

.mermaid-render :deep(svg) {
  max-width: 100%;
  height: auto;
}

.mermaid-source {
  margin: 8px 0 0;
  padding: 8px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow-y: auto;
}
</style>
