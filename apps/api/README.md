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
处理所用的整数毫秒数。

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

歌曲和专辑元数据默认在每个 Web 进程中缓存 600 秒、每类最多 256 条，避免歌词预览与
海报生成重复请求音乐平台。可使用 `METADATA_CACHE_TTL_SECONDS` 和
`METADATA_CACHE_MAX_ENTRIES` 调整；多进程之间不共享缓存。

成功生成海报时，响应中的 `Server-Timing` 会分别报告 `queue`、`metadata`、`lyrics`、
`cover`、`palette`、`render` 和 `read` 耗时，统一使用整数毫秒，可用来区分排队、上游
网络和本地图像渲染瓶颈。`X-Process-Time` 仍表示整个 HTTP 请求的整数毫秒总耗时。

在 Nginx、Caddy 或云平台负载均衡器后部署时，将其反向代理到容器的 `8000` 端口即可。
应用已启用代理头处理，平台也可以通过 `PORT` 环境变量修改监听端口。

### 线上日志

服务会向标准输出写入一行一个 JSON 的结构化日志。`/v1/*` 请求包含 Request ID、路由
模板、状态码、耗时、响应大小和构建版本；成功生成海报时还会记录类型、主题、二维码平台
及各阶段耗时。日志不会记录查询参数、请求体、歌词、音乐链接或鉴权信息，健康检查和前端
静态资源也不会生成访问日志。

```bash
docker compose logs -f beatprints-api
```

可通过 `LOG_LEVEL` 环境变量调整最低日志级别，默认是 `INFO`。客户端报告错误时，可以把
响应头或错误界面中的 `X-Request-ID` 与服务端日志关联。

## 1. 只传歌曲查询词

服务会用 `provider` 指定的平台获取元数据和封面。歌词来源由独立适配器提供；使用
`/v1/lyrics/sources` 获取已启用来源，再将其 key 传给歌词预览。没有指定 `lyrics_range`
时，兼容接口仍通过默认来源选择前四行非空歌词。

前端歌词选择器可以先读取所选歌曲的规范化歌词：

```bash
curl "http://localhost:8000/v1/lyrics/sources"
curl "http://localhost:8000/v1/lyrics?provider=deezer&catalog_id=5416564&source=lrclib"
```

响应中的 `lines` 按原歌词顺序包含一开始编号的非空行；`instrumental=true` 表示纯音乐。
界面选择完成后应将最多四行最终文字作为 `lyrics` 提交，确保生成内容与选择一致；
提交空字符串表示明确不显示歌词，并避免触发后端默认选择前四行的兼容行为。

内置来源为 LRCLIB 和 LrcApi。LrcApi 默认使用其公开服务；通过 `LRC_API_BASE_URL`
可以改为自托管实例，通过 `LRC_API_AUTH` 传入自托管实例所需的 Authorization 值。

```bash
curl -X POST http://localhost:8000/v1/posters/track \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "provider": "spotify",
    "query": "Summer Breeze Piper",
    "theme": "Light",
    "accent": false
  }' \
  --output track.png
```

推荐把搜索结果中的 `provider + id` 原样传成 `provider + catalog_id`：

```json
{
  "provider": "spotify",
  "catalog_id": "7lp5evZr7qEDwlv5PS8b6i",
  "platform_links": {
    "apple_music": "https://music.apple.com/us/album/summer-breeze/1790520587",
    "qq_music": "https://y.qq.com/n/ryqq/songDetail/001example",
    "netease_music": "https://music.163.com/song?id=123456"
  },
  "qr_platform": "apple_music",
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
    "query": "Summer Breeze Piper",
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

## 海报中的音乐平台直达入口

歌曲和专辑海报接口都支持 `qr_platform + platform_links`。`qr_platform` 用来明确指定这张
海报显示哪个平台；未提供 `qr_platform` 时，海报不会显示任何平台标识或二维码：

```json
{
  "provider": "spotify",
  "catalog_id": "7lp5evZr7qEDwlv5PS8b6i",
  "qr_platform": "apple_music",
  "platform_links": {
    "spotify": "https://open.spotify.com/track/7lp5evZr7qEDwlv5PS8b6i",
    "apple_music": "https://music.apple.com/us/album/summer-breeze/1790520587",
    "qq_music": "https://y.qq.com/n/ryqq/songDetail/001example",
    "netease_music": "https://music.163.com/song?id=123456"
  }
}
```

上述请求只会显示 Apple Music 二维码，其他链接不会同时渲染。这样调用方可以保存一组跨平台
链接，并针对同一首歌曲分别生成不同平台版本的海报。

`qr_platform` 支持注册表中当前启用的目标平台（目前为 `spotify`、`apple_music`、`qq_music` 和
`netease_music`）。选定平台后，
`platform_links` 必须包含该平台的链接。链接支持平台网页地址、Universal Link 或 Deep
Link。推荐优先传平台分享功能生成的 HTTPS/Universal Link：扫码设备安装了对应 App 时通常
会直接唤起 App，未安装时仍可回退到网页。

使用 Spotify 作为 `provider`、同时明确选择
`"qr_platform": "spotify"` 时，可以省略 `platform_links.spotify`，服务会使用 Spotify
元数据返回的歌曲或专辑链接。所有目标平台都使用同一套链接匹配接口；`platform` 是注册表中
启用的目标键。启用列表集中在 `beatprints_api/integrations/destinations/registry.py`：

```bash
curl "http://localhost:8000/v1/platform-links/apple_music/options?provider=deezer&catalog_id=5416564&type=track"
```

该接口始终先读取未经改变的 `provider + catalog_id`，再使用所有目标平台共享的匹配规则。
平台适配器只负责检索、链接解析和 Spotify ISRC 等额外能力；统一引擎负责标题版本、艺人、
发行信息、时长、曲目数和歧义判断。响应同时包含可选的 `match` 和同次检索得到的 `candidates`，
不会把近似同名作品静默确认。调用方将成功结果的 `url` 写入对应 `platform_links.<platform>` 后生成海报。未指定
`qr_platform` 时，数据源是 Spotify 也不会自动显示二维码。

自动结果不存在、被用户拒绝或需要手动输入链接时，使用响应中的候选或解析端点：

```bash
curl --get "http://localhost:8000/v1/platform-links/spotify/resolve" \
  --data-urlencode "url=https://open.spotify.com/track/7lp5evZr7qEDwlv5PS8b6i"
```

`/options` 提供自动确认与可由用户确认的排序候选；`/resolve` 读取所选公开链接的当前资料，用于刷新目标
平台确认卡片。两者均支持四个平台，且不会改写海报使用的 Spotify / Deezer 来源资料、歌词或封面。

选择 Spotify 且链接是标准的 Spotify 歌曲或专辑链接时，海报左下角会使用 Spotify
提供的原生 Spotify Code PNG（可由 Spotify App 的“搜索 → 扫描”识别），而不是普通
方形二维码。服务会移除 Code 图像的白色底板，并用海报主题色绘制，因此能自然融入模板。
Spotify Code 由 Spotify 的 scannable 图服务生成，不需要额外的开发者凭据。不能解析为
标准 Spotify 歌曲或专辑链接时，服务会保留普通二维码作为兼容回退。

Apple Music、QQ 音乐和网易云音乐继续使用普通二维码。所有平台标记和二维码均使用同一套
海报主题色规则；平台之间只允许标记与编码格式不同，不能为 Apple Music 或其他平台另走封面
取色路径。二维码背景和 quiet zone 始终保持白色，以提高相机识别稳定性。

Apple Music 会使用 Apple Music Symbol 加二维码的紧凑组合，并与 Spotify Code 一样采用海报主题色，
以保持相同的视觉位置、比例和配色逻辑。它不是 App Clip Code；扫码仍会打开调用方提供的
Apple Music 链接，因此可由任意标准相机扫码。

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
APPLE_MUSIC_STOREFRONT=US
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

Spotify 海报分支会保持封面原有构图和色彩。BeatPrints 内置的 Deezer 图标现在默认隐藏，
只有明确提供 `qr_platform` 时才会在原位置显示指定平台的彩色二维码。Spotify 完整专辑响应
中的 `label` 已被官方标记为 deprecated，因此服务会先使用真实 `label`，字段缺失时再从
录音版权信息中提取厂牌；仍无法确定时留空，不显示误导性的 `Unknown Label`。

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
