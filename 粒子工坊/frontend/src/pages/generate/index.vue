<script setup lang="ts">
/** 路由 /：选按钮 + 写描述 → 预览提示词 → 新建任务后跳到详情页 */
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import PageToolbar from "@/components/PageToolbar.vue";
import LoadingBlock from "@/components/library/LoadingBlock.vue";
import { getOptions, previewPrompt, type OptionsPayload, type PromptPreview, type RunOptions } from "@/api/option";
import { createRun } from "@/api/particleRun";
import { errorMessage } from "@/utils/request";
import OptionButtons from "./components/option-buttons.vue";
import DescriptionBox from "./components/description-box.vue";
import PromptPreviewPanel from "./components/prompt-preview.vue";

const router = useRouter();
const catalog = ref<OptionsPayload | null>(null);
const options = ref<RunOptions | null>(null);
const description = ref("");
const preview = ref<PromptPreview | null>(null);
const previewing = ref(false);
const submitting = ref(false);

onMounted(async () => {
  try {
    catalog.value = await getOptions();
    options.value = { ...catalog.value.defaults };
  } catch (e) {
    message.error(errorMessage(e, "加载按钮清单失败"));
  }
});

function body() {
  return { description: description.value.trim(), options: options.value as RunOptions };
}

async function onPreview() {
  if (!description.value.trim()) {
    message.warning("先写一句描述");
    return;
  }
  previewing.value = true;
  try {
    preview.value = await previewPrompt(body());
  } catch (e) {
    message.error(errorMessage(e, "预览提示词失败"));
  } finally {
    previewing.value = false;
  }
}

async function onSubmit() {
  if (!description.value.trim()) {
    message.warning("先写一句描述");
    return;
  }
  submitting.value = true;
  try {
    const run = await createRun(body());
    await router.push(`/runs/${run.id}`);
  } catch (e) {
    message.error(errorMessage(e, "新建任务失败"));
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <PageToolbar title="新建任务" sub="按钮决定硬性约束，描述决定画什么；按钮与描述冲突时以按钮为准" />

  <LoadingBlock v-if="!catalog || !options" tip="加载按钮清单…" />
  <template v-else>
    <a-alert v-if="!catalog.llm_configured" type="warning" show-icon class="panel">
      <template #message>
        还没有配置大模型 API Key，暂时不能生成；图片取色不受影响。
        <router-link to="/settings">去设置</router-link>
      </template>
    </a-alert>
    <a-row :gutter="16" class="panel">
      <a-col :xs="24" :lg="12">
        <OptionButtons v-model:options="options" :catalog="catalog" />
      </a-col>
      <a-col :xs="24" :lg="12">
        <DescriptionBox v-model:description="description" />
        <div class="actions">
          <a-button :loading="previewing" @click="onPreview">预览提示词</a-button>
          <a-button type="primary" :loading="submitting" :disabled="!catalog.llm_configured" @click="onSubmit">
            生成 {{ options.variants }} 个变体
          </a-button>
        </div>
        <PromptPreviewPanel v-if="preview" :preview="preview" class="panel" />
      </a-col>
    </a-row>
  </template>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
