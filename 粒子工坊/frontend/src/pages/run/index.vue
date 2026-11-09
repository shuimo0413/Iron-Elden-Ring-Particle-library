<script setup lang="ts">
/** 路由 /runs：任务历史，分页 + 按状态过滤，点行进详情 */
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import PageToolbar from "@/components/PageToolbar.vue";
import { listRuns, type Run } from "@/api/particleRun";
import { fmtTime, RUN_STATUS_META } from "@/utils/format";
import { errorMessage } from "@/utils/request";

const router = useRouter();
const rows = ref<Run[]>([]);
const loading = ref(false);
const status = ref<string | undefined>(undefined);
const pagination = reactive({ current: 1, pageSize: 20, total: 0 });

const statusOptions = Object.entries(RUN_STATUS_META).map(([value, meta]) => ({ value, label: meta.label }));

const columns = [
  { title: "ID", dataIndex: "id", width: 70 },
  { title: "描述", dataIndex: "description", ellipsis: true },
  { title: "尺寸", key: "size", width: 90 },
  { title: "变体", key: "variants", width: 70 },
  { title: "状态", key: "status", width: 100 },
  { title: "入库名", dataIndex: "published_name", width: 180 },
  { title: "创建时间", key: "created_at", width: 180 },
];

async function load() {
  loading.value = true;
  try {
    const page = await listRuns({ page: pagination.current, page_size: pagination.pageSize, status: status.value });
    rows.value = page.items;
    pagination.total = page.total;
  } catch (e) {
    message.error(errorMessage(e, "加载任务历史失败"));
  } finally {
    loading.value = false;
  }
}

function onTableChange(page: { current?: number; pageSize?: number }) {
  pagination.current = page.current ?? 1;
  pagination.pageSize = page.pageSize ?? 20;
  void load();
}

function onStatusChange() {
  pagination.current = 1;
  void load();
}

const rowProps = (record: Run) => ({ onClick: () => router.push(`/runs/${record.id}`), class: "clickable-row" });

onMounted(load);
</script>

<template>
  <PageToolbar title="任务历史">
    <template #extra>
      <a-select
        v-model:value="status"
        :options="statusOptions"
        allow-clear
        placeholder="全部状态"
        style="width: 140px"
        @change="onStatusChange"
      />
      <a-button @click="load">刷新</a-button>
    </template>
  </PageToolbar>

  <a-table
    class="panel"
    row-key="id"
    size="middle"
    :columns="columns"
    :data-source="rows"
    :loading="loading"
    :pagination="pagination"
    :custom-row="rowProps"
    @change="onTableChange"
  >
    <template #bodyCell="{ column, record }">
      <template v-if="column.key === 'size'">{{ record.options.size }}×{{ record.options.size }}</template>
      <template v-else-if="column.key === 'variants'">{{ record.options.variants }}</template>
      <template v-else-if="column.key === 'status'">
        <a-tag :color="RUN_STATUS_META[record.status]?.color">{{ RUN_STATUS_META[record.status]?.label ?? record.status }}</a-tag>
      </template>
      <template v-else-if="column.key === 'created_at'">{{ fmtTime(record.created_at) }}</template>
    </template>
  </a-table>
</template>

<style scoped>
:deep(.clickable-row) {
  cursor: pointer;
}
</style>
