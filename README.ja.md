<div align="center">

# BeatPrints Web

**お気に入りの音楽を、紙の上のかたちに。**

実際の音楽カタログから曲やアルバムの正しい作品を選び、歌詞やサービスへのリンクを添えて、ダウンロード・保存・印刷できる高解像度 PNG ポスターを作成します。

[BeatPrints Web](https://github.com/sdrpsps/beatprints-web) は [TrueMyst / elysianmyst の BeatPrints](https://github.com/TrueMyst/BeatPrints) を基にしています。上流プロジェクトがポスターの組版とレンダリングを担い、本プロジェクトは Web 作成画面、HTTP API、複数の音楽カタログ連携、セルフホスト機能を追加します。

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[クイックスタート](#クイックスタート) · [Docker でのデプロイ](#docker-でのデプロイ) · [API ドキュメント](apps/api/README.md) · [フロントエンドガイド](apps/web/README.md)

</div>

![BeatPrints Web の画面](https://i.imgur.com/N4vE3QJ.jpg)

## オリジナルの BeatPrints との関係

[BeatPrints](https://github.com/TrueMyst/BeatPrints) は TrueMyst / elysianmyst による音楽ポスタージェネレーターです。ポスターのレイアウト、テーマ、書体、配色、PNG 出力を担います。本プロジェクトはこのジェネレーターをそのまま使用し、ブラウザ向けの作成画面、FastAPI、音楽サービス連携、セルフホスト機能を追加しています。コマンドライン版のみが必要な場合は上流プロジェクトをご覧ください。

BeatPrints Web は元のジェネレーターに次の機能を追加します。

- ブラウザでポスター作成を完結できるレスポンシブな React 画面。
- 音楽カタログの検索、歌詞の取得、ポスター生成を行う FastAPI サービス。
- QQ Music、NetEase Music、Spotify、Apple Music のカタログ連携と QR リンク先の解決。
- 本番向け Docker Compose、統合マルチアーキテクチャイメージ、自動リリースフロー。

コマンドラインジェネレーターやポスター組版エンジンについては [TrueMyst/BeatPrints](https://github.com/TrueMyst/BeatPrints) を、ブラウザや HTTP サービスとしての利用には本プロジェクトをご利用ください。

## BeatPrints Web とは

BeatPrints Web は元の BeatPrints を基にしたセルフホスト可能な Web アプリです。架空の音楽を生成するのではなく、QQ Music、NetEase Music、Spotify、Apple Music の実際のジャケットと作品情報を取得し、正しい作品を確認した後に BeatPrints でポスターを作成します。

楽曲ポスターの作成手順：

```text
曲を検索 → 正しい作品を選択 → 歌詞を最大4行選択（任意） → リンク先を選択（任意） → 外観を調整 → PNG をダウンロード
```

アルバムポスターでは曲番号や曲順のシャッフルも設定できます。画像はブラウザに直接送信され、サーバーには保存されません。

> [!IMPORTANT]
> **作品情報の取得元**と**ポスターのリンク先**は別々です。`provider` は音楽情報の取得元を、`qr_platform` は Spotify、Apple Music、QQ Music、NetEase Music へのリンクの有無を指定します。リンク先を選ばなければ、プラットフォームのマークや QR コードは表示されません。

## 機能

- 曲やアルバムを検索し、ジャケット、アーティスト、発売情報、長さで作品を確認。
- 楽曲ポスターに歌詞を0〜4行選択または手入力。アルバムでは曲番号とシャッフルに対応。
- Spotify Code、または他の対応サービス向けの標準 QR コードや WeChat コードを追加。
- サービス間の照合では ISRC などの識別子を優先。確定できない場合は候補を選ぶかリンクを手動入力。
- Light、Dark、Catppuccin、Gruvbox、Nord、RosePine、Everforest テーマと、ジャケットから抽出したアクセントカラーに対応。
- 画面は英語、簡体字中国語、繁体字中国語、日本語、韓国語で利用可能。
- 単一のコンテナイメージで Web と API を提供。

## クイックスタート

### 必要な環境

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- pnpm 11

### ローカル開発

```bash
git clone https://github.com/sdrpsps/beatprints-web.git
cd beatprints-web
cp .env.example .env
make setup
make dev
```

起動後は次の URL にアクセスできます。

- Web: <http://localhost:5173>
- API: <http://localhost:8000>
- OpenAPI ドキュメント: <http://localhost:8000/docs>

Spotify の検索は任意です。必要な場合は `.env` に `SPOTIFY_CLIENT_ID` と `SPOTIFY_CLIENT_SECRET` を設定してください。Spotify の認証情報がなくても QQ Music、NetEase Music、Apple Music の検索を利用できます。

WeChat コードには QR サービスが必要です。Docker Compose は自動的に起動します。ローカル開発では `WECHAT_QR_BASE_URL`（例：`http://127.0.0.1:8080`）を設定してください。未設定の場合、この選択肢は非表示になります。標準 QR コードにこのサービスは不要で、Spotify は常に Spotify Code を使用します。詳細は [API ドキュメント](apps/api/README.md#本地启动) を参照してください。

### 主なコマンド

```bash
make help         # コマンド一覧
make dev          # API と Web を起動
make dev:api      # API のみ起動
make dev:web      # Web のみ起動
make test:api     # API のテスト
make lint:api     # Python のチェック
make build        # API と Web をビルド
```

フロントエンドの完全なチェック：

```bash
pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

## Docker でのデプロイ

FastAPI がフロントエンドも配信するため、公開するポートは `8000` のみです。

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

サービスの状態を確認：

```bash
curl http://localhost:8000/health
```

更新とログの確認：

```bash
git pull
docker compose up -d --build
docker compose logs -f beatprints-api
```

Nginx、Caddy、Traefik などを使い、コンテナのポート `8000` にリバースプロキシすることを推奨します。`2280 × 3480` の高解像度ポスターの生成には多くのメモリが必要です。1 GB のサーバーでは以下の既定の並行設定を推奨します。

```dotenv
WEB_CONCURRENCY=1
MAX_CONCURRENT_JOBS=1
```

検索対象は英語のホームページ `/` のみです。画面はブラウザの言語を検出し、`/en/`、`/zh-CN/`、`/zh-TW/`、`/ja/`、`/ko/` で言語を指定することもできます。明示的な URL はブラウザ設定より優先されます。各言語 URL は `noindex` とし、正規 URL は英語のホームページを指します。正規 URL、サイトマップ、共有 URL は `https://beatprints.bytespark.app` に固定されています。独自ドメインで検索に掲載する場合は、ビルド前に `apps/web/index.html`、`apps/web/public/robots.txt`、`apps/web/public/sitemap.xml`、`apps/web/tests/seo-regressions.mjs` を更新してください。

### 認証

`API_KEY` が空の場合、Web と API は公開されます。設定すると保護された `/v1` エンドポイントには Bearer Token が必要です。公開フロントエンドのビルドに長期 API キーを埋め込まないでください。アクセス制御が必要な場合は認証レイヤー、リバースプロキシ、API ゲートウェイを追加し、公開 API にはレート制限などを設定してください。

## 設定

主な環境変数は [`.env.example`](.env.example) に記載されています。

| 変数 | 説明 | 既定値 |
| --- | --- | --- |
| `PORT` | API の待受ポート | `8000` |
| `API_KEY` | `/v1` エンドポイント用の任意の Bearer Token | 空欄 |
| `CORS_ORIGINS` | 許可するフロントエンドのオリジン。複数はカンマ区切り | 空欄 |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Spotify 検索と情報取得を有効化 | 空欄 |
| `METADATA_CACHE_TTL_SECONDS` | メタデータキャッシュの有効期間（秒） | `600` |
| `MAX_CONCURRENT_JOBS` | ワーカーごとのポスター生成の最大並行数 | `1` |

## プロジェクト構成

```text
.
├── apps/
│   ├── api/          # FastAPI、音楽カタログ連携、ポスター生成
│   └── web/          # React、Vite、Tailwind CSS、shadcn/ui フロントエンド
├── docs/             # 製品フローと設計資料
├── packages/         # フロントエンド共有パッケージ
├── Makefile          # 開発、テスト、ビルド、デプロイの共通コマンド
├── pyproject.toml    # Python プロジェクトと依存関係
├── pnpm-workspace.yaml
└── docker-compose.yml
```

依存関係の管理：

- Python はルートの `pyproject.toml` と `uv.lock` で管理します。
- Web は pnpm workspace と `pnpm-lock.yaml` で管理します。
- `Makefile` はアプリをまたぐコマンドをまとめます。

関連資料：

- [フロントエンド開発ガイド](apps/web/README.md)
- [API のデプロイと呼び出し例](apps/api/README.md)
- [フロントエンドの製品フローと API 対応](docs/frontend-product-brief.md)

## API の概要

成功時に `image/png` を直接返すポスター生成以外の JSON レスポンスは次の形式です。

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

主なエンドポイント：

```http
GET  /v1/search
GET  /v1/lyrics
GET  /v1/capabilities
GET  /v1/platform-links/{platform}/options
GET  /v1/platform-links/{platform}/resolve
POST /v1/posters/track
POST /v1/posters/album
```

地域対応の連携では `GET /v1/capabilities` から取得元とリンク先それぞれの対応地域を確認し、検索時に選択した取得元の地域をポスター生成まで保持します。取得元と QR リンク先の地域は独立しており、省略時は `US` です。各手順のパラメーターは[地域のワークフローと使用例](apps/api/README.md#音乐平台)をご覧ください。

完全なリクエスト形式、サービス間の照合、エラー処理、`curl` の例は [API ドキュメント](apps/api/README.md) または起動後の `/docs` を参照してください。

## ビルドとリリース

GitHub Actions は Web と API の両方を含むマルチアーキテクチャイメージを自動的にビルドします。

```text
ghcr.io/sdrpsps/beatprints-web:latest
```

- Pull Request は CI 検証用に `linux/amd64` イメージをビルドし、公開はしません。
- `vX.Y.Z` タグは `linux/amd64` と `linux/arm64` のイメージを公開します。
- Release Please は Conventional Commits に基づき、セマンティックバージョン、変更履歴、GitHub Releases を管理します。

`fix:` はパッチ、`feat:` はマイナー、`!` または `BREAKING CHANGE:` を含むコミットはメジャーバージョンを更新します。

## 謝辞とライセンス

本プロジェクトは [TrueMyst / elysianmyst の BeatPrints](https://github.com/TrueMyst/BeatPrints) を基にしており、WeChat コードの生成には [AnglerS888/kuima-generator](https://github.com/AnglerS888/kuima-generator) を使用しています。

ライセンスは [CC BY-NC-SA 4.0](LICENSE) で、非商用利用に限られます。利用・再配布・派生作品の作成時は作者を明記し、同じライセンスで共有してください。商用利用には原作者の許諾が必要です。
