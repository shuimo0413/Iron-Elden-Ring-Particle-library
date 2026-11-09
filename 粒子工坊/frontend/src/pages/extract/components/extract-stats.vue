<script setup lang="ts">
/** 取色统计：源格式、动图、尺寸、写出像素、颜色数、半透明像素 */
import type { ExtractStats } from "@/api/extract";

defineProps<{ stats: ExtractStats }>();
</script>

<template>
  <a-card size="small" title="统计">
    <a-descriptions :column="1" size="small">
      <a-descriptions-item label="源格式">
        <span class="mono">{{ stats.source_mode }}</span>
        <a-tag v-if="stats.animated" color="orange" class="tag">动图，只取第一帧</a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="尺寸">{{ stats.width }} × {{ stats.height }}</a-descriptions-item>
      <a-descriptions-item label="写出像素">{{ stats.written_pixels }} / {{ stats.total_pixels }}</a-descriptions-item>
      <a-descriptions-item label="不重复颜色">{{ stats.unique_colors }}</a-descriptions-item>
      <a-descriptions-item label="半透明像素">{{ stats.semi_transparent_pixels }}</a-descriptions-item>
    </a-descriptions>
  </a-card>
</template>

<style scoped>
.tag {
  margin-left: 8px;
}
</style>
