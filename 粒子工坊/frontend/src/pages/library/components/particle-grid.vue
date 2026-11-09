<script setup lang="ts">
/** 粒子缩略图网格：深色底（粒子多叠在深色场景上），点击打开详情 */
import type { ParticleItem } from "@/api/library";

defineProps<{ items: ParticleItem[] }>();
const emit = defineEmits<{ open: [name: string] }>();
</script>

<template>
  <a-empty v-if="!items.length" description="没有匹配的粒子" />
  <div v-else class="grid">
    <div v-for="item in items" :key="item.name" class="cell" :title="item.name" @click="emit('open', item.name)">
      <div class="stage thumb">
        <img :src="item.png_url" class="pixelated" loading="lazy" :alt="item.name" />
      </div>
      <div class="name mono">{{ item.name }}</div>
      <div class="muted size">{{ item.width }}×{{ item.height }}</div>
    </div>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
  gap: 12px;
}

.cell {
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  background: var(--bg1);
  border: 1px solid var(--line);
  transition: border-color 0.15s;
}

.cell:hover {
  border-color: var(--accent);
}

.thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1;
}

.thumb img {
  width: 64px;
  height: 64px;
  object-fit: contain;
}

.name {
  margin-top: 4px;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.size {
  font-size: 11px;
}
</style>
