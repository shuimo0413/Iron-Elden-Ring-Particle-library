<script setup lang="ts">
/** 提示词预览：冲突提示 + system / user 两条消息 */
import type { PromptPreview } from "@/api/option";

defineProps<{ preview: PromptPreview }>();
</script>

<template>
  <a-card size="small" title="提示词预览">
    <a-alert v-for="note in preview.notes" :key="note" type="info" show-icon :message="note" class="note" />
    <a-collapse :default-active-key="['user']" ghost>
      <a-collapse-panel key="user" header="user 消息">
        <pre class="pre-block">{{ preview.user }}</pre>
      </a-collapse-panel>
      <a-collapse-panel key="system" header="system 消息（固定）">
        <pre class="pre-block">{{ preview.system }}</pre>
      </a-collapse-panel>
    </a-collapse>
  </a-card>
</template>

<style scoped>
.note {
  margin-bottom: 8px;
}
</style>
