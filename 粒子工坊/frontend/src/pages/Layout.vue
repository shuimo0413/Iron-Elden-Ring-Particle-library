<script setup lang="ts">
/** 页面骨架：顶部菜单 + 内容区 */
import AppHeader from "@/components/AppHeader.vue";
</script>

<template>
  <div class="layout">
    <AppHeader />
    <main class="shell">
      <!-- 按路径重建页面：/runs/1 → /runs/2 时详情页需要重新加载 -->
      <router-view :key="$route.path" />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
</style>
