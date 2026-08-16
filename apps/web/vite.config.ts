import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"
import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

const apiProxyTarget =
  process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000"

const projectRoot = path.resolve(__dirname, "../..")

function readVersionFile() {
  return readFileSync(path.join(projectRoot, "VERSION"), "utf8").trim()
}

function git(command: string[]) {
  try {
    return execFileSync("git", command, {
      cwd: projectRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim()
  } catch {
    return undefined
  }
}

function normalizeVersion(value: string) {
  return value.replace(/^v/i, "")
}

function resolveBuildInfo() {
  const version = normalizeVersion(process.env.VITE_APP_VERSION?.trim() || readVersionFile())
  const injectedSha = process.env.VITE_GIT_SHA?.trim()

  if (injectedSha) {
    return { gitSha: injectedSha, version: `v${version}` }
  }

  const gitSha = git(["rev-parse", "HEAD"]) ?? "local"
  const description = git(["describe", "--tags", "--always", "--dirty"])
  const displayVersion = description?.startsWith("v")
    ? description
    : `v${version}-dev${
        gitSha === "local"
          ? ""
          : `+${gitSha.slice(0, 7)}${description?.endsWith("-dirty") ? ".dirty" : ""}`
      }`

  return { gitSha, version: displayVersion }
}

const buildInfo = resolveBuildInfo()

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(buildInfo.version),
    __GIT_SHA__: JSON.stringify(buildInfo.gitSha),
  },
  plugins: [react(), tailwindcss()],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes("node_modules")) {
            if (
              id.includes("react") ||
              id.includes("react-dom") ||
              id.includes("scheduler")
            ) {
              return "vendor-react"
            }
            if (id.includes("@base-ui")) {
              return "vendor-base-ui"
            }
            if (id.includes("lucide-react")) {
              return "vendor-icons"
            }
            if (id.includes("i18next")) {
              return "vendor-i18n"
            }
            return "vendor"
          }
        },
      },
    },
  },
  server: {
    proxy: {
      "/v1": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      "/health": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
