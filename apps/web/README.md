# BeatPrints Web

BeatPrints Web 前端应用，使用 React、TypeScript、Vite、Tailwind CSS v4 和 shadcn/ui
（Base UI）。

## 产品流程

BeatPrints Web 用真实歌曲或专辑的资料、封面与歌词制作可下载的 PNG 海报。核心歌曲流程是：

```text
查询歌曲 → 选择准确版本 → 可选最多四行歌词 → 可选的平台二维码 → 配置样式 → 生成并下载
```

搜索结果选定后，前端必须保留并提交原始 `provider + id`，不能重新提交搜索词让后端选择
第一条结果。元数据来源和海报上的可选平台二维码是两个不同概念。

前端通过 `GET /v1/lyrics` 读取所选 `provider + catalog_id` 的规范化歌词行，默认不选
歌词，并允许用户选择最多四行或手动填写；留空时海报不显示歌词。完整的产品流程、接口映射与状态见
[`docs/frontend-product-brief.md`](../../docs/frontend-product-brief.md)。

## 开发

从仓库根目录运行：

```bash
pnpm --filter @beatprints/web dev
pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

开发服务器会将 `/v1` 与 `/health` 代理到 `http://localhost:8000`。生产环境默认使用同源
API；如果 Web 与 API 分开部署，可在构建时设置 `VITE_API_BASE_URL`。

## UI 开发路径

新建界面或组件时，遵循以下顺序：

1. 明确页面用户、单一目标、真实内容和必要状态。
2. 在 shadcn 中查找已有组件，优先组合，不从零实现 UI 原语。
3. 调用仓库已安装的 `shadcn` skill。新增、修复或使用组件前，都先读取当前组件文档
   和示例；不确定用哪个组件时先搜索官方 registry：

   ```bash
   pnpm dlx shadcn@latest docs <component> -c apps/web
   pnpm dlx shadcn@latest search @shadcn -q "<need>" -c apps/web
   pnpm dlx shadcn@latest add <component> -c apps/web --dry-run
   ```

4. 新页面、新流程或大幅视觉调整再调用仓库安装的 `frontend-design` skill，确定信息
   层级、交互、排版、色彩、响应式和动效。设计必须来自封面、歌词、唱片资料与制作海报
   的过程，避免套用普通 AI 产品或 SaaS dashboard 模板。
5. 安装组件并进行业务组合：

   ```bash
   pnpm dlx shadcn@latest add <component> -c apps/web
   ```

6. 检查加载、空、错误、成功、禁用、键盘焦点、移动端和 reduced-motion 状态。
7. 完成后运行 lint、build，并在桌面与移动端进行视觉检查。

## 目录职责

```text
src/
├── components/
│   ├── ui/              # shadcn 管理的 UI 原语
│   └── ...              # 跨业务复用的组合组件
├── features/<feature>/  # 业务功能、状态、hooks、服务及组合组件
├── pages/               # 路由页面，只负责页面级组合
├── hooks/               # 跨业务 React hooks
└── lib/                 # 与 UI 无关的工具和集成
```

不要把业务组件放入 `components/ui`。只有在 shadcn 及其合理组合无法满足明确的交互或
可访问性要求时，才允许自建 UI 原语，并在变更说明中记录原因。

UI 原语默认来自官方 `@shadcn` registry。页面 block 或第三方 registry 组件必须使用
需求中明确指定的来源；来源不明确时先确认，不擅自选择。

完整的 Agent 约束见仓库根目录的 [`AGENTS.md`](../../AGENTS.md)。
