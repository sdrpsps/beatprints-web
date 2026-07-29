# BeatPrints

BeatPrints 图片生成服务 monorepo。后端使用 FastAPI + uv，前端工作区使用 pnpm；
两套依赖系统彼此独立，仓库根目录只负责编排开发和部署命令。

```text
.
├── apps/
│   ├── api/          # Python/FastAPI，uv 独立管理
│   └── web/          # 预留前端应用，pnpm 管理
├── packages/         # 预留前端共享包
├── Makefile
├── package.json
├── pnpm-workspace.yaml
└── docker-compose.yml
```

## 快速开始

需要 Python 3.12、[uv](https://docs.astral.sh/uv/) 和 pnpm 11：

```bash
make setup
make dev
```

目前尚未初始化前端，因此 `make dev` 只启动 API。以后在 `apps/web` 创建
`package.json` 且包名设为 `@beatprints/web` 后，`make dev` 会通过 pnpm 同时启动
API 和前端。

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

- Python 依赖：只在 `apps/api/pyproject.toml` 中维护，使用 `uv add`、`uv remove`。
- 前端依赖：只通过根目录 pnpm workspace 或具体前端 package 维护。
- `apps/api/uv.lock` 与根目录 `pnpm-lock.yaml` 都应提交。
- Makefile 负责跨应用命令编排，采用 `动作:应用` 命名。
- pnpm 只管理前端 workspace，uv 只管理 `apps/api`。
