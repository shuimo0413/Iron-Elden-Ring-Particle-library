<script setup lang="ts">
/** 手改像素：画笔（取色器 + 透明度 / 现有颜色快选）、橡皮、撤销；保存后由父组件随批准提交 */
import { computed, ref, watch } from "vue";
import PixelCanvas from "@/components/PixelCanvas.vue";
import {
  buildGrid,
  collectColors,
  gridToArt,
  hexToRgba,
  rgbaCss,
  rgbaKey,
  rgbaToHex,
  type PixelArt,
  type PixelGrid,
  type Rgba,
} from "@/lib/pixelArt";

/** 编辑画布目标边长（px） */
const EDITOR_CANVAS_SIDE_PX = 512;
/** 撤销步数上限 */
const MAX_UNDO_STEPS = 50;

const props = defineProps<{ art: PixelArt | null }>();
const open = defineModel<boolean>("open", { required: true });
const emit = defineEmits<{ save: [art: PixelArt] }>();

const grid = ref<PixelGrid>([]);
const undoStack = ref<PixelGrid[]>([]);
const brushHex = ref("#ffffff");
const brushAlpha = ref(255);
const erasing = ref(false);
const hover = ref<{ x: number; y: number; rgba: Rgba | null } | null>(null);
/** 一次按下-拖动只记一次撤销点 */
let strokeOpen = false;

const editingArt = computed<PixelArt | null>(() => (props.art ? gridToArt(props.art.name, grid.value) : null));
const scale = computed(() => (props.art ? Math.max(4, Math.floor(EDITOR_CANVAS_SIDE_PX / props.art.width)) : 8));
const swatches = computed(() => (props.art ? collectColors(props.art).map((entry) => entry.rgba) : []));
const brush = computed<Rgba>(() => hexToRgba(brushHex.value, brushAlpha.value));

watch(
  () => [props.art, open.value],
  () => {
    if (props.art && open.value) {
      grid.value = buildGrid(props.art);
      undoStack.value = [];
    }
  },
  { immediate: true },
);

function cloneGrid(source: PixelGrid): PixelGrid {
  return source.map((row) => row.map((cell) => (cell ? ([...cell] as Rgba) : null)));
}

function paint(x: number, y: number) {
  const value = erasing.value ? null : brush.value;
  const current = grid.value[y][x];
  if ((current === null && value === null) || (current && value && rgbaKey(current) === rgbaKey(value))) return;
  if (!strokeOpen) {
    undoStack.value = [...undoStack.value.slice(-MAX_UNDO_STEPS + 1), cloneGrid(grid.value)];
    strokeOpen = true;
  }
  const next = cloneGrid(grid.value);
  next[y][x] = value;
  grid.value = next;
}

function endStroke() {
  strokeOpen = false;
}

function undo() {
  const previous = undoStack.value[undoStack.value.length - 1];
  if (!previous) return;
  grid.value = previous;
  undoStack.value = undoStack.value.slice(0, -1);
}

function pickSwatch(rgba: Rgba) {
  brushHex.value = rgbaToHex(rgba).slice(0, 7).toLowerCase();
  brushAlpha.value = rgba[3];
  erasing.value = false;
}

function save() {
  if (editingArt.value) emit("save", editingArt.value);
}
</script>

<template>
  <a-modal v-model:open="open" title="手改像素" :width="EDITOR_CANVAS_SIDE_PX + 340" ok-text="保存手改" @ok="save">
    <div v-if="editingArt" class="editor">
      <div class="canvas-wrap" @mouseup="endStroke" @mouseleave="endStroke">
        <PixelCanvas :art="editingArt" :scale="scale" editable @paint="paint" @hover="hover = $event" />
        <div class="mono muted hover">
          <template v-if="hover">
            ({{ hover.x }}, {{ hover.y }}) {{ hover.rgba ? `[${hover.rgba.join(", ")}]` : "透明" }}
          </template>
        </div>
      </div>
      <div class="tools">
        <div class="label">画笔</div>
        <a-space>
          <input v-model="brushHex" type="color" class="color-input" @input="erasing = false" />
          <span class="current" :style="{ background: rgbaCss(brush) }" />
          <span class="mono">{{ rgbaToHex(brush) }}</span>
        </a-space>
        <div class="label">透明度 {{ brushAlpha }}</div>
        <a-slider v-model:value="brushAlpha" :min="1" :max="255" />
        <div class="label">现有颜色</div>
        <div class="swatches">
          <span
            v-for="rgba in swatches"
            :key="rgbaKey(rgba)"
            class="swatch"
            :title="rgbaToHex(rgba)"
            :style="{ background: rgbaCss(rgba) }"
            @click="pickSwatch(rgba)"
          />
        </div>
        <a-space class="tool-buttons">
          <a-button :type="erasing ? 'primary' : 'default'" @click="erasing = !erasing">橡皮</a-button>
          <a-button :disabled="!undoStack.length" @click="undo">撤销</a-button>
        </a-space>
        <div class="muted tip">按住鼠标拖动连续绘制；保存后批准时以手改版本入库。</div>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.editor {
  display: flex;
  gap: 16px;
}

.canvas-wrap {
  flex: none;
}

.hover {
  min-height: 20px;
  font-size: 12px;
  margin-top: 4px;
}

.tools {
  flex: 1;
  min-width: 0;
}

.label {
  margin: 8px 0 4px;
  font-weight: 500;
}

.color-input {
  width: 40px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--field-border);
  cursor: pointer;
}

.current {
  display: inline-block;
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
}

.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.swatch {
  width: 22px;
  height: 22px;
  border: 1px solid var(--line);
  cursor: pointer;
}

.tool-buttons {
  margin-top: 12px;
}

.tip {
  margin-top: 8px;
  font-size: 12px;
}
</style>
