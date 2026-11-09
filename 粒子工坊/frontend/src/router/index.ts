/** 路由表：页面懒加载 */
import { createRouter, createWebHistory } from "vue-router";
import Layout from "@/pages/Layout.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: Layout,
      children: [
        { path: "", name: "generate", component: () => import("@/pages/generate/index.vue"), meta: { title: "新建任务" } },
        { path: "runs", name: "runs", component: () => import("@/pages/run/index.vue"), meta: { title: "任务历史" } },
        {
          path: "runs/:id",
          name: "run-detail",
          component: () => import("@/pages/run/detail.vue"),
          meta: { title: "任务详情" },
        },
        { path: "extract", name: "extract", component: () => import("@/pages/extract/index.vue"), meta: { title: "图片取色" } },
        { path: "library", name: "library", component: () => import("@/pages/library/index.vue"), meta: { title: "粒子库" } },
        { path: "settings", name: "settings", component: () => import("@/pages/settings/index.vue"), meta: { title: "设置" } },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.afterEach((to) => {
  const title = to.meta.title as string | undefined;
  document.title = title ? `${title} · 粒子工坊` : "粒子工坊";
});

export default router;
