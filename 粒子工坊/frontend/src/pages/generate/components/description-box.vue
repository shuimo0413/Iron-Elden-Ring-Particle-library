<script setup lang="ts">
/** 描述输入框：一句话描述想要的粒子，最多 500 字 */
const description = defineModel<string>("description", { required: true });
</script>

<template>
  <a-card size="small" title="描述">
    <a-textarea
      v-model:value="description"
      :rows="5"
      :maxlength="500"
      show-count
      placeholder="例如：一枚冰霜碎片，中间有一点高光"
    />
  </a-card>
</template>
