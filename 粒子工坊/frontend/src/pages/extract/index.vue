<script setup lang="ts">
/** 路由 /extract：上传图片 → 逐像素 RGBA（标准像素 JSON）+ 颜色列表 + 统计；可放大查看、复制 / 下载 JSON */
import { computed, ref } from "vue";
import { message } from "ant-design-vue";
import PageToolbar from "@/components/PageToolbar.vue";
import PixelCanvas from "@/components/PixelCanvas.vue";
import { extractImage, type ExtractResult } from "@/api/extract";
import { rgbaCss, rgbaToHex, type Rgba } from "@/lib/pixelArt";
import { downloadText } from "@/utils/format";
import { errorMessage } from "@/utils/request";
import UploadPanel from "./components/upload-panel.vue";
import PaletteList from "./components/palette-list.vue";
import ExtractStats from "./components/extract-stats.vue";

/** 画布目标显示边长（px），按图片尺寸自动算初始放大倍数 */
const TARGET_CANVAS_SIDE_PX = 512;

const result = ref<ExtractResult | null>(null);
const loading = ref(false);
const scale = ref(16);
const highlightKey = ref<string | null>(null);
const hover = ref<{ x: number; y: number; rgba: Rgba | null } | null>(null);

const artJson = computed(() => (result.value ? JSON.stringify(result.value.art, null, 2) : ""));

async function onSubmit(payload: { file: File; name: string; minAlpha: number }) {
  loading.value = true;
  try {
    result.value = await extractImage(payload.file, payload.name, payload.minAlpha);
    const side = Math.max(result.value.stats.width, result.value.stats.height);
    scale.value = Math.max(1, Math.min(64, Math.floor(TARGET_CANVAS_SIDE_PX / side)));
    highlightKey.value = null;
  } catch (e) {
    message.error(errorMessage(e, "取色失败"));
  } finally {
    loading.value = false;
  }
}

async function copyJson() {
  try {
    await navigator.clipboard.writeText(artJson.value);
    message.success("已复制像素 JSON");
  } catch {
    message.error("复制失败，请改用下载");
  }
}

function downloadJson() {
  if (result.value) downloadText(`${result.value.art.name}.json`, artJson.value + "\n");
}
</script>

<template>
  <PageToolbar title="图片取色" sub="上传图片，导出每个像素的 RGBA（8 位 × 4 通道），格式与 origin_json 一致">
    <template v-if="result" #extra>
      <a-button @click="copyJson">复制 JSON</a-button>
      <a-button type="primary" @click="downloadJson">下载 JSON</a-button>
    </template>
  </PageToolbar>

  <a-row :gutter="16" class="panel">
    <a-col :xs="24" :lg="7">
      <UploadPanel :loading="loading" @submit="onSubmit" />
      <ExtractStats v-if="result" :stats="result.stats" class="panel" />
    </a-col>

    <a-col :xs="24" :lg="11">
      <a-card v-if="result" size="small" title="像素预览">
        <template #extra>
          <a-space>
            <span class="muted">放大</span>
            <a-slider v-model:value="scale" :min="1" :max="64" style="width: 140px" />
            <span class="mono">×{{ scale }}</span>
          </a-space>
        </template>
        <div class="hover-bar mono">
          <template v-if="hover">
            ({{ hover.x }}, {{ hover.y }})
            <template v-if="hover.rgba">
              <span class="swatch" :style="{ background: rgbaCss(hover.rgba) }" />
              [{{ hover.rgba.join(", ") }}] {{ rgbaToHex(hover.rgba) }}
            </template>
            <span v-else class="muted">透明 / 未写出</span>
          </template>
          <span v-else class="muted">鼠标移到画布上查看坐标与颜色</span>
        </div>
        <div class="canvas-scroll">
          <PixelCanvas :art="result.art" :scale="scale" :highlight-key="highlightKey" @hover="hover = $event" />
        </div>
      </a-card>
      <a-empty v-else description="上传一张图片开始取色" />
    </a-col>

    <a-col :xs="24" :lg="6">
      <PaletteList v-if="result" v-model:highlight-key="highlightKey" :palette="result.palette" />
    </a-col>
  </a-row>
</template>

<style scoped>
.hover-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
  margin-bottom: 8px;
  font-size: 13px;
}

.swatch {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 1px solid var(--line);
}

.canvas-scroll {
  overflow: auto;
  max-height: 70vh;
}
</style>
