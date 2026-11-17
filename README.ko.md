<div align="center">

# BeatPrints Web

**좋아하는 음악을 종이 위의 모습으로.**

실제 음악 카탈로그에서 정확한 곡이나 앨범을 찾고 가사와 플랫폼 링크를 선택해 다운로드, 보관 또는 인쇄할 수 있는 고해상도 PNG 포스터를 만드세요.

[BeatPrints Web](https://github.com/sdrpsps/beatprints-web)은 [TrueMyst / elysianmyst의 BeatPrints](https://github.com/TrueMyst/BeatPrints)를 기반으로 합니다. 원본 프로젝트가 포스터 조판과 렌더링을 담당하고, 이 프로젝트는 Web 제작 화면, HTTP API, 여러 음악 카탈로그 연동과 자체 호스팅 기능을 추가합니다.

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[빠른 시작](#빠른-시작) · [Docker 배포](#docker-배포) · [API 문서](apps/api/README.md) · [프론트엔드 가이드](apps/web/README.md)

</div>

![BeatPrints Web 화면](https://i.imgur.com/N4vE3QJ.jpg)

## 원본 BeatPrints와의 관계

[BeatPrints](https://github.com/TrueMyst/BeatPrints)는 TrueMyst / elysianmyst가 만든 음악 포스터 생성기로, 레이아웃, 테마, 글꼴, 색상과 PNG 렌더링을 담당합니다. 이 프로젝트는 원본 생성기를 그대로 사용하며 브라우저 제작 화면, FastAPI, 음악 서비스 연동과 자체 호스팅 기능을 추가합니다. 명령줄 생성기만 필요하다면 원본 프로젝트를 참고하세요.

BeatPrints Web은 원본 생성기에 다음 기능을 추가합니다.

- 브라우저에서 포스터 제작의 모든 단계를 완료할 수 있는 반응형 React 화면.
- 음악 카탈로그 검색, 가사 조회, 포스터 생성을 위한 FastAPI 서비스.
- QQ Music, NetEase Music, Spotify, Apple Music 카탈로그 연동과 QR 연결 대상 확인.
- 운영 환경용 Docker Compose 설정, 통합 멀티 아키텍처 이미지와 자동 릴리스 과정.

명령줄 생성기나 포스터 조판 엔진을 사용하려면 [TrueMyst/BeatPrints](https://github.com/TrueMyst/BeatPrints)를 참고하세요. 브라우저에서 사용하거나 HTTP 서비스로 배포하려면 이 프로젝트를 사용할 수 있습니다.

## BeatPrints Web이란

BeatPrints Web은 원본 BeatPrints를 기반으로 한 자체 호스팅 가능한 Web 앱입니다. 가상의 음악을 생성하지 않고 QQ Music, NetEase Music, Spotify 또는 Apple Music에서 실제 표지와 작품 정보를 가져옵니다. 정확한 버전을 확인하면 BeatPrints로 포스터를 생성합니다.

곡 포스터 제작 과정:

```text
곡 검색 → 정확한 버전 선택 → 가사 최대 네 줄 선택(선택 사항) → 플랫폼 링크 선택(선택 사항) → 모양 조정 → PNG 다운로드
```

앨범 포스터는 트랙 번호와 순서 섞기도 설정할 수 있습니다. 이미지는 브라우저로 직접 전달되며 서버에 저장되지 않습니다.

> [!IMPORTANT]
> **음악 정보의 소스**와 **포스터의 플랫폼 링크**는 서로 독립적입니다. `provider`는 음악 정보를 가져올 소스를, `qr_platform`은 Spotify, Apple Music, QQ Music 또는 NetEase Music 링크를 넣을지 결정합니다. 플랫폼을 선택하지 않으면 플랫폼 표시나 QR 코드가 나타나지 않습니다.

## 기능

- 곡 또는 앨범을 검색하고 표지, 아티스트, 발매 정보와 길이로 정확한 버전을 확인합니다.
- 곡 포스터에는 가사를 0~4줄 선택하거나 직접 입력하고, 앨범에는 트랙 번호와 순서 섞기를 설정합니다.
- Spotify Code 또는 다른 지원 플랫폼의 일반 QR 코드나 WeChat 코드를 추가합니다.
- 플랫폼 간 매칭은 ISRC 같은 안정적인 식별자를 우선합니다. 확실한 결과가 없으면 후보를 고르거나 링크를 직접 입력합니다.
- Light, Dark, Catppuccin, Gruvbox, Nord, RosePine, Everforest 테마와 표지에서 추출한 강조 색상을 제공합니다.
- 영어, 중국어 간체, 중국어 번체, 일본어, 한국어 화면을 지원합니다.
- 하나의 컨테이너 이미지에서 Web과 API를 함께 제공합니다.

## 빠른 시작

### 필요한 환경

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- pnpm 11

### 로컬 개발

```bash
git clone https://github.com/sdrpsps/beatprints-web.git
cd beatprints-web
cp .env.example .env
make setup
make dev
```

실행 후 다음 주소에 접속할 수 있습니다.

- Web: <http://localhost:5173>
- API: <http://localhost:8000>
- OpenAPI 문서: <http://localhost:8000/docs>

Spotify 검색은 선택 사항입니다. 사용하려면 `.env`에 `SPOTIFY_CLIENT_ID`와 `SPOTIFY_CLIENT_SECRET`을 설정하세요. Spotify 인증 정보를 설정하지 않아도 QQ Music, NetEase Music, Apple Music 검색을 사용할 수 있습니다.

WeChat 코드에는 QR 서비스가 필요합니다. Docker Compose는 이 서비스를 자동으로 시작합니다. 로컬 개발에서는 `WECHAT_QR_BASE_URL`을 설정하세요(예: `http://127.0.0.1:8080`). 설정하지 않으면 해당 옵션이 숨겨집니다. 일반 QR 코드에는 이 서비스가 필요 없으며 Spotify는 항상 Spotify Code를 사용합니다. 자세한 내용은 [API 문서](apps/api/README.md#本地启动)를 참고하세요.

### 주요 명령

```bash
make help         # 명령 목록 보기
make dev          # API와 Web 실행
make dev:api      # API만 실행
make dev:web      # Web만 실행
make test:api     # API 테스트
make lint:api     # Python 코드 검사
make build        # API와 Web 빌드
```

전체 프론트엔드 검사:

```bash
pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

## Docker 배포

FastAPI가 프론트엔드 파일도 제공하므로 `8000` 포트만 공개하면 됩니다.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

서비스 상태 확인:

```bash
curl http://localhost:8000/health
```

업데이트와 로그 확인:

```bash
git pull
docker compose up -d --build
docker compose logs -f beatprints-api
```

Nginx, Caddy 또는 Traefik을 컨테이너의 `8000` 포트로 연결하는 리버스 프록시로 사용하는 것을 권장합니다. `2280 × 3480` 고해상도 포스터 생성에는 메모리가 많이 필요합니다. 메모리 1 GB 서버에서는 다음 기본 동시 실행 설정을 유지하세요.

```dotenv
WEB_CONCURRENCY=1
MAX_CONCURRENT_JOBS=1
```

검색 엔진에 등록되는 페이지는 영어 홈페이지 `/`뿐입니다. 화면은 브라우저 언어를 감지하며 `/en/`, `/zh-CN/`, `/zh-TW/`, `/ja/`, `/ko/` 주소로 언어를 지정할 수도 있습니다. 명시적인 언어 주소가 브라우저 설정보다 우선합니다. 각 언어 주소는 `noindex`이며 정규 URL은 영어 홈페이지를 가리킵니다. 정규 URL, 사이트맵, 공유 URL은 `https://beatprints.bytespark.app`으로 고정되어 있습니다. 자체 배포 도메인을 검색에 등록하려면 빌드 전에 `apps/web/index.html`, `apps/web/public/robots.txt`, `apps/web/public/sitemap.xml`, `apps/web/tests/seo-regressions.mjs`를 함께 수정하세요.

### 인증

`API_KEY`가 비어 있으면 Web과 API가 공개됩니다. 값을 설정하면 보호된 `/v1` 엔드포인트에 Bearer Token이 필요합니다. 공개 프론트엔드 빌드에 장기 API 키를 넣지 마세요. 접근 제어가 필요하면 인증 계층, 리버스 프록시 또는 API 게이트웨이를 추가하고, API를 공개할 때는 속도 제한과 남용 방지 설정을 적용하세요.

## 설정

주요 환경 변수는 [`.env.example`](.env.example)에 설명되어 있습니다.

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `PORT` | API 수신 포트 | `8000` |
| `API_KEY` | `/v1` 엔드포인트의 선택적 Bearer Token | 비어 있음 |
| `CORS_ORIGINS` | 허용할 프론트엔드 출처, 여러 값은 쉼표로 구분 | 비어 있음 |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Spotify 검색과 정보 조회 활성화 | 비어 있음 |
| `METADATA_CACHE_TTL_SECONDS` | 메타데이터 캐시 유효 시간(초) | `600` |
| `MAX_CONCURRENT_JOBS` | 워커당 동시 포스터 생성 작업 수 | `1` |

## 프로젝트 구조

```text
.
├── apps/
│   ├── api/          # FastAPI, 음악 카탈로그 연동, 포스터 생성
│   └── web/          # React, Vite, Tailwind CSS, shadcn/ui 프론트엔드
├── docs/             # 제품 흐름과 구조 문서
├── packages/         # 프론트엔드 공유 패키지
├── Makefile          # 개발, 테스트, 빌드, 배포 공통 명령
├── pyproject.toml    # Python 프로젝트와 의존성
├── pnpm-workspace.yaml
└── docker-compose.yml
```

의존성 관리:

- Python 의존성은 루트의 `pyproject.toml`과 `uv.lock`으로 관리합니다.
- Web 의존성은 pnpm workspace와 `pnpm-lock.yaml`로 관리합니다.
- `Makefile`은 여러 앱에 걸친 공통 명령을 제공합니다.

추가 문서:

- [프론트엔드 개발 가이드](apps/web/README.md)
- [API 배포와 사용 예시](apps/api/README.md)
- [프론트엔드 제품 흐름과 API 매핑](docs/frontend-product-brief.md)

## API 개요

포스터 생성 성공 시 `image/png`를 직접 반환하는 경우를 제외하고, JSON 응답은 다음 형식입니다.

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

주요 엔드포인트:

```http
GET  /v1/search
GET  /v1/lyrics
GET  /v1/capabilities
GET  /v1/platform-links/{platform}/options
GET  /v1/platform-links/{platform}/resolve
POST /v1/posters/track
POST /v1/posters/album
```

지역을 지원하는 연동에서는 `GET /v1/capabilities`로 소스와 연결 대상의 지원 지역을 확인하고, 검색에서 선택한 소스 지역을 포스터 생성까지 유지합니다. 소스와 QR 연결 대상의 지역은 독립적이며 생략하면 `US`가 기본값입니다. 각 단계의 매개변수는 [지역 작업 흐름과 예시](apps/api/README.md#音乐平台)를 참고하세요.

전체 요청 형식, 플랫폼 간 매칭, 오류 처리와 `curl` 예시는 [BeatPrints API 문서](apps/api/README.md) 또는 서비스 실행 후 `/docs`에서 확인할 수 있습니다.

## 빌드와 릴리스

GitHub Actions는 Web과 API를 모두 포함한 멀티 아키텍처 이미지를 자동으로 빌드합니다.

```text
ghcr.io/sdrpsps/beatprints-web:latest
```

- Pull Request는 CI 검증을 위해 `linux/amd64` 이미지를 빌드하지만 게시하지 않습니다.
- `vX.Y.Z` 태그는 `linux/amd64`와 `linux/arm64` 이미지를 게시합니다.
- Release Please는 Conventional Commits에 따라 시맨틱 버전, 변경 내역, GitHub Releases를 관리합니다.

`fix:`는 패치, `feat:`는 마이너, `!` 또는 `BREAKING CHANGE:`가 포함된 커밋은 메이저 버전을 올립니다.

## 저작자 표시와 라이선스

이 프로젝트는 [TrueMyst / elysianmyst의 BeatPrints](https://github.com/TrueMyst/BeatPrints)를 기반으로 하며 WeChat 코드 생성에 [AnglerS888/kuima-generator](https://github.com/AnglerS888/kuima-generator)를 사용합니다.

라이선스는 [CC BY-NC-SA 4.0](LICENSE)이며 비상업적 용도로만 사용할 수 있습니다. 사용, 배포 또는 파생 작품 제작 시 저작자를 표시하고 같은 라이선스로 공유하세요. 상업적으로 사용하려면 원작자의 허가가 필요합니다.
