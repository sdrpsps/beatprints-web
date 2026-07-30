# BeatPrints

BeatPrints 音乐海报制作应用 monorepo。用户查询歌曲或专辑，使用匹配到的封面和音乐
资料，选择歌词与可选的平台入口，生成可下载的 BeatPrints PNG 海报。后端使用
FastAPI + uv，前端使用 React、Vite、shadcn/ui 与 pnpm；两套依赖系统彼此独立，
根目录同时作为 Python 项目和开发、部署命令入口。

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

GitHub Actions 会使用 `apps/api/Dockerfile` 构建 `linux/amd64` 和 `linux/arm64`
镜像：

- Pull Request：只构建验证，不推送。
- 推送到 `main`：发布 `main`、`latest` 和 `sha-xxxxxxx` 标签。
- 推送 `v1.2.3` Git tag：发布 `1.2.3`、`1.2`、`1` 和 SHA 标签。

镜像地址为：

```text
ghcr.io/<github-owner>/<repository>:latest
```

工作流使用仓库自带的 `GITHUB_TOKEN`，不需要额外配置 Registry 密钥。GHCR 首次发布的
Package 默认可能是私有的，可在 GitHub Package 设置中调整可见性。

API 文档和调用示例见 [apps/api/README.md](apps/api/README.md)。

## 依赖边界

- Python 依赖：只在根目录 `pyproject.toml` 中维护，使用 `uv add`、`uv remove`。
- 前端依赖：只通过根目录 pnpm workspace 或具体前端 package 维护。
- 根目录的 `uv.lock` 与 `pnpm-lock.yaml` 都应提交。
- Makefile 负责跨应用命令编排，采用 `动作:应用` 命名。
- pnpm 只管理前端 workspace，uv 在根目录管理 `apps/api`。
