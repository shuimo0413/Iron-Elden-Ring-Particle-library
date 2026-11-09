<script setup lang="ts">
/** 根组件：中文语言包 + 路由出口 */
import zhCN from "ant-design-vue/es/locale/zh_CN";
</script>

<template>
  <a-config-provider :locale="zhCN">
    <router-view />
  </a-config-provider>
</template>
