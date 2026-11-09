<script setup lang="ts">
/** 变体卡片：最终出图（深色底预览）、检查结论、手改入口、全部尝试 */
import { computed } from "vue";
import type { Variant } from "@/api/particleRun";
import AttemptList from "./attempt-list.vue";

const props = defineProps<{ variant: Variant; selectable: boolean; selected: boolean; edited: boolean }>();
const emit = defineEmits<{ select: []; edit: []; "discard-edit": [] }>();

const finalAttempt = computed(() =>
  props.variant.attempts.find((attempt) => attempt.attempt_no === props.variant.final_attempt_no),
);
const report = computed(() => finalAttempt.value?.check_report ?? {});
const hints = computed(() => (report.value.items ?? []).filter((item) => item.level === "hint" && !item.passed));

function onClick() {
  if (props.selectable && finalAttempt.value) emit("select");
}
</script>

<template>
  <a-card
    size="small"
    class="variant-card"
    :class="{ selectable: selectable && finalAttempt, selected: selectable && selected }"
    @click="onClick"
  >
    <template #title>
      <a-space>
        <a-radio v-if="selectable && finalAttempt" :checked="selected" />
        <span>变体 {{ variant.variant_id }}</span>
        <a-tag v-if="!finalAttempt" color="error">未出图</a-tag>
        <a-tag v-else-if="finalAttempt.passed" color="success">规则全过</a-tag>
        <a-tag v-else color="warning">规则未全过</a-tag>
        <a-tag v-if="edited" color="purple">已手改</a-tag>
      </a-space>
    </template>
    <template v-if="selectable && finalAttempt" #extra>
      <a-space @click.stop>
        <a-button size="small" @click="emit('edit')">手改</a-button>
        <a-button v-if="edited" size="small" type="link" danger @click="emit('discard-edit')">撤销手改</a-button>
      </a-space>
    </template>

    <div v-if="finalAttempt?.preview_url" class="stage preview-wrap">
      <img :src="finalAttempt.preview_url" class="pixelated preview" alt="预览" />
    </div>
    <a-empty v-else description="暂无出图" />

    <div v-if="finalAttempt" class="report">
      <div v-for="problem in report.problems ?? []" :key="problem" class="problem">✗ {{ problem }}</div>
      <div v-for="item in hints" :key="item.rule" class="muted hint">提示：{{ item.message }}</div>
      <div v-for="warning in report.warnings ?? []" :key="warning" class="muted hint">修复：{{ warning }}</div>
    </div>

    <a-collapse ghost class="attempts" @click.stop>
      <a-collapse-panel key="attempts" :header="`全部尝试（${variant.attempts.length}）`">
        <AttemptList :attempts="variant.attempts" />
      </a-collapse-panel>
    </a-collapse>
  </a-card>
</template>

<style scoped>
.variant-card.selectable {
  cursor: pointer;
}

.variant-card.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.preview-wrap {
  display: flex;
  justify-content: center;
  padding: 12px;
}

.preview {
  width: 100%;
  max-width: 320px;
  aspect-ratio: 1;
}

.report {
  margin-top: 8px;
  font-size: 12px;
}

.problem {
  color: var(--danger);
}

.hint {
  font-size: 12px;
}

.attempts {
  margin-top: 4px;
}
</style>
