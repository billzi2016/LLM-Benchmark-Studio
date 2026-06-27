# Vue PRD - LLM Benchmark Studio Frontend

## 1. 目标

前端使用 Vue 3 + Vite，目录为 `frontend/`。界面面向 21:9 超宽屏，清晰、大气、简洁，第一屏就是可操作的 Studio，不做营销式 landing page。

前端核心目标是让用户看见系统状态、模型列表、benchmark datasets、任务队列，并能对单个任务执行 play、pause、stop。

## 1.1 工程原则

前端必须遵守 DRY 和 SOLID 思路：

- DRY：API 请求、SSE 重连、错误提示、状态 badge、进度条、空状态不能重复写。
- Single Responsibility：组件只负责展示和交互，数据请求放 API client，跨组件状态放 store。
- Open/Closed：新增 task type、provider、dataset 状态时通过配置或类型扩展，不重写页面主结构。
- Interface Segregation：System、Models、Datasets、Tasks 拆分独立 store 和组件。
- Dependency Inversion：组件依赖 typed API client 和 store，不直接拼接 fetch 细节。

原则上不自己造轮子。优先使用成熟 Vue 生态套件：

- 构建：Vite。
- 框架：Vue 3 + TypeScript。
- 状态管理：Pinia。
- 路由预留：Vue Router。
- 数据请求缓存：TanStack Query for Vue 或等价成熟方案。
- 图标：lucide-vue-next。
- 表格/虚拟列表：TanStack Table 或成熟 Vue 表格库。
- 表单校验：zod / vee-validate。
- 测试：Vitest + Vue Test Utils。

UI 组件可以使用成熟组件库，但必须保持界面简洁、信息密度高、适合 21:9 operational dashboard。

## 1.2 安全要求

前端必须包含 XSS 和 CSRF 配合策略：

- 不对 dataset 内容、LLM 输出、judge reason 使用不可信 `v-html`。
- 所有来自 API 的文本默认按文本节点渲染。
- 如必须渲染 Markdown，必须使用成熟 sanitizer，例如 DOMPurify。
- API client 必须支持 CSRF token header。
- cookie/session 模式下请求带 `credentials`，并读取后端提供的 CSRF cookie。
- 前端不保存 provider API key。
- 错误弹窗和日志面板不得渲染 HTML。
- 配合后端 CSP，避免 inline script。

## 2. 页面布局

主界面为四列：

1. System 信息列。
2. LLM 模型列。
3. Benchmark Datasets 和 Languages 列。
4. Task Queue 列。

设计比例建议：

```text
System 20% | LLM 25% | Datasets 30% | Task Queue 25%
```

在 21:9 屏幕上默认横向展开。小屏幕时改为可滚动布局，但本项目优先优化 21:9。

## 3. 第一列：System 信息

展示后端 `/api/system/status` 返回的信息：

- Django API 状态。
- PostgreSQL 状态。
- RabbitMQ 状态。
- Celery worker 状态。
- 默认 provider。
- Judge provider / model。
- Translate provider / model。
- think 模型上下文长度。
- no-think 模型上下文长度。
- 数据集目录。
- 激活模型数量。
- 激活数据集数量。
- 激活语言数量。

状态视觉：

- 正常：绿色状态点。
- 警告：黄色状态点。
- 错误：红色状态点。

## 4. 第二列：LLM 模型

数据来自：

```text
GET /api/models
```

后端读取：

```text
data/llm_model_names.json
```

每个模型展示：

- 模型名称。
- provider。
- 是否支持 think。
- context length。
- activate 状态。
- 当前可用状态。

交互：

- 可选择一个模型作为 benchmark target。
- `activate=false` 的模型显示为禁用，不作为默认候选。
- 支持 think 的模型标记 `Think`。
- 不支持 think 的模型标记 `Direct`。

## 5. 第三列：Benchmark Datasets 和 Languages

Datasets 来自：

```text
GET /api/datasets
```

扫描目录：

```text
data/benchmark_datasets/
```

每个 dataset 展示：

- dataset name。
- subset。
- source language。
- sample count。
- imported count。
- evaluated count。
- activate。

Languages 来自：

```text
GET /api/languages
```

后端读取：

```text
data/languages.json
```

每个 language 展示：

- code。
- name。
- activate。

交互：

- 选择 dataset。
- 选择目标语言。
- 点击 translate 创建单个翻译任务。
- 如果 dataset 原语言等于目标语言，前端显示无需翻译，不创建任务。
- 点击 benchmark 创建单个 benchmark 任务。
- 点击 judge 创建单个 judge 任务。
- 点击 regex judge 创建单个 regex judge 任务。

## 6. 第四列：Task Queue

数据来自：

```text
GET /api/tasks
GET /api/events/tasks
```

Task Queue 展示：

- task id。
- task type：benchmark / judge / regex judge / translate。
- dataset。
- sample id。
- model。
- provider。
- target language。
- status。
- progress。
- created time。
- updated time。
- error message。

按钮：

- Play：执行当前选中的 pending / paused 任务。
- Pause：暂停可暂停任务。
- Stop：停止 running / pending 任务。

规则：

- 当前版本一次只执行一个任务。
- 前端不能批量提交任务。
- 如果已有 running 任务，新的任务可以进入 pending，但不能自动并发执行。
- 进度条通过 SSE 滚动更新。
- Benchmark 队列默认按模型分组排序：同一个模型跑完选定数据集后，再切换下一个模型，避免本地模型反复加载。
- Vue Task Queue 必须按 `run_group_id -> model_group_order -> dataset_order -> sample_order` 排序展示，不能按创建时间把不同模型交错在一起。
- 前端创建多模型测评计划时，也必须先按模型生成任务，再按 dataset/sample 生成，和后端排序规则一致。

## 6.1 结果导出

前端必须提供一键导出所有结果的按钮。

交互要求：

- 顶部工具栏或 Task Queue 区域提供 Export Results 按钮。
- 点击后调用后端导出 API。
- 后端返回压缩 ZIP 文件。
- 浏览器直接下载 ZIP。
- ZIP 内包含 JSON 结果文件。
- 默认导出全部结果。
- 后续可扩展按 dataset、model、language、task status 过滤导出。
- 导出过程中按钮显示 loading，避免重复点击。

前端不在浏览器里重新组装全部结果，避免大数据量时卡死。压缩和打包由 Django 后端完成。

## 7. API 集成

前端需要封装 API client：

```text
GET  /api/system/status
GET  /api/models
GET  /api/datasets
GET  /api/languages
GET  /api/tasks
POST /api/tasks/benchmark
POST /api/tasks/judge
POST /api/tasks/regex judge
POST /api/tasks/translate
POST /api/tasks/{task_id}/play
POST /api/tasks/{task_id}/pause
POST /api/tasks/{task_id}/stop
GET  /api/results/export
GET  /api/events/tasks
```

SSE 规则：

- 页面加载后连接 `/api/events/tasks`。
- 收到 task 更新后局部更新 task queue。
- SSE 断开后自动重连。
- 重连后调用 `/api/tasks` 拉取快照。

## 8. UI 风格

视觉要求：

- 专业、清晰、适合长时间观察。
- 避免花哨营销布局。
- 使用高信息密度但不拥挤的 operational dashboard 风格。
- 保证按钮、表格、进度条在 21:9 上稳定对齐。
- 不使用一整屏大 hero。
- 不使用只有 CSS 装饰的空洞视觉。

建议组件：

- 顶部薄工具栏：项目名、连接状态、刷新按钮。
- 四列 workspace。
- 状态 pill。
- 模型列表。
- dataset table。
- language selector。
- task queue table。
- 右侧 task detail drawer 或底部 detail panel。

## 9. Project Tree

```text
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  README.md
  src/
    main.ts
    App.vue
    styles/
      base.css
      layout.css
      components.css
    api/
      client.ts
      system.ts
      models.ts
      datasets.ts
      languages.ts
      tasks.ts
      results.ts
      events.ts
    stores/
      systemStore.ts
      modelStore.ts
      datasetStore.ts
      languageStore.ts
      taskStore.ts
    components/
      layout/
        StudioShell.vue
        TopBar.vue
        ColumnPanel.vue
      system/
        SystemPanel.vue
        StatusIndicator.vue
      models/
        ModelList.vue
        ModelCard.vue
      datasets/
        DatasetPanel.vue
        DatasetTable.vue
        LanguageSelector.vue
      tasks/
        TaskQueue.vue
        TaskControls.vue
        TaskProgress.vue
        TaskDetail.vue
      results/
        ExportResultsButton.vue
    types/
      system.ts
      model.ts
      dataset.ts
      language.ts
      task.ts
    utils/
      format.ts
      sse.ts
      taskOrdering.ts
  tests/
    unit/
      taskStore.test.ts
      modelStore.test.ts
```

## 10. 验收标准

- Vite dev server 可启动。
- 页面默认展示四列 Studio。
- 系统状态、模型、datasets、languages、tasks 均来自 API。
- Task Queue 可通过 SSE 实时更新。
- Play / Pause / Stop 按钮调用对应 API。
- 一次只提交一个任务。
- 21:9 屏幕下无明显重叠、溢出或空白失衡。
