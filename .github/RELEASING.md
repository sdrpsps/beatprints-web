# 用户更新说明

每个功能 PR 的 `## What's New` 必须包含 `### 简体中文`、`### 繁體中文`、`### English`、`### 日本語`、`### 한국어` 五节，以等价、面向用户的 Markdown 列表说明变化。纯内部修改每一节均填写 `None`。PR 校验会检查格式；Release Please 的自动发布 PR 不需要填写。校验无法判断翻译质量，请人工审核。

Release Please 创建或更新发布 PR 后，工作流按合并顺序收集上一版本以来关联到默认分支的 PR，把五种语言的摘要写入发布 PR 的 `<!-- release-summary:start -->` 与 `<!-- release-summary:end -->` 之间；Release Please 原有 commit 日志保留在后面，`CHANGELOG.md` 不受影响。合并发布 PR 后，Release Please 使用完整正文创建 Release 草稿及标签。应用弹窗显示当前界面语言的摘要；缺少当前语言时回退到英文，完全没有分语言摘要的旧版本显示原文。没有用户可见更新时，摘要明确说明这一点。

汇总依赖 GitHub 将合并的 commit 关联到 PR。旧的三语言 PR 仍会汇总，日语和韩语部分回退到该 PR 的英文内容；新 PR 必须填写全部五种语言。直接推送的提交、无说明或其他不符合格式的 PR 不进入摘要；这些提交仍可能出现在原始日志中，但不保证包含每次提交。发布日志会列出跳过的 PR。

发布 PR 的检查会等待摘要写入，最多等待一分钟；如果仍未写入，检查会失败。合并前请确认检查通过。如果生成失败，修复原因并重新运行 Release Please 工作流。标记内的内容会在发布 PR 更新时重新生成，请勿手动编辑。对已发布的历史版本，仍可在 **Release Please** 工作流选择 **Run workflow** 并输入标签（例如 `v1.4.0`）刷新摘要。工作流使用 `RELEASE_PLEASE_TOKEN`，需要仓库 contents 和 pull requests 写入权限。历史版本需要有可从新标签的第一父提交历史找到的 `v*` 标签。

## 发布检查和镜像

在 GitHub 的 `main` 分支保护规则或 ruleset 中，将 CI 的 **Application checks** 设为必需状态检查，并要求 PR 合并；该仓库设置需要管理员在工作流首次运行后配置。此检查运行后端测试和格式检查、前端 lint、构建及回归测试，以及发布脚本测试。发布 PR 也必须通过这些检查；仅版本变更的发布 PR 可以跳过重复的 Docker PR 构建。

Release Please 使用 `RELEASE_PLEASE_TOKEN` 创建标签和 Release 草稿。标签触发 Docker 工作流构建 amd64 和 arm64 镜像；发布任务检查两个架构的版本、提交和多架构清单，更新允许的镜像标签，然后才公开 Release。任一步失败时草稿会保留，不能将 GitHub Release 或镜像视为发布完成。发布后检查 Docker 工作流成功，以及版本标签和 `latest` 的两个架构均可拉取。

如果架构镜像已成功推送但清单或公开步骤失败，在默认分支上的 **Docker → Run workflow** 中输入 `recover_tag`（例如 `v1.5.0`）。恢复流程会重新检查版本和提交、重建清单，并在成功后公开草稿。若架构镜像缺失或不匹配，同时勾选 `rebuild`，以当前工作流构建该标签的代码后再恢复。**不要重跑使用旧版工作流的历史标签任务**：旧工作流可能覆盖 `latest`；使用当前工作流的恢复功能。

浮动标签只由相应范围内最新的正式版本更新：例如旧的 1.4 版本不会回退 `1` 或 `latest`，预发布版本不会更新任何浮动标签。版本专属标签和提交标签仍可用于定位各个构建。

本地测试：`uv run --locked pytest -q`、`make lint:api`、`pnpm --filter @beatprints/web lint`、`pnpm --filter @beatprints/web build`、三组前端回归测试，以及 `python3 -m unittest discover -s .github/tests -v`。
