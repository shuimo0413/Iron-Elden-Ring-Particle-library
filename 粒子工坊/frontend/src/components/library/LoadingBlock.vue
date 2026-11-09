<script setup lang="ts">
/** 通用加载占位：居中转圈 + 可选文案 */
defineProps<{ tip?: string }>();
</script>

<template>
  <div class="loading-block">
    <a-spin :tip="tip" />
  </div>
</template>

<style scoped>
.loading-block {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}
</style>
