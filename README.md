<div align="center">

# BeatPrints Web

**把喜欢的音乐，留下纸面的形状。**

从真实音乐目录中找到准确的歌曲或专辑，挑选歌词与平台入口，生成一张可以下载、收藏或打印的 PNG 海报。

[BeatPrints Web](https://github.com/sdrpsps/beatprints-web) 基于
[TrueMyst / elysianmyst 的 BeatPrints](https://github.com/TrueMyst/BeatPrints) 构建：
原项目负责音乐海报的核心排版与渲染，本项目为它补充了 Web 创作界面、HTTP API、音乐目录集成和自部署能力。

[快速开始](#快速开始) · [Docker 部署](#docker-部署) · [API 文档](apps/api/README.md) · [前端开发](apps/web/README.md)

</div>

![BeatPrints Web 产品界面](https://us1.workspace.org/d/v2/yaikbaKQV0odeVqFeJ1su6GLxtf2aX-x/2BK7NEM3R11V)

## 与原始 BeatPrints 的关系

[BeatPrints](https://github.com/TrueMyst/BeatPrints) 是由 TrueMyst / elysianmyst
创作的音乐海报生成器，定义了海报的版式、主题、字体、调色板与最终 PNG 渲染方式。
本项目直接使用 BeatPrints 生成器，不是一个无关的同名项目，也没有重新实现它的核心设计。

BeatPrints Web 在原生成器之外补充了：

- 可以在浏览器中完成整个创作流程的 React 界面；
- 用于搜索音乐、读取歌词和生成海报的 FastAPI 服务；
- Deezer、Spotify 与多个二维码目标平台的目录集成；
- Docker Compose、统一生产镜像和自动发布工具。

如果你只需要原始生成器，或想了解海报排版能力本身，请访问
[TrueMyst/BeatPrints](https://github.com/TrueMyst/BeatPrints)。如果你希望通过浏览器使用
BeatPrints，或者把它作为 HTTP 服务部署，则可以直接使用本项目。

## BeatPrints 是什么

BeatPrints Web 是原始 BeatPrints 的可自部署 Web 使用方式。它不生成虚构的音乐内容，
而是从 Deezer 或 Spotify 获取真实的封面与曲目信息，让你确认准确版本后，再调用
BeatPrints 完成海报渲染。

一次单曲海报的创作过程很简单：

```text
搜索歌曲 → 选择准确版本 → 可选最多四行歌词 → 可选一个平台入口 → 调整外观 → 下载 PNG
```

专辑海报沿用相同的创作方式，并提供曲目编号与随机排序选项。生成结果由浏览器直接接收，
服务端不会保存你的海报。

> [!IMPORTANT]
> 音乐资料来源与海报平台入口是两件不同的事。`provider` 决定从 Deezer 或 Spotify
> 获取元数据；`qr_platform` 只决定海报是否带有 Spotify、Apple Music、QQ 音乐或
> 网易云音乐入口。不选择平台时，海报不会显示平台标识或二维码。

## 功能

- **精确选择音乐版本**：搜索歌曲或专辑，并用封面、艺人、发行信息与时长确认结果。
- **编辑歌词内容**：单曲海报可选择零至四行歌词，也可以手动填写。
- **添加平台入口**：可选 Spotify Code，或 Apple Music、QQ 音乐、网易云音乐二维码。
- **跨平台谨慎匹配**：优先使用 ISRC 等稳定标识；无法确认时展示候选项或接受手动链接，
  不会静默选择一个相似结果。
- **定制海报外观**：支持 Light、Dark、Catppuccin、Gruvbox、Nord、RosePine 与
  Everforest 主题，以及封面强调色。
- **单曲与专辑海报**：专辑海报额外支持曲目编号和随机曲序。
- **多语言界面**：简体中文、繁體中文与 English。
- **Web 与 API 一体部署**：生产镜像同时提供前端静态资源和 FastAPI 服务。

## 快速开始

### 环境要求

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- pnpm 11

### 本地开发

```bash
git clone https://github.com/sdrpsps/beatprints-web.git
cd beatprints-web

cp .env.example .env
make setup
make dev
```

启动后可以访问：

- Web：<http://localhost:5173>
- API：<http://localhost:8000>
- OpenAPI：<http://localhost:8000/docs>

Spotify 搜索是可选能力。需要时，在 `.env` 中配置
`SPOTIFY_CLIENT_ID` 和 `SPOTIFY_CLIENT_SECRET`；未配置时仍可使用 Deezer。

### 常用命令

```bash
make help         # 查看全部命令
make dev          # 同时启动 API 与 Web
make dev:api      # 只启动 FastAPI
make dev:web      # 只启动 Vite
make test:api     # 运行 API 测试
make lint:api     # 检查 Python 格式
make build        # 构建 API 与 Web
```

前端的完整质量检查：

```bash
pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

## Docker 部署

项目提供单容器部署：前端构建产物由 FastAPI 一并提供，对外只需要暴露 `8000` 端口。

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

检查服务：

```bash
curl http://localhost:8000/health
```

更新与查看日志：

```bash
git pull
docker compose up -d --build
docker compose logs -f beatprints-api
```

建议将 Nginx、Caddy 或 Traefik 反向代理到容器的 `8000` 端口。生成一张
`2280 × 3480` 海报会占用较多内存；1 GB 内存的服务器建议保持：

```dotenv
WEB_CONCURRENCY=1
MAX_CONCURRENT_JOBS=1
```

### 鉴权说明

`API_KEY` 留空时，Web 界面与 API 均可公开访问。设置 `API_KEY` 后，受保护的 `/v1`
接口需要 Bearer Token。

不要把长期 API Key 写进公开的 Vite 前端。需要鉴权的线上部署，应在应用前增加登录层、
后端代理或其他访问控制；也可以在充分配置限流与滥用防护后，有意识地公开 API。

## 配置

主要环境变量记录在 [`.env.example`](.env.example)：

| 变量 | 用途 | 默认值 |
| --- | --- | --- |
| `PORT` | API 监听端口 | `8000` |
| `API_KEY` | `/v1` 接口的可选 Bearer Token | 留空 |
| `CORS_ORIGINS` | 允许访问 API 的前端来源，多个值用逗号分隔 | 留空 |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | 启用 Spotify 搜索 | 留空 |
| `SPOTIFY_MARKET` | Spotify 市场 | `US` |
| `APPLE_MUSIC_STOREFRONT` | Apple Music storefront | `US` |
| `METADATA_CACHE_TTL_SECONDS` | 元数据缓存时间 | `600` |
| `MAX_CONCURRENT_JOBS` | 单进程同时生成海报的数量 | `1` |

## 项目结构

```text
.
├── apps/
│   ├── api/          # FastAPI、音乐目录集成与海报生成
│   └── web/          # React、Vite、Tailwind CSS 与 shadcn/ui
├── docs/             # 产品流程与集成说明
├── packages/         # 前端共享包
├── Makefile          # 开发、测试、构建与部署入口
├── pyproject.toml    # Python 项目与依赖
├── pnpm-workspace.yaml
└── docker-compose.yml
```

依赖边界：

- Python 依赖由根目录 `pyproject.toml` 与 `uv.lock` 管理。
- Web 依赖由 pnpm workspace 与 `pnpm-lock.yaml` 管理。
- Makefile 只负责编排跨应用命令。

进一步阅读：

- [前端开发指南](apps/web/README.md)
- [API 部署与调用示例](apps/api/README.md)
- [前端产品流程与 API 映射](docs/frontend-product-brief.md)

## API

除了成功返回 PNG 的海报生成接口，JSON 响应统一使用：

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

主要接口包括：

```http
GET  /v1/search
GET  /v1/lyrics
GET  /v1/platform-links/{platform}
POST /v1/posters/track
POST /v1/posters/album
```

完整的请求字段、跨平台匹配方式、错误结构与 `curl` 示例请查看
[BeatPrints API 文档](apps/api/README.md)，或在服务启动后打开 `/docs`。

## 构建与发布

GitHub Actions 会构建同时包含 Web 与 API 的多架构镜像：

```text
ghcr.io/sdrpsps/beatprints-web:latest
```

- Pull Request 会构建 `linux/amd64` 镜像进行验证，但不会推送。
- `vX.Y.Z` tag 会发布 `linux/amd64` 与 `linux/arm64` 镜像。
- Release Please 根据 Conventional Commits 维护版本、变更日志与 GitHub Release。

版本规则为：`fix:` 递增 patch，`feat:` 递增 minor，带 `!` 或
`BREAKING CHANGE:` 的提交递增 major。

## 致谢与许可

本项目基于 TrueMyst / elysianmyst 创作的
[BeatPrints](https://github.com/TrueMyst/BeatPrints) 构建，并保留对原项目的署名。

项目采用 [CC BY-NC-SA 4.0](LICENSE) 许可，仅供非商业使用。使用、分发或创建衍生作品时，
请保留署名并以相同许可共享；商业使用前请先取得原作者授权。
