<script setup lang="ts">
/**
 * 像素画布（取色、审核、手改、粒子库共用）：用 <canvas> 绘制，不为每个像素建 DOM。
 * - hover：鼠标所在像素坐标与颜色
 * - editable：按住鼠标拖动时持续发出 paint（由父组件改数据）
 */
import { computed, onMounted, ref, watch } from "vue";
import { buildGrid, drawGrid, type PixelArt, type Rgba } from "@/lib/pixelArt";

const props = withDefaults(
  defineProps<{
    art: PixelArt | null;
    /** 每个逻辑像素的屏幕像素数 */
    scale?: number;
    checker?: boolean;
    gridLines?: boolean;
    /** 只高亮这个颜色（rgbaKey），其余变暗 */
    highlightKey?: string | null;
    editable?: boolean;
  }>(),
  { scale: 8, checker: true, gridLines: true, highlightKey: null, editable: false },
);

const emit = defineEmits<{
  hover: [info: { x: number; y: number; rgba: Rgba | null } | null];
  paint: [x: number, y: number];
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const grid = computed(() => (props.art ? buildGrid(props.art) : []));
const cssVar = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
let painting = false;

function redraw() {
  const canvas = canvasRef.value;
  if (!canvas || !props.art) return;
  canvas.width = props.art.width * props.scale;
  canvas.height = props.art.height * props.scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  drawGrid(ctx, grid.value, {
    scale: props.scale,
    checker: props.checker,
    gridLines: props.gridLines,
    highlightKey: props.highlightKey,
    checkerLight: cssVar("--checker-light"),
    checkerDark: cssVar("--checker-dark"),
  });
}

function cellAt(event: MouseEvent): { x: number; y: number } | null {
  const canvas = canvasRef.value;
  if (!canvas || !props.art) return null;
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor(((event.clientX - rect.left) / rect.width) * props.art.width);
  const y = Math.floor(((event.clientY - rect.top) / rect.height) * props.art.height);
  if (x < 0 || y < 0 || x >= props.art.width || y >= props.art.height) return null;
  return { x, y };
}

function onMove(event: MouseEvent) {
  const cell = cellAt(event);
  emit("hover", cell ? { ...cell, rgba: grid.value[cell.y]?.[cell.x] ?? null } : null);
  if (props.editable && painting && cell) emit("paint", cell.x, cell.y);
}

function onDown(event: MouseEvent) {
  if (!props.editable) return;
  painting = true;
  const cell = cellAt(event);
  if (cell) emit("paint", cell.x, cell.y);
}

function onUp() {
  painting = false;
}

function onLeave() {
  painting = false;
  emit("hover", null);
}

watch(() => [props.art, props.scale, props.checker, props.gridLines, props.highlightKey], redraw, { deep: true });
onMounted(redraw);
</script>

<template>
  <canvas
    ref="canvasRef"
    class="pixel-canvas"
    :class="{ editable }"
    @mousemove="onMove"
    @mousedown.prevent="onDown"
    @mouseup="onUp"
    @mouseleave="onLeave"
  />
</template>

<style scoped>
.pixel-canvas {
  display: block;
  image-rendering: pixelated;
  border: 1px solid var(--line);
}

.pixel-canvas.editable {
  cursor: crosshair;
}
</style>
