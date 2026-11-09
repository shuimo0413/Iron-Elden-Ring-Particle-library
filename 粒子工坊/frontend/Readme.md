# 粒子工坊 · 前端

Vue 3 + TypeScript + Vite + ant-design-vue 4。设计见 `../设计文档.md`。

```powershell
cd 粒子工坊/frontend
npm install
npm run dev        # http://localhost:5175 ，/api 代理到 127.0.0.1:8002（先启动后端）
npm run build      # vue-tsc 类型检查 + 打包
```

页面：

| 路由 | 用途 |
|---|---|
| `/` | 选按钮 + 写描述，预览提示词，新建生成任务 |
| `/runs` | 任务历史 |
| `/runs/:id` | 进度时间线、变体预览、审核（批准 / 手改后批准 / 打回 / 放弃）、取消 |
| `/extract` | 图片取色：上传图片得到逐像素 RGBA |
| `/library` | 粒子库浏览与总览图重建 |
| `/settings` | 填写大模型 API Key / 接口地址 / 模型名（保存到后端，立即生效） |

目录：`api`（只写接口）→ `pages`（页面 + 页面私有组件）→ `components`（跨页组件）；`lib/pixelArt.ts` 是像素纯函数，`utils/request.ts` 统一处理 `{code, message, data}`。
