<div align="center">

# BeatPrints Web

**把喜歡的音樂，留下紙面的形狀。**

從真實音樂目錄中找到準確的歌曲或專輯，挑選歌詞與平台連結，產生可下載、收藏或列印的高清 PNG 海報。

[BeatPrints Web](https://github.com/sdrpsps/beatprints-web) 基於
[TrueMyst / elysianmyst 創作的 BeatPrints](https://github.com/TrueMyst/BeatPrints) 建立：
原專案負責音樂海報的核心排版與算圖，本專案為它補充 Web 創作介面、HTTP API、多平台音樂目錄整合和自行部署功能。

[English](../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[快速開始](#快速開始) · [Docker 部署](#docker-部署) · [API 文件](../apps/api/README.md) · [前端開發](../apps/web/README.md)

</div>

![BeatPrints Web 介面](https://i.imgur.com/N4vE3QJ.jpg)

## 與原始 BeatPrints 的關係

[BeatPrints](https://github.com/TrueMyst/BeatPrints) 是由 TrueMyst (@elysianmyst) 創作的音樂海報生成器，定義了海報的版面、主題、字體、調色盤與 PNG 算圖流程。本專案直接使用原始 BeatPrints 生成器，並非無關的同名專案，也沒有重新實作它的核心設計。

BeatPrints Web 在原生成器之外補充了：

- 可在瀏覽器中完成整個海報創作流程的響應式 React 介面；
- 用於搜尋音樂目錄、讀取歌詞和產生海報的 FastAPI 服務；
- QQ 音樂、網易雲音樂、Spotify、Apple Music 等多來源目錄整合，以及 QR 目的地解析；
- 適用於正式環境的 Docker Compose 設定、統一多架構容器映像檔與自動發布流程。

如果只需要命令列生成器，或想了解海報排版引擎，請參考 [TrueMyst/BeatPrints](https://github.com/TrueMyst/BeatPrints)。若希望在瀏覽器中使用 BeatPrints，或將它部署為 HTTP 服務，可以直接使用本專案。

## BeatPrints Web 是什麼

BeatPrints Web 是基於原始 BeatPrints 建立、可自行部署的 Web 應用程式。它不產生虛構的音樂內容，而是從 QQ 音樂、網易雲音樂、Spotify 或 Apple Music 取得真實封面與曲目資料，讓你確認準確版本後，再呼叫 BeatPrints 算出最終海報。

單曲海報的製作流程：

```text
搜尋歌曲 → 選擇準確版本 → 可選最多四行歌詞 → 可選一個平台連結 → 調整外觀 → 下載 PNG
```

專輯海報沿用相同流程，並提供曲目編號與隨機曲序選項。生成的海報圖片直接傳送至瀏覽器，伺服器不會儲存海報。

> [!IMPORTANT]
> **資料來源**與**海報平台連結**是兩個獨立的概念：`provider` 決定從 QQ 音樂、網易雲音樂、Spotify 或 Apple Music 取得資料；`qr_platform` 決定海報是否附帶 Spotify、Apple Music、QQ 音樂或網易雲音樂的掃描連結。未選擇平台時，海報不會顯示任何平台標誌或 QR Code。

## 功能

- **精確選擇音樂版本**：搜尋歌曲或專輯，透過封面、藝人、發行日期與長度確認準確版本。
- **挑選與編輯歌詞**：單曲海報支援選擇 0 至 4 行歌詞，也可手動輸入。
- **掃描前往音樂平台**：可加入 Spotify Code，或為 Apple Music、QQ 音樂、網易雲音樂選擇標準 QR Code 或微信葵花碼。
- **謹慎的跨平台比對**：優先使用 ISRC 等穩定識別碼；無法確認時提供排序後的候選清單或手動連結解析，不會悄悄選擇可信度不足的結果。
- **自訂海報外觀**：提供 Light、Dark、Catppuccin、Gruvbox、Nord、RosePine 與 Everforest 主題，並可使用封面擷取的強調色。
- **單曲與專輯模式**：可製作單曲或整張專輯海報，專輯另支援曲目編號與隨機曲序。
- **多語言介面**：支援英文、簡體中文、繁體中文、日文與韓文。
- **Web 與 API 一體部署**：單一容器映像檔同時提供 React 前端與 FastAPI 後端。

## 快速開始

### 環境需求

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- pnpm 11

### 本機開發

```bash
git clone https://github.com/sdrpsps/beatprints-web.git
cd beatprints-web

cp .env.example .env
make setup
make dev
```

啟動後可以存取：

- Web：<http://localhost:5173>
- API：<http://localhost:8000>
- OpenAPI 文件：<http://localhost:8000/docs>

Spotify 搜尋是可選功能。需要時，在 `.env` 中設定 `SPOTIFY_CLIENT_ID` 與 `SPOTIFY_CLIENT_SECRET`；未設定 Spotify 憑證時，仍可使用 QQ 音樂、網易雲音樂及 Apple Music 搜尋。

微信葵花碼需要 QR 服務。Docker Compose 會自動啟動；本機開發時可用 `WECHAT_QR_BASE_URL` 指定服務位址（例如 `http://127.0.0.1:8080`），未設定時會隱藏微信選項。部署詳情請參閱 [API 文件](../apps/api/README.md#本地启动)。標準 QR Code 不需要此服務；Spotify 一律使用 Spotify Code。

### 常用命令

```bash
make help         # 查看所有可用命令
make dev          # 同時啟動 API 與 Web
make dev:api      # 只啟動 FastAPI 後端
make dev:web      # 只啟動 Vite 前端
make test:api     # 執行 API 測試
make lint:api     # 檢查 Python 格式與程式碼
make build        # 建置 API 與 Web
```

完整前端檢查：

```bash
pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

## Docker 部署

本專案提供單容器部署方案：前端靜態檔案由 FastAPI 一併提供，對外只需開放 `8000` 連接埠。

英文首頁 `/` 是唯一提交搜尋收錄的頁面。介面會偵測瀏覽器語言，也可使用 `/en/`、`/zh-CN/`、`/zh-TW/`、`/ja/` 和 `/ko/` 指定語言；明確的語言網址優先於瀏覽器設定。這些語言網址標記為 `noindex`，規範網址指向英文首頁。規範網址、網站地圖與分享網址固定使用 `https://beatprints.bytespark.app`。若自行部署時需要以自己的網域收錄，請在建置前同步修改 `apps/web/index.html`、`apps/web/public/robots.txt`、`apps/web/public/sitemap.xml` 以及 `apps/web/tests/seo-regressions.mjs` 中的網域。

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

檢查服務狀態：

```bash
curl http://localhost:8000/health
```

更新與查看記錄：

```bash
git pull
docker compose up -d --build
docker compose logs -f beatprints-api
```

建議使用 Nginx、Caddy 或 Traefik 反向代理到容器的 `8000` 連接埠。產生 `2280 × 3480` 高清海報會消耗較多記憶體；1 GB 記憶體的伺服器建議保持以下預設並行設定：

```dotenv
WEB_CONCURRENCY=1
MAX_CONCURRENT_JOBS=1
```

### 驗證

`API_KEY` 留空時，Web 介面與 API 均可公開存取。設定 `API_KEY` 後，受保護的 `/v1` 端點需要 Bearer Token。

請勿將長期有效的 API 金鑰嵌入公開的 Vite 前端建置。需要存取控制的正式環境應在應用程式前方加入驗證層、反向代理或 API 閘道；若直接公開 API，請設定適當的速率限制與防濫用措施。

## 設定

主要環境變數記錄在 [`.env.example`](../.env.example)：

| 變數 | 用途 | 預設值 |
| --- | --- | --- |
| `PORT` | API 監聽連接埠 | `8000` |
| `API_KEY` | `/v1` 端點的可選 Bearer Token | 留空 |
| `CORS_ORIGINS` | 允許的前端來源，多個值以逗號分隔 | 留空 |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | 啟用 Spotify 搜尋與資料取得 | 留空 |
| `METADATA_CACHE_TTL_SECONDS` | 資料快取時間（秒） | `600` |
| `MAX_CONCURRENT_JOBS` | 每個程序同時生成海報的最大工作數 | `1` |

## 專案結構

```text
.
├── apps/
│   ├── api/          # FastAPI、音樂目錄整合與海報生成
│   └── web/          # React、Vite、Tailwind CSS 與 shadcn/ui 前端
├── docs/             # 產品流程與架構文件
├── packages/         # 前端共用套件
├── Makefile          # 開發、測試、建置與部署入口
├── pyproject.toml    # Python 專案與相依套件
├── pnpm-workspace.yaml
└── docker-compose.yml
```

相依套件管理：

- Python 相依套件由根目錄的 `pyproject.toml` 與 `uv.lock` 管理。
- Web 相依套件由 pnpm workspace 與 `pnpm-lock.yaml` 管理。
- `Makefile` 負責統一執行跨專案命令。

進一步閱讀：

- [前端開發指南](../apps/web/README.md)
- [API 部署與呼叫範例](../apps/api/README.md)
- [前端產品流程與 API 對應](frontend-product-brief.md)

## API 概覽

除直接回傳 `image/png` 的海報生成端點外，所有 JSON 回應都使用相同格式：

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

主要端點：

```http
GET  /v1/search
GET  /v1/lyrics
GET  /v1/capabilities
GET  /v1/platform-links/{platform}/options
GET  /v1/platform-links/{platform}/resolve
POST /v1/posters/track
POST /v1/posters/album
```

支援地區的整合可透過 `GET /v1/capabilities` 查詢來源與目標各自支援的地區。呼叫方應從搜尋到生成海報持續保留所選來源地區；來源與 QR 目的地地區彼此獨立，省略時預設為 `US`。各步驟的參數與範例見[地區工作流程](../apps/api/README.md#音乐平台)。

完整請求格式、跨平台比對、錯誤處理與 `curl` 範例請參閱 [BeatPrints API 文件](../apps/api/README.md)，或在服務啟動後開啟 `/docs`。

## 建置與發布

GitHub Actions 自動建置同時包含 Web 與 API 的多架構容器映像檔：

```text
ghcr.io/sdrpsps/beatprints-web:latest
```

- Pull Request 會建置 `linux/amd64` 映像檔以供 CI 驗證，但不會推送。
- `vX.Y.Z` 標籤會發布 `linux/amd64` 與 `linux/arm64` 映像檔。
- Release Please 根據 Conventional Commits 管理語意化版本、更新日誌與 GitHub Releases。

版本規則：`fix:` 遞增修訂版本，`feat:` 遞增次要版本，包含 `!` 或 `BREAKING CHANGE:` 的提交遞增主要版本。

## 致謝與授權

本專案基於 [TrueMyst / elysianmyst 創作的 BeatPrints](https://github.com/TrueMyst/BeatPrints)，並保留對原專案的署名。

微信葵花碼使用 [AnglerS888/kuima-generator](https://github.com/AnglerS888/kuima-generator) 產生，感謝其作者與貢獻者。

本專案採用 [CC BY-NC-SA 4.0](../LICENSE)，僅供非商業使用。使用、散布或製作衍生作品時請保留署名並以相同授權分享；商業使用前請取得原作者授權。
