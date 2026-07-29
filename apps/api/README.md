# BeatPrints API

一个把 [TrueMyst/BeatPrints](https://github.com/TrueMyst/BeatPrints) 封装成 HTTP API
的轻量服务。生成器直接使用 BeatPrints 1.1.9，因此版式、主题、字体、调色板和图片尺寸
与原项目一致。

> 许可证提示：BeatPrints 使用 CC BY-NC-SA 4.0。本项目同样按该许可证发布，只适用于
> 非商业用途，并保留对原作者 TrueMyst/elysianmyst 的署名。商业部署前请先获得原作者授权。

## 本地启动

需要 Python 3.14 和 [uv](https://docs.astral.sh/uv/)：

```bash
# 从 monorepo 根目录执行
uv sync
uv run uvicorn beatprints_api.main:app --reload
```

添加或删除依赖使用 `uv add` / `uv remove`，不要直接编辑 `requirements.txt` 或向
`.venv` 执行 `pip install`。根目录的 `uv.lock` 必须提交到版本控制。

或使用 Docker：

```bash
# 从 monorepo 根目录执行
docker build -f apps/api/Dockerfile -t beatprints-api .
docker run --rm -p 8000:8000 beatprints-api
```

打开 `http://localhost:8000/docs` 可直接调试所有接口。

## API 分层

后端按三层组织，入口 `main.py` 只负责创建和组装 FastAPI 应用：

```text
src/beatprints_api/
├── api/                 # API 层：路由、鉴权、异常处理、中间件
│   └── routes/
├── services/            # Services 层：目录搜索、元数据、封面与海报业务
└── models/              # Model / DTO 层：Pydantic 请求、响应模型
```

除成功返回 PNG 的两个海报接口外，所有 JSON 成功及错误响应都采用统一结构：

```json
{
  "code": 0,
  "data": {
    "status": "ok"
  },
  "message": "success"
}
```

`code` 为 `0` 表示成功；错误使用非零业务码，`data` 在无附加信息时为 `null`。
Pydantic 请求校验错误会在 `data.errors` 中提供字段级详情。所有响应都带有
`X-Request-ID` 和 `X-Process-Time` 响应头，其中 `X-Process-Time` 是本次请求在应用内
处理所用的毫秒数（纯数值，保留三位小数）。

## Docker 服务器部署

建议至少使用 1 GB 内存的 Linux 服务器。第一次部署：

```bash
cp .env.example .env
# 编辑 .env，至少修改 API_KEY
docker compose up -d --build
docker compose ps
```

检查服务：

```bash
curl http://localhost:8000/health
```

设置 `API_KEY` 后，除健康检查外的接口都需要 Bearer Token：

```bash
curl http://localhost:8000/v1/themes \
  -H "Authorization: Bearer $API_KEY"
```

更新服务：

```bash
git pull
docker compose up -d --build
```

默认只允许一个海报生成任务同时执行。高分辨率图片处理会占用较多内存；确认服务器资源
充足后，才建议提高 `WEB_CONCURRENCY` 或 `MAX_CONCURRENT_JOBS`。每个 Web 进程有各自的
并发限制，因此实际最大并发约为两者乘积。

在 Nginx、Caddy 或云平台负载均衡器后部署时，将其反向代理到容器的 `8000` 端口即可。
应用已启用代理头处理，平台也可以通过 `PORT` 环境变量修改监听端口。

## 1. 只传歌曲查询词

服务会用 `provider` 指定的平台获取元数据和封面，并用 LRClib 获取歌词。默认平台是
Spotify；没有指定 `lyrics_range` 时使用前四行非空歌词。

```bash
curl -X POST http://localhost:8000/v1/posters/track \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "provider": "spotify",
    "query": "Apples - Rocco",
    "theme": "Light",
    "accent": false
  }' \
  --output track.png
```

推荐把搜索结果中的 `provider + id` 原样传成 `provider + catalog_id`：

```json
{
  "provider": "spotify",
  "catalog_id": "3B0ms7Xlxl16tRztKHpcu9",
  "lyrics": "line one\nline two\nline three\nline four",
  "theme": "Nord",
  "accent": true
}
```

## 2. 只传专辑查询词

```bash
curl -X POST http://localhost:8000/v1/posters/album \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "provider": "spotify",
    "query": "Charm - Clairo",
    "theme": "Light",
    "accent": true,
    "indexing": false
  }' \
  --output album.png
```

## 3. 直接传完整信息

不依赖任何音乐平台元数据时，可直接传 `metadata`：

```bash
curl -X POST http://localhost:8000/v1/posters/track \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "metadata": {
      "title": "My Song",
      "artists": ["My Artist"],
      "album": "My Album",
      "released": "July 29, 2026",
      "duration": "03:42",
      "cover_url": "https://example.com/cover.jpg",
      "label": "Independent"
    },
    "lyrics": "line one\nline two\nline three\nline four",
    "theme": "RosePine",
    "accent": true
  }' \
  --output custom.png
```

专辑的 `metadata` 将 `album`、`duration` 换成 `tracks` 数组即可。

## 音乐平台

Spotify 搜索和海报资料获取需要在
[Spotify Developer Dashboard](https://developer.spotify.com/dashboard) 创建应用，并在
根目录 `.env` 中配置：

```bash
cp .env.example .env
```

然后编辑 `.env`：

```dotenv
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
SPOTIFY_MARKET=US
```

重新执行 `make dev:api`，或用 `docker compose up -d --build` 重建服务。

随后可使用：

```text
GET /v1/search?query=Summer%20Breeze&type=track&provider=spotify&limit=5
GET /v1/search?query=Summer%20Breeze&type=track&provider=all&limit=5
```

`provider=all` 中的 `limit` 对每个来源分别生效；Spotify 单次最多返回 10 条。未配置
Spotify 时，`all` 会只返回 Deezer；明确指定 `provider=spotify` 则返回 HTTP 503。

生成接口统一使用 `provider + catalog_id`。Deezer 和 Spotify 是同等级 provider；
以后新增 Apple Music、QQ 音乐等平台时，也不需要改变请求结构。

Spotify 海报分支会保持封面原有构图和色彩，并隐藏 BeatPrints 内置的 Deezer 图标。后续可在
同一个平台渲染钩子中加入 Spotify 跳转码和署名；对外发布前应补齐跳转链接与 Spotify 标识。

## 接口

- `GET /health`
- `GET /v1/themes`
- `GET /v1/search?query=...&type=track&provider=spotify&limit=5`
- `POST /v1/posters/track`
- `POST /v1/posters/album`

两个生成接口成功时直接返回 `image/png`，失败时返回统一 JSON 错误体。每个请求使用独立
临时目录，响应完成后不会在服务端留下生成图片。远程封面限制为公网 HTTP(S) 地址、
JPEG/PNG/WebP 格式和 15 MB。

## Attribution

Poster generation is powered by
[BeatPrints by TrueMyst](https://github.com/TrueMyst/BeatPrints), licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
