<script setup lang="ts">
/** 全部尝试：缩略图、触发原因、用量、问题，以及提示词 / 原始返回 / 紧凑 JSON / 标准 JSON 的链接 */
import type { Attempt } from "@/api/particleRun";
import { TRIGGER_LABEL } from "@/utils/format";

defineProps<{ attempts: Attempt[] }>();

/** prompt.txt 与 response.json 同目录 */
function promptUrl(attempt: Attempt): string | null {
  return attempt.raw_response_url?.replace(/response\.json$/, "prompt.txt") ?? null;
}
</script>

<template>
  <div class="attempt-list">
    <div v-for="attempt in attempts" :key="attempt.id" class="attempt">
      <div class="thumb stage">
        <img v-if="attempt.png_url" :src="attempt.png_url" class="pixelated" alt="" />
        <span v-else class="no-image">✗</span>
      </div>
      <div class="info">
        <div class="head">
          <span class="mono">#{{ attempt.attempt_no }}</span>
          <a-tag>{{ TRIGGER_LABEL[attempt.trigger] ?? attempt.trigger }}</a-tag>
          <a-tag v-if="attempt.png_url" :color="attempt.passed ? 'success' : 'warning'">
            {{ attempt.passed ? "通过" : "未通过" }}
          </a-tag>
          <a-tag v-else color="error">解析失败</a-tag>
          <span class="muted mono tokens">{{ attempt.prompt_tokens }}+{{ attempt.completion_tokens }}</span>
        </div>
        <div v-for="problem in attempt.check_report.problems ?? []" :key="problem" class="problem">{{ problem }}</div>
        <div class="links">
          <a v-if="promptUrl(attempt)" :href="promptUrl(attempt)!" target="_blank">提示词</a>
          <a v-if="attempt.raw_response_url" :href="attempt.raw_response_url" target="_blank">原始返回</a>
          <a v-if="attempt.compact_url" :href="attempt.compact_url" target="_blank">紧凑 JSON</a>
          <a v-if="attempt.art_url" :href="attempt.art_url" target="_blank">标准 JSON</a>
          <a v-if="attempt.preview_url" :href="attempt.preview_url" target="_blank">放大图</a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.attempt {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-top: 1px solid var(--line);
}

.thumb {
  flex: none;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumb img {
  width: 64px;
  height: 64px;
}

.no-image {
  color: var(--danger);
}

.info {
  flex: 1;
  min-width: 0;
  font-size: 12px;
}

.head {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.tokens {
  margin-left: auto;
}

.problem {
  color: var(--danger);
  word-break: break-all;
}

.links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 2px;
}
</style>
