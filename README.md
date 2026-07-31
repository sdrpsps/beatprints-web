# BeatPrints Web

> 把喜欢的音乐，留下纸面的形状。

BeatPrints Web 是一个可自部署的音乐海报创作工具。搜索一首歌或一张专辑，确认准确
版本，选择最想留下的四行歌词，再将它们排成一张可以下载、收藏或打印的 PNG 海报。

它基于原始 [BeatPrints](https://github.com/TrueMyst/BeatPrints) 项目构建，在原始海报
生成能力之上补充了完整的 Web 创作界面、HTTP API、音乐目录集成与部署工具。后端使用
FastAPI + uv，前端使用 React、Vite、shadcn/ui 与 pnpm；生产环境中，前端构建产物由
同一个 API 容器提供。

## 功能

- 从 Deezer 或 Spotify 音乐目录中搜索并确认单曲或专辑版本。
- 选择四行歌词，或为纯音乐手动添加文字。
- 可选添加 Spotify、Apple Music、QQ 音乐或网易云音乐的二维码入口。
- 配置海报主题、封面强调色、曲目编号和随机曲序。
- 生成、下载和收藏 PNG 音乐海报。
- 提供可供其他应用调用的 REST API。
- 内置简体中文、繁體中文与 English 界面。
- 支持 Docker Compose 自部署。

```text
.
├── apps/
│   ├── api/          # Python/FastAPI，uv 独立管理
│   └── web/          # React/Vite 前端应用，pnpm 管理
├── packages/         # 预留前端共享包
├── Makefile
├── pyproject.toml    # API 项目、构建及工具配置
├── uv.lock
├── package.json
├── pnpm-workspace.yaml
└── docker-compose.yml
```

## 快速开始

需要 Python 3.14、[uv](https://docs.astral.sh/uv/) 和 pnpm 11：

```bash
uv sync
make setup
make dev
```

`make dev` 会同时启动 API 和前端。前端开发路径见
[apps/web/README.md](apps/web/README.md)，产品流程、API 映射和当前集成缺口见
[docs/frontend-product-brief.md](docs/frontend-product-brief.md)。

常用命令：

```bash
make help
make dev
make dev:api
make dev:web
make test:api
make lint:api
make build:api
make docker:up
```

## Docker 镜像

GitHub Actions 会使用 `apps/api/Dockerfile` 构建同时包含 Web 前端与 API 的
`linux/amd64` 和 `linux/arm64` 单镜像：

- Pull Request：只构建验证，不推送。
- 推送到 `main`：发布 `main`、`latest` 和 `sha-xxxxxxx` 标签。
- 推送 `v1.2.3` Git tag：发布 `1.2.3`、`1.2`、`1` 和 SHA 标签。
- 仅修改 Markdown、`docs/` 或 `LICENSE` 时不会触发镜像构建；仍可手动运行工作流。

页面页脚会显示构建版本和短 Git SHA；`/health` 会返回完整版本和 SHA，OpenAPI 文档使用
同一版本。发布构建以 Git tag 与 Actions SHA 为准；本地开发则以根目录 `VERSION` 和当前
Git 工作树生成可追溯的开发版本（未提交修改会标记为 `dirty`）。

镜像地址为：

```text
ghcr.io/<github-owner>/<repository>:latest
```

工作流使用仓库自带的 `GITHUB_TOKEN`，不需要额外配置 Registry 密钥。GHCR 首次发布的
Package 默认可能是私有的，可在 GitHub Package 设置中调整可见性。

API 文档和调用示例见 [apps/api/README.md](apps/api/README.md)。部署时，将服务器的
Nginx、Caddy 或 Traefik 反向代理到容器的 `8000` 端口即可。

## 自动发布

合并到 `main` 的 Conventional Commit 会由 Release Please 汇总为一个可审阅的 Release PR：
`fix:` 递增 patch，`feat:` 递增 minor，带 `!` 或 `BREAKING CHANGE:` 的提交递增 major。
合并该 PR 后，Release Please 会更新 `VERSION`、`pyproject.toml`、`uv.lock` 与
`CHANGELOG.md`，并创建 `vX.Y.Z` Git tag 和 GitHub Release；该 tag 随即触发 Docker
工作流发布镜像。

首次启用时会创建 `v1.0.0` 的 Release PR。后续版本由
[`release-please-config.json`](release-please-config.json) 和
[`.release-please-manifest.json`](.release-please-manifest.json) 共同记录。

在仓库 Actions secrets 中创建 `RELEASE_PLEASE_TOKEN`：它应是有 `Contents: Read and write`
与 `Pull requests: Read and write` 权限的 fine-grained PAT（传统 PAT 则需要 `repo` scope）。
必须使用 PAT，而不是默认的 `GITHUB_TOKEN`，这样 Release Please 创建的 tag 才能触发本仓库
的 Docker 发布工作流。

## 依赖边界

- Python 依赖：只在根目录 `pyproject.toml` 中维护，使用 `uv add`、`uv remove`。
- 前端依赖：只通过根目录 pnpm workspace 或具体前端 package 维护。
- 根目录的 `uv.lock` 与 `pnpm-lock.yaml` 都应提交。
- Makefile 负责跨应用命令编排，采用 `动作:应用` 命名。
- pnpm 只管理前端 workspace，uv 在根目录管理 `apps/api`。

## 致谢与许可

本项目基于 TrueMyst 创作的原始
[BeatPrints](https://github.com/TrueMyst/BeatPrints) 项目构建。请在使用、分发或创建
衍生作品时保留对原始项目的署名。

本项目仅供非商业使用，并采用 [CC BY-NC-SA 4.0](./LICENSE) 许可。
