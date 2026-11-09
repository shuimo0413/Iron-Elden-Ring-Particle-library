<script setup lang="ts">
/** 取色上传面板：选文件、name、min_alpha，提交给父组件 */
import { ref } from "vue";
import { InboxOutlined } from "@ant-design/icons-vue";

defineProps<{ loading: boolean }>();
const emit = defineEmits<{ submit: [payload: { file: File; name: string; minAlpha: number }] }>();

const file = ref<File | null>(null);
const name = ref("");
const minAlpha = ref(1);

/** 不让组件库自己上传，只记下文件；选中后立即取色 */
function beforeUpload(selected: File) {
  file.value = selected;
  name.value = selected.name.replace(/\.[^.]+$/, "");
  submit();
  return false;
}

function submit() {
  if (file.value) emit("submit", { file: file.value, name: name.value, minAlpha: minAlpha.value });
}
</script>

<template>
  <a-card size="small" title="上传图片">
    <a-upload-dragger
      :show-upload-list="false"
      :before-upload="beforeUpload"
      accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
    >
      <p class="ant-upload-drag-icon"><InboxOutlined /></p>
      <p class="ant-upload-text">点击或拖入图片</p>
      <p class="ant-upload-hint">PNG / JPG / GIF / WebP / BMP，边长 ≤ 512</p>
    </a-upload-dragger>

    <a-form layout="vertical" class="form">
      <a-form-item label="name（写入 JSON）">
        <a-input v-model:value="name" placeholder="默认用文件名" :maxlength="64" />
      </a-form-item>
      <a-form-item label="min_alpha（低于此值的像素不写入）">
        <a-input-number v-model:value="minAlpha" :min="0" :max="255" style="width: 100%" />
        <div class="muted hint">1 = 跳过完全透明；0 = 全部写出</div>
      </a-form-item>
      <a-button type="primary" block :loading="loading" :disabled="!file" @click="submit">
        {{ file ? `重新取色：${file.name}` : "先选择图片" }}
      </a-button>
    </a-form>
  </a-card>
</template>

<style scoped>
.form {
  margin-top: 16px;
}

.hint {
  font-size: 12px;
  margin-top: 4px;
}
</style>
