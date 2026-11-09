<script setup lang="ts">
/** 路由 /settings：填写大模型 API Key / 接口地址 / 模型名；保存到后端 data/llm_settings.json，优先于 .env，立即生效 */
import { computed, onMounted, reactive, ref } from "vue";
import { message, Modal } from "ant-design-vue";
import PageToolbar from "@/components/PageToolbar.vue";
import LoadingBlock from "@/components/library/LoadingBlock.vue";
import { getLlmSettings, saveLlmSettings, type LlmSettings } from "@/api/settings";
import { errorMessage } from "@/utils/request";

/** Key 来源 → 中文 */
const SOURCE_LABEL: Record<LlmSettings["api_key_source"], string> = {
  page: "本页面保存",
  env: "backend/.env",
  none: "未配置",
};

const current = ref<LlmSettings | null>(null);
const saving = ref(false);
const form = reactive({ apiKey: "", baseUrl: "", model: "" });

const keyPlaceholder = computed(() =>
  current.value?.api_key_masked ? `当前 ${current.value.api_key_masked}，留空不修改` : "粘贴 API Key，如 sk-...",
);

function fillForm(settings: LlmSettings) {
  current.value = settings;
  form.apiKey = "";
  form.baseUrl = settings.base_url;
  form.model = settings.model;
}

onMounted(async () => {
  try {
    fillForm(await getLlmSettings());
  } catch (e) {
    message.error(errorMessage(e, "读取模型设置失败"));
  }
});

async function onSave() {
  saving.value = true;
  try {
    fillForm(
      await saveLlmSettings({
        api_key: form.apiKey.trim() || null,
        base_url: form.baseUrl.trim(),
        model: form.model.trim(),
      }),
    );
    message.success("已保存，立即生效");
  } catch (e) {
    message.error(errorMessage(e, "保存失败"));
  } finally {
    saving.value = false;
  }
}

function onClearKey() {
  Modal.confirm({
    title: "清除本页面保存的 Key？",
    content: "清除后回退到 backend/.env 里的 LLM_API_KEY（没有则不能生成）。",
    okText: "清除",
    okType: "danger",
    onOk: async () => {
      try {
        fillForm(
          await saveLlmSettings({ clear_api_key: true, base_url: form.baseUrl.trim(), model: form.model.trim() }),
        );
        message.success("已清除");
      } catch (e) {
        message.error(errorMessage(e, "清除失败"));
      }
    },
  });
}
</script>

<template>
  <PageToolbar title="设置" sub="大模型接口（OpenAI 兼容，默认 DeepSeek）；保存后立即生效，不用重启后端" />

  <LoadingBlock v-if="!current" tip="读取设置…" />
  <a-card v-else size="small" class="panel settings-card">
    <a-descriptions :column="1" size="small" class="status">
      <a-descriptions-item label="状态">
        <a-tag :color="current.configured ? 'success' : 'warning'">{{ current.configured ? "已配置" : "未配置" }}</a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="Key 来源">{{ SOURCE_LABEL[current.api_key_source] }}</a-descriptions-item>
    </a-descriptions>

    <a-form layout="vertical" @submit.prevent="onSave">
      <a-form-item label="API Key">
        <a-input-password v-model:value="form.apiKey" :placeholder="keyPlaceholder" autocomplete="off" />
      </a-form-item>
      <a-form-item label="接口地址" extra="留空则用 .env 的 LLM_BASE_URL；DeepSeek 为 https://api.deepseek.com">
        <a-input v-model:value="form.baseUrl" placeholder="https://api.deepseek.com" />
      </a-form-item>
      <a-form-item label="模型名" extra="留空则用 .env 的 LLM_MODEL；需支持 JSON 模式输出">
        <a-input v-model:value="form.model" placeholder="deepseek-flash" />
      </a-form-item>
      <a-space>
        <a-button type="primary" html-type="submit" :loading="saving">保存</a-button>
        <a-button v-if="current.api_key_source === 'page'" danger @click="onClearKey">清除页面 Key</a-button>
      </a-space>
    </a-form>

    <a-alert
      class="panel"
      type="info"
      show-icon
      message="Key 以明文保存在 backend/data/llm_settings.json（该目录已被 git 忽略），仅适合本机单人使用。"
    />
  </a-card>
</template>

<style scoped>
.settings-card {
  max-width: 640px;
}

.status {
  margin-bottom: 8px;
}
</style>
