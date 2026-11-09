<script setup lang="ts">
/**
 * 路由 /runs/:id：任务详情与审核。
 * 运行中每秒轮询增量事件；收到出图类事件时重新拉详情刷新变体卡片；进入审核 / 结束后停止轮询。
 */
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { message, Modal } from "ant-design-vue";
import PageToolbar from "@/components/PageToolbar.vue";
import LoadingBlock from "@/components/library/LoadingBlock.vue";
import {
  cancelRun,
  fetchArtifactJson,
  getRunDetail,
  listRunEvents,
  resumeRun,
  type RunDetail,
  type RunEvent,
} from "@/api/particleRun";
import type { PixelArt } from "@/lib/pixelArt";
import { usePolling } from "@/composables/usePolling";
import { fmtTime, RUN_STATUS_META } from "@/utils/format";
import { errorMessage } from "@/utils/request";
import EventTimeline from "./components/event-timeline.vue";
import VariantCard from "./components/variant-card.vue";
import ReviewBar from "./components/review-bar.vue";
import PixelEditorModal from "./components/pixel-editor-modal.vue";

/** 轮询间隔（毫秒） */
const POLL_INTERVAL_MS = 1000;
/** 后端单次最多返回的事件条数；拿满说明后面还有 */
const MAX_EVENTS_PER_POLL = 200;
/** 收到这些事件时重新拉详情（变体卡片、状态会变） */
const REFRESH_EVENTS = new Set([
  "attempt_ready",
  "parse_failed",
  "variant_done",
  "variant_failed",
  "review_waiting",
  "published",
  "run_rejected",
  "run_failed",
  "run_cancelled",
  "run_interrupted",
]);

const route = useRoute();
const runId = Number(route.params.id);
const detail = ref<RunDetail | null>(null);
const events = ref<RunEvent[]>([]);
const lastSeq = ref(0);
const selectedVariantId = ref<string | null>(null);
const submitting = ref(false);
/** 手改后的像素，按变体存；批准时随请求提交 */
const editedArts = reactive<Record<string, PixelArt>>({});
const editor = reactive<{ open: boolean; variantId: string | null; art: PixelArt | null }>({
  open: false,
  variantId: null,
  art: null,
});

const status = computed(() => detail.value?.run.status);
const polling = computed(() => status.value === "running");
const statusMeta = computed(() => (status.value ? RUN_STATUS_META[status.value] : undefined));
const reviewable = computed(() => status.value === "reviewing");
const renderedVariants = computed(() => detail.value?.variants.filter((v) => v.final_attempt_no !== null) ?? []);

async function loadDetail() {
  try {
    detail.value = await getRunDetail(runId);
    const variants = renderedVariants.value;
    if (!selectedVariantId.value || !variants.some((v) => v.variant_id === selectedVariantId.value)) {
      selectedVariantId.value = detail.value.run.selected_variant_id ?? variants[0]?.variant_id ?? null;
    }
  } catch (e) {
    message.error(errorMessage(e, "加载任务详情失败"));
  }
}

/** 拉取 lastSeq 之后的全部事件；拿满一页就接着拉 */
async function pollEvents() {
  try {
    let needRefresh = false;
    for (;;) {
      const batch = await listRunEvents(runId, lastSeq.value);
      if (!batch.length) break;
      events.value.push(...batch);
      lastSeq.value = batch[batch.length - 1].seq;
      needRefresh ||= batch.some((event) => REFRESH_EVENTS.has(event.type));
      if (batch.length < MAX_EVENTS_PER_POLL) break;
    }
    if (needRefresh) await loadDetail();
  } catch (e) {
    message.error(errorMessage(e, "加载事件失败"));
  }
}

usePolling(pollEvents, POLL_INTERVAL_MS, polling);

onMounted(async () => {
  await loadDetail();
  // 非运行中时轮询不会启动，这里补拉一次完整时间线
  if (!polling.value) await pollEvents();
});

async function submitResume(body: Parameters<typeof resumeRun>[1], successText: string) {
  submitting.value = true;
  try {
    await resumeRun(runId, body);
    message.success(successText);
    await loadDetail();
  } catch (e) {
    message.error(errorMessage(e, "提交审核失败"));
  } finally {
    submitting.value = false;
  }
}

function onApprove(publishName: string) {
  const variantId = selectedVariantId.value;
  if (!variantId) return;
  const edited = editedArts[variantId];
  Modal.confirm({
    title: "批准并入库？",
    content: `将把变体 ${variantId}${edited ? "（手改版）" : ""} 写入粒子库并重建总览图。`,
    okText: "入库",
    onOk: () =>
      submitResume(
        { action: "approve", variant_id: variantId, edited_art: edited ?? null, publish_name: publishName || null },
        "已提交批准，正在入库",
      ),
  });
}

function onRevise(feedback: string) {
  if (!selectedVariantId.value) return;
  void submitResume({ action: "revise", variant_id: selectedVariantId.value, feedback }, "已打回，正在重画");
}

function onReject() {
  Modal.confirm({
    title: "放弃这个任务？",
    content: "放弃后不能再继续审核。",
    okText: "放弃",
    okType: "danger",
    onOk: () => submitResume({ action: "reject" }, "已放弃"),
  });
}

function onCancel() {
  Modal.confirm({
    title: "取消运行中的任务？",
    okText: "取消任务",
    okType: "danger",
    onOk: async () => {
      try {
        await cancelRun(runId);
        message.success("任务已取消");
        await loadDetail();
        await pollEvents();
      } catch (e) {
        message.error(errorMessage(e, "取消失败"));
      }
    },
  });
}

async function onEdit(variantId: string) {
  const variant = detail.value?.variants.find((v) => v.variant_id === variantId);
  const attempt = variant?.attempts.find((a) => a.attempt_no === variant.final_attempt_no);
  if (!attempt?.art_url) return;
  try {
    editor.art = editedArts[variantId] ?? (await fetchArtifactJson<PixelArt>(attempt.art_url));
    editor.variantId = variantId;
    editor.open = true;
  } catch (e) {
    message.error(errorMessage(e, "读取像素数据失败"));
  }
}

function onEditSave(art: PixelArt) {
  if (editor.variantId) editedArts[editor.variantId] = art;
  editor.open = false;
  message.success("已保存手改版本，批准时会以手改为准");
}

function onEditDiscard(variantId: string) {
  delete editedArts[variantId];
}
</script>

<template>
  <LoadingBlock v-if="!detail" tip="加载任务…" />
  <template v-else>
    <PageToolbar :title="`任务 #${detail.run.id}`">
      <template #sub>
        <a-tag :color="statusMeta?.color">{{ statusMeta?.label ?? detail.run.status }}</a-tag>
        <span class="muted">{{ fmtTime(detail.run.created_at) }}</span>
      </template>
      <template #extra>
        <a-button v-if="polling" danger @click="onCancel">取消任务</a-button>
        <a-button @click="loadDetail">刷新</a-button>
      </template>
    </PageToolbar>

    <a-alert
      v-if="detail.run.status === 'published'"
      type="success"
      show-icon
      class="panel"
      :message="`已入库：images/${detail.run.published_name}.png 与 tool/origin_json/${detail.run.published_name}.json`"
    />
    <a-alert v-if="detail.run.error_message" type="error" show-icon class="panel" :message="detail.run.error_message" />

    <a-row :gutter="16" class="panel">
      <a-col :xs="24" :xl="17">
        <a-card size="small" title="任务">
          <a-descriptions :column="{ xs: 1, md: 3 }" size="small">
            <a-descriptions-item label="描述" :span="3">{{ detail.run.description }}</a-descriptions-item>
            <a-descriptions-item label="尺寸">{{ detail.run.options.size }}×{{ detail.run.options.size }}</a-descriptions-item>
            <a-descriptions-item label="类别 / 色调">
              {{ detail.run.options.category }} / {{ detail.run.options.palette }}
            </a-descriptions-item>
            <a-descriptions-item label="描边 / 对称">
              {{ detail.run.options.outline }} / {{ detail.run.options.symmetry }}
            </a-descriptions-item>
            <a-descriptions-item label="模型调用">{{ detail.usage.model_calls }} 次</a-descriptions-item>
            <a-descriptions-item label="输入 token">{{ detail.usage.prompt_tokens }}</a-descriptions-item>
            <a-descriptions-item label="输出 token">{{ detail.usage.completion_tokens }}</a-descriptions-item>
          </a-descriptions>
          <a-alert v-for="note in detail.prompt_notes" :key="note" type="info" show-icon :message="note" class="note" />
          <a-collapse ghost>
            <a-collapse-panel key="prompt" header="首轮提示词">
              <pre class="pre-block">{{ detail.prompt_text }}</pre>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <ReviewBar
          v-if="reviewable"
          class="panel"
          :selected-variant-id="selectedVariantId"
          :edited="!!(selectedVariantId && editedArts[selectedVariantId])"
          :submitting="submitting"
          @approve="onApprove"
          @revise="onRevise"
          @reject="onReject"
        />

        <div class="variants panel">
          <a-empty v-if="!detail.variants.length" description="变体还在生成中…" />
          <VariantCard
            v-for="variant in detail.variants"
            :key="variant.variant_id"
            :variant="variant"
            :selectable="reviewable"
            :selected="selectedVariantId === variant.variant_id"
            :edited="!!editedArts[variant.variant_id]"
            @select="selectedVariantId = variant.variant_id"
            @edit="onEdit(variant.variant_id)"
            @discard-edit="onEditDiscard(variant.variant_id)"
          />
        </div>
      </a-col>

      <a-col :xs="24" :xl="7">
        <EventTimeline :events="events" :running="polling" />
      </a-col>
    </a-row>

    <PixelEditorModal v-model:open="editor.open" :art="editor.art" @save="onEditSave" />
  </template>
</template>

<style scoped>
.note {
  margin-top: 8px;
}

.variants {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
</style>
