<script setup lang="ts">
/** 事件时间线：最新的在最上面；运行中时顶部显示转圈 */
import { computed } from "vue";
import type { RunEvent } from "@/api/particleRun";
import { EVENT_LABEL, fmtTime } from "@/utils/format";

const props = defineProps<{ events: RunEvent[]; running: boolean }>();

const ERROR_EVENTS = new Set(["parse_failed", "check_failed", "variant_failed", "run_failed"]);
const SUCCESS_EVENTS = new Set(["variant_done", "published"]);

const reversed = computed(() => [...props.events].reverse());

function color(type: string): string {
  if (ERROR_EVENTS.has(type)) return "red";
  if (SUCCESS_EVENTS.has(type)) return "green";
  if (type === "review_waiting") return "orange";
  return "blue";
}

/** 每类事件挑最有用的一句摘要 */
function summary(event: RunEvent): string {
  const payload = event.payload as Record<string, unknown>;
  switch (event.type) {
    case "model_called":
      return payload.error
        ? `第 ${payload.attempt_no} 次调用失败：${payload.error}`
        : `第 ${payload.attempt_no} 次（${payload.prompt_tokens}+${payload.completion_tokens} token）`;
    case "parse_failed":
    case "check_failed":
      return `第 ${payload.attempt_no} 次：${((payload.problems as string[]) ?? []).join("；")}`;
    case "attempt_ready":
      return `第 ${payload.attempt_no} 次出图${payload.passed ? "，规则全过" : "，规则未全过"}`;
    case "variant_done":
      return `最终第 ${payload.final_attempt_no} 次`;
    case "variant_failed":
      return String(payload.error ?? "");
    case "review_submitted":
      return [payload.action, payload.feedback, payload.edited ? "手改" : ""].filter(Boolean).join(" · ");
    case "published":
      return `${payload.name}${(payload.warnings as string[])?.length ? "；" + (payload.warnings as string[]).join("；") : ""}`;
    case "run_failed":
    case "run_cancelled":
    case "run_interrupted":
    case "run_rejected":
      return String(payload.reason ?? "");
    default:
      return "";
  }
}
</script>

<template>
  <a-card size="small" title="时间线">
    <div class="timeline-scroll">
      <a-timeline :pending="running ? '运行中…' : undefined" :reverse="false">
        <a-timeline-item v-for="event in reversed" :key="event.seq" :color="color(event.type)">
          <div class="head">
            <span class="type">{{ EVENT_LABEL[event.type] ?? event.type }}</span>
            <a-tag v-if="event.variant_id" class="variant">{{ event.variant_id }}</a-tag>
            <span class="muted time">{{ fmtTime(event.created_at).slice(-8) }}</span>
          </div>
          <div v-if="summary(event)" class="muted summary">{{ summary(event) }}</div>
        </a-timeline-item>
      </a-timeline>
      <a-empty v-if="!events.length" description="暂无事件" />
    </div>
  </a-card>
</template>

<style scoped>
.timeline-scroll {
  max-height: 75vh;
  overflow: auto;
  padding-top: 8px;
}

.head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.type {
  font-weight: 500;
}

.variant {
  margin: 0;
}

.time {
  margin-left: auto;
  font-size: 12px;
}

.summary {
  font-size: 12px;
  word-break: break-all;
}
</style>
