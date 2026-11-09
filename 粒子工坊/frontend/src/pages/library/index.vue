<script setup lang="ts">
/** 路由 /library：粒子库浏览（搜索、按系列过滤、详情抽屉）与总览图重建 */
import { computed, onMounted, ref } from "vue";
import { message } from "ant-design-vue";
import PageToolbar from "@/components/PageToolbar.vue";
import PixelCanvas from "@/components/PixelCanvas.vue";
import LoadingBlock from "@/components/library/LoadingBlock.vue";
import {
  getParticle,
  listParticles,
  rebuildShowcase,
  showcaseUrl,
  type ParticleDetail,
  type ParticleItem,
} from "@/api/library";
import { downloadText, fmtTime } from "@/utils/format";
import { errorMessage } from "@/utils/request";
import ParticleGrid from "./components/particle-grid.vue";

/** 详情抽屉里画布的目标边长（px） */
const DETAIL_CANVAS_SIDE_PX = 320;

const particles = ref<ParticleItem[]>([]);
const loading = ref(false);
const keyword = ref("");
const series = ref<string | undefined>(undefined);
const detail = ref<ParticleDetail | null>(null);
const drawerOpen = ref(false);
const rebuilding = ref(false);
const showcaseOpen = ref(false);
const showcaseSrc = ref("");

const seriesOptions = computed(() =>
  [...new Set(particles.value.map((item) => item.series))].sort().map((value) => ({ value, label: value })),
);

/** 一次拉全量后在前端过滤：库只有几百张，免得每敲一个字发一次请求 */
const filtered = computed(() => {
  const query = keyword.value.trim().toLowerCase();
  return particles.value.filter(
    (item) => (!series.value || item.series === series.value) && (!query || item.name.toLowerCase().includes(query)),
  );
});

const detailScale = computed(() =>
  detail.value ? Math.max(1, Math.floor(DETAIL_CANVAS_SIDE_PX / Math.max(detail.value.width, detail.value.height))) : 8,
);

async function load() {
  loading.value = true;
  try {
    particles.value = await listParticles({});
  } catch (e) {
    message.error(errorMessage(e, "加载粒子库失败"));
  } finally {
    loading.value = false;
  }
}

async function openDetail(name: string) {
  try {
    detail.value = await getParticle(name);
    drawerOpen.value = true;
  } catch (e) {
    message.error(errorMessage(e, "加载粒子详情失败"));
  }
}

async function onRebuild() {
  rebuilding.value = true;
  try {
    const result = await rebuildShowcase();
    message.success(`总览图已重建，共 ${result.particle_count} 张`);
    openShowcase();
  } catch (e) {
    message.error(errorMessage(e, "重建总览图失败"));
  } finally {
    rebuilding.value = false;
  }
}

function openShowcase() {
  showcaseSrc.value = showcaseUrl();
  showcaseOpen.value = true;
}

function downloadArt() {
  if (detail.value) downloadText(`${detail.value.name}.json`, JSON.stringify(detail.value.art, null, 2) + "\n");
}

onMounted(load);
</script>

<template>
  <PageToolbar title="粒子库" :sub="`共 ${particles.length} 张，当前显示 ${filtered.length} 张`">
    <template #extra>
      <a-input-search v-model:value="keyword" placeholder="按名称搜索" allow-clear style="width: 200px" />
      <a-select
        v-model:value="series"
        :options="seriesOptions"
        allow-clear
        show-search
        placeholder="全部系列"
        style="width: 160px"
      />
      <a-button @click="load">刷新</a-button>
      <a-button @click="openShowcase">查看总览图</a-button>
      <a-button type="primary" :loading="rebuilding" @click="onRebuild">重建总览图</a-button>
    </template>
  </PageToolbar>

  <LoadingBlock v-if="loading && !particles.length" tip="加载粒子库…" />
  <ParticleGrid v-else class="panel" :items="filtered" @open="openDetail" />

  <a-drawer v-model:open="drawerOpen" :title="detail?.name" width="420">
    <template v-if="detail">
      <div class="detail-canvas">
        <PixelCanvas :art="detail.art" :scale="detailScale" />
      </div>
      <a-descriptions :column="1" size="small" class="panel">
        <a-descriptions-item label="尺寸">{{ detail.width }}×{{ detail.height }}</a-descriptions-item>
        <a-descriptions-item label="系列">{{ detail.series }}</a-descriptions-item>
        <a-descriptions-item label="像素数">{{ detail.art.pixels.length }}</a-descriptions-item>
        <a-descriptions-item label="源 JSON">{{ detail.has_json ? "tool/origin_json 中有" : "无（由 PNG 现取）" }}</a-descriptions-item>
        <a-descriptions-item label="修改时间">{{ fmtTime(new Date(detail.modified_at * 1000).toISOString()) }}</a-descriptions-item>
      </a-descriptions>
      <a-space class="panel">
        <a-button :href="detail.png_url" target="_blank">打开 PNG</a-button>
        <a-button @click="downloadArt">下载像素 JSON</a-button>
      </a-space>
    </template>
  </a-drawer>

  <a-modal v-model:open="showcaseOpen" title="粒子库总览图" width="90vw" :footer="null">
    <div class="showcase-wrap">
      <img :src="showcaseSrc" class="pixelated showcase" alt="粒子库总览图" />
    </div>
  </a-modal>
</template>

<style scoped>
.detail-canvas {
  display: flex;
  justify-content: center;
}

.showcase-wrap {
  max-height: 80vh;
  overflow: auto;
  text-align: center;
}

.showcase {
  max-width: 100%;
}
</style>
