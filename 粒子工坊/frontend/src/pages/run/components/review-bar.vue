<script setup lang="ts">
/** 审核栏：对选中变体批准（可填入库名）/ 打回附意见 / 放弃整个任务 */
import { ref } from "vue";

defineProps<{ selectedVariantId: string | null; edited: boolean; submitting: boolean }>();
const emit = defineEmits<{ approve: [publishName: string]; revise: [feedback: string]; reject: [] }>();

const publishName = ref("");
const feedback = ref("");

function revise() {
  if (feedback.value.trim()) emit("revise", feedback.value.trim());
}
</script>

<template>
  <a-card size="small" title="审核">
    <template #extra>
      <span class="muted">
        当前选中：
        <b>{{ selectedVariantId ?? "未选择" }}</b>
        <template v-if="edited">（手改版）</template>
      </span>
    </template>
    <a-row :gutter="16">
      <a-col :xs="24" :md="12">
        <div class="label">批准入库</div>
        <a-input
          v-model:value="publishName"
          placeholder="入库文件名（留空用模型起的名字）"
          :maxlength="64"
          class="field"
        />
        <a-button type="primary" :disabled="!selectedVariantId" :loading="submitting" @click="emit('approve', publishName.trim())">
          批准并入库
        </a-button>
      </a-col>
      <a-col :xs="24" :md="12">
        <div class="label">打回重画（只重画选中变体）</div>
        <a-textarea
          v-model:value="feedback"
          :rows="2"
          :maxlength="500"
          placeholder="例如：高光太多，整体再暗一档"
          class="field"
        />
        <a-space>
          <a-button :disabled="!selectedVariantId || !feedback.trim()" :loading="submitting" @click="revise">打回</a-button>
          <a-button danger :loading="submitting" @click="emit('reject')">放弃任务</a-button>
        </a-space>
      </a-col>
    </a-row>
  </a-card>
</template>

<style scoped>
.label {
  margin-bottom: 6px;
  font-weight: 500;
}

.field {
  margin-bottom: 8px;
}
</style>
