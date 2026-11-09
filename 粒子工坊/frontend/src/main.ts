/** 入口：全局样式、ant-design-vue、路由 */
import { createApp } from "vue";
import Antd from "ant-design-vue";
import "ant-design-vue/dist/reset.css";
import "@/assets/styles/variables.css";
import "@/assets/styles/common.css";
import App from "@/App.vue";
import router from "@/router";

createApp(App).use(Antd).use(router).mount("#app");
