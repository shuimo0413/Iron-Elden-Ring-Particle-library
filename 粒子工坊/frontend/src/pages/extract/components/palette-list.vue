<script setup lang="ts">
/** 颜色列表：按出现次数 / 首次出现排序；点击某色在画布上高亮，再点取消 */
import { computed, ref } from "vue";
import type { PaletteEntry } from "@/api/extract";
import { rgbaCss, rgbaKey } from "@/lib/pixelArt";

const props = defineProps<{ palette: PaletteEntry[] }>();
const highlightKey = defineModel<string | null>("highlightKey", { default: null });

const order = ref<"count" | "first">("count");

const sorted = computed(() =>
  [...props.palette].sort((a, b) =>
    order.value === "count" ? b.count - a.count || a.first_index - b.first_index : a.first_index - b.first_index,
  ),
);

function toggle(entry: PaletteEntry) {
  const key = rgbaKey(entry.rgba);
  highlightKey.value = highlightKey.value === key ? null : key;
}
</script>

<template>
  <a-card size="small" :title="`颜色（${palette.length}）`">
    <template #extra>
      <a-radio-group v-model:value="order" size="small" button-style="solid">
        <a-radio-button value="count">按次数</a-radio-button>
        <a-radio-button value="first">首次出现</a-radio-button>
      </a-radio-group>
    </template>
    <div class="palette-scroll">
      <div
        v-for="entry in sorted"
        :key="entry.hex"
        class="palette-row"
        :class="{ active: highlightKey === rgbaKey(entry.rgba) }"
        @click="toggle(entry)"
      >
        <span class="swatch" :style="{ background: rgbaCss(entry.rgba) }" />
        <span class="mono hex">{{ entry.hex }}</span>
        <span class="mono muted rgba">[{{ entry.rgba.join(",") }}]</span>
        <span class="mono count">{{ entry.count }}</span>
      </div>
    </div>
  </a-card>
</template>

<style scoped>
.palette-scroll {
  max-height: 70vh;
  overflow: auto;
}

.palette-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.palette-row:hover {
  background: var(--bg0);
}

.palette-row.active {
  background: #e6f4ff;
}

.swatch {
  flex: none;
  width: 18px;
  height: 18px;
  border: 1px solid var(--line);
}

.rgba {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.count {
  flex: none;
}
</style>
