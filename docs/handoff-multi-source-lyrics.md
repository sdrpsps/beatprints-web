# 多来源歌词交接

更新日期：2026-08-03

## 当前状态

歌词来源已具备可插拔的 API 边界，当前按 **QQ 音乐、网易云音乐、LRCLIB** 的顺序启用。
QQ 音乐同时是前后端默认歌词来源。
现有实现支持“从一个来源预览歌词，用户最终提交至多四行文字”的海报流程。当前需求
不需要独立歌词 Python 包，来源实现继续留在 BeatPrints API 的 integration 层。

已完成：

- `LyricsSourceAdapter` 与 `LyricsSourceResult` 定义在
  `apps/api/src/beatprints_api/integrations/lyrics/base.py`；来源负责检索及行规范化。
- `apps/api/src/beatprints_api/integrations/lyrics/registry.py` 是唯一启用列表。取消某一来源
  只需移除或注释该来源的一条导入，不应改动 service、route、DTO 或前端条件分支。
- 前端通过静态歌词 registry 维护来源、顺序和默认项；后端 registry 独立校验并执行来源适配器。
- `GET /v1/lyrics?provider=<selected-provider>&catalog_id=<selected-id>&source=<source-key>`
  基于用户已经选定的目录项目预览歌词，返回带稳定行号的非空行。
- `netease.py` 与 `qq_music.py` 各自拥有请求、响应解析和来源特有的失败处理；共享的标题、
  专辑、艺人、时长确认及 LRC 行规范化在 `common.py`，不包含来源名称条件。
- 自动候选必须通过标题、三秒以内时长误差，以及“艺人或专辑”中的至少一个可靠证据；
  Live、Remix 等版本冲突会被拒绝。本地化艺人名可由标题、专辑和时长共同确认。
- 普通 no-match 使用 `LyricsNotFoundError` 并由预览路由返回 404；网络、响应格式和来源
  错误仍返回上游失败，不能混为同一种结果。
- 海报请求最终提交 `lyrics` 文本，而不是让服务端重新选择行。空字符串表示明确不显示
  歌词；未传 `lyrics` 仅为兼容旧请求，才使用默认来源的旧选择行为。
- `apps/api/tests/test_lyrics_sources.py` 与 `apps/api/tests/test_api.py` 覆盖已启用来源、来源
  列表和预览契约。

当前用户路径：

1. 用户从 Deezer 或 Spotify 选择精确歌曲结果。
2. 前端从静态 registry 选择来源，再以原始 `provider + catalog_id` 请求某一来源预览。
3. 用户从该预览中最多选择四行。
4. 前端将最终四行文字作为 `lyrics` 发给 `POST /v1/posters/track`。

歌词来源与 catalog metadata provider、QR destination 完全独立。禁用 Spotify QR destination
不能影响 Spotify metadata 或歌词来源；任何 core service 都不能按平台名称、市场或地区分支。

## LrcApi 已移除

此前接入的 LrcApi 已从代码、配置、测试和前端来源选择中移除，不能直接恢复。

- 其公开端点在“未找到歌词”时返回 HTTP 404；旧适配器将所有 HTTP 错误转换为上游错误，
  API 路由因此把普通 no-match 表现为 502。
- 即使成功时可返回 LRC，严格标题/艺人匹配和公开服务稳定性不足以成为默认来源。
- 若未来重新评估它，必须先明确 no-match 与暂时故障的不同响应，并用真实录制 fixture
  覆盖成功、无结果、超时和格式异常；不能把 404 统一映射为 502。

## 当前包边界决定

暂不创建 `packages/beatprints-lyrics`。当前应用只消费纯文本行和 `instrumental` 状态，已有
`LyricsSourceAdapter`、`LyricsSourceResult` 与 registry 足以隔离三个来源。新来源仍必须各自
放在独立 integration 模块中，不能在 `services/lyrics.py`、路由或前端增加来源名条件。

只有在以下需求实际出现时再评估独立包：需要保留 LRC/ELRC/TTML 时间信息、多个应用共同
消费 provider、自动按优先级/轮换/质量聚合来源，或 API integration 合同无法继续保持简单。
届时包应只包含通用歌曲输入、结果格式、provider 合同、registry 和选择策略；网络 URL、
cookie、认证和 FastAPI 适配仍留在应用层。

## 来源筛选结论

- Musixmatch 需要付费，不纳入方案。
- LRC4StreamMusic/StreamMusic 所见方案依赖非官方 QQ Music 流程且许可与服务承诺不清晰，
  不应作为默认后端来源。
- `lyrics.ovh` 是可继续评估的 MIT 自托管候选，但接入前仍须审查其上游抓取来源、可用性和
  适用条款。
- Navidrome Lyrics Plugin 是架构参考，不是可直接调用的 HTTP lyrics service；其 Rust/WASM
  与 Navidrome host API 不应进入 BeatPrints 运行时。
- 网易云使用 `music.163.com/api/search/get` 与 `api/song/lyric/v1`；QQ 音乐使用
  `c.y.qq.com/soso/fcgi-bin/client_search_cp` 搜索和
  `c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg` 读取歌词。这些是未公开客户端接口，
  必须监控响应变化；请求不携带 cookie 或用户凭据。
- BeatPrints 只需要纯文本供用户选行，因此网易云只读取原始 `lrc`，不混入翻译/YRC；
  QQ 音乐请求 `nobase64=1` 的原始 LRC，不混入翻译歌词或逐字时间轴。

每个候选来源均需先确认许可证、公开使用条款、认证方式、地域可用性和失败语义。不得通过
用户 cookie、受限 token 或违反第三方条款的抓取方式取得歌词。

## UI 与 API 要求

前端静态 registry 维护来源可用性、顺序和默认项，并在没有至少两个启用来源时隐藏来源切换
控件。当前已有三个来源，切换控件会由 registry 数据驱动逻辑显示。每个来源的预览应清楚
对应当前选择的来源，但不要混合不同来源的行后再提交海报。

新来源需要与 LRCLIB 一致地处理：加载、无歌词、纯音乐、网络失败、未知/禁用来源、用户
切换来源、切换歌曲、禁用生成，以及最终四行提交。用户切换来源不会改变已选歌曲的标题、
艺人、封面、发行信息或 `provider + catalog_id`。

遵守前端软性规模要求：组件和 hooks 达到约 150 行时，按真实职责拆分，例如将来源加载、
歌词预览请求和行选择分别放在 focused hook/component 中；不要为了行数机械切碎。

## 验收与测试清单

每次变更来源架构时至少覆盖：

- registry：每个启用 provider、默认 provider、重复 key、未知 key、以及注释一条导入后的
  disabled path；
- provider：使用保留真实字段结构、歌词内容经过合成替换的 fixture 验证响应到
  `LyricsResult` 的规范化；
- orchestration：优先级/轮换/质量策略、无结果与网络故障的明确区分；
- API：精确 `provider + catalog_id` 预览、未知来源 404，以及来源异常
  的可预期响应；
- 前端：来源从静态 registry 读取，选中状态、加载/空/错误状态、最多四行限制，以及最终 `lyrics`
  请求体；
- 质量门：`uv run pytest apps/api/tests`、
  `pnpm --filter @beatprints/web lint`、`pnpm --filter @beatprints/web build`。

在生产镜像涉及依赖裁剪时，Dockerfile 还应保留应用导入检查，避免只在开发虚拟环境中通过。
