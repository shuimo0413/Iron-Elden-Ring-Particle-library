<script setup lang="ts">
/** 顶部菜单：按当前路由高亮 */
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const items = [
  { key: "/", label: "新建任务" },
  { key: "/runs", label: "任务历史" },
  { key: "/extract", label: "图片取色" },
  { key: "/library", label: "粒子库" },
  { key: "/settings", label: "设置" },
];

const selectedKeys = computed(() => {
  const path = route.path;
  if (path.startsWith("/runs")) return ["/runs"];
  const match = items.find((item) => item.key !== "/" && path.startsWith(item.key));
  return [match?.key ?? "/"];
});

const onSelect = ({ key }: { key: string | number }) => router.push(String(key));
</script>

<template>
  <header class="app-header">
    <div class="brand">粒子工坊</div>
    <a-menu mode="horizontal" :selected-keys="selectedKeys" :items="items" class="menu" @click="onSelect" />
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  background: var(--bg1);
  border-bottom: 1px solid var(--line);
}

.brand {
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.menu {
  flex: 1;
  border-bottom: none;
}
</style>
