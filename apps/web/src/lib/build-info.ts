declare const __APP_VERSION__: string
declare const __GIT_SHA__: string

export const buildInfo = {
  version: __APP_VERSION__,
  gitSha: __GIT_SHA__,
  shortGitSha: __GIT_SHA__ === "local" ? "local" : __GIT_SHA__.slice(0, 7),
}
