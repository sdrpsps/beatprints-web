# 用户更新说明

每个功能 PR 的 `## What's New` 必须包含 `### 简体中文`、`### 繁體中文`、`### English` 三节，以等价、面向用户的 Markdown 列表说明变化。纯内部修改每一节均填写 `None`。PR 校验会检查格式；Release Please 的自动发布 PR 不需要填写。校验无法判断翻译质量，请人工审核。

Release Please 创建或更新发布 PR 后，工作流按合并顺序收集上一版本以来关联到默认分支的 PR，把三种语言的摘要写入发布 PR 的 `<!-- release-summary:start -->` 与 `<!-- release-summary:end -->` 之间；Release Please 原有 commit 日志保留在后面，`CHANGELOG.md` 不受影响。合并发布 PR 后，Release Please 直接使用完整正文创建 GitHub Release。应用弹窗显示完整 Release 正文。没有用户可见更新时，摘要明确说明这一点。

汇总依赖 GitHub 将合并的 commit 关联到 PR。直接推送的提交、无说明或旧格式的 PR 不进入摘要；这些提交仍可能出现在原始日志中，但不保证包含每次提交。发布日志会列出跳过的 PR。

发布 PR 的检查会等待摘要写入，最多等待一分钟；如果仍未写入，检查会失败。合并前请确认检查通过。如果生成失败，修复原因并重新运行 Release Please 工作流。标记内的内容会在发布 PR 更新时重新生成，请勿手动编辑。对已发布的历史版本，仍可在 **Release Please** 工作流选择 **Run workflow** 并输入标签（例如 `v1.4.0`）刷新摘要。工作流使用 `RELEASE_PLEASE_TOKEN`，需要仓库 contents 和 pull requests 写入权限。历史版本需要有可从新标签的第一父提交历史找到的 `v*` 标签。

本地测试：`python3 -m unittest discover -s .github/tests -v`。
