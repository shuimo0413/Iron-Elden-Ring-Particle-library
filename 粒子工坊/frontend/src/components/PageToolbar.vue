<script setup lang="ts">
/** 页内工具条：页面标题 + 副标题 + 右侧页面级操作（extra 插槽） */
defineProps<{
  title: string;
  sub?: string;
}>();
</script>

<template>
  <div class="page-toolbar">
    <div class="title-block">
      <a-typography-title :level="4" class="title">{{ title }}</a-typography-title>
      <a-typography-text v-if="sub" type="secondary">{{ sub }}</a-typography-text>
      <slot name="sub" />
    </div>
    <div class="extra">
      <slot name="extra" />
    </div>
  </div>
</template>

<style scoped>
.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 0 4px;
}

.title-block {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.title {
  margin: 0 !important;
}

.extra {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
