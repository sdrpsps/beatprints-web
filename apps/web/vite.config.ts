import { execFileSync } from "node:child_process"
import { mkdirSync, readFileSync, writeFileSync } from "node:fs"
import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { HomeGuide, HomeHero } from "./src/components/home-content.tsx"
import { homeContent, type HomeLanguage } from "./src/i18n/home.ts"
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

function escapeAttribute(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;")
}

function prerenderHomepages() {
  return {
    name: "prerender-homepages",
    apply: "build" as const,
    closeBundle() {
      const output = path.resolve(__dirname, "dist")
      const template = readFileSync(path.join(output, "index.html"), "utf8")
      const pages: { language: HomeLanguage; outputPath: string; indexable: boolean }[] = [
        { language: "en", outputPath: "", indexable: true },
        ...Object.keys(homeContent).map((language) => ({
          language: language as HomeLanguage,
          outputPath: language,
          indexable: false,
        })),
      ]
      for (const { language, outputPath, indexable } of pages) {
        const content = homeContent[language]
        const markup = renderToStaticMarkup(createElement(
          "main",
          null,
          createElement(HomeHero, { content }),
          createElement(HomeGuide, { content }),
        ))
        let html = template.replace('<html lang="en">', `<html lang="${language}">`)
        if (!indexable) {
          html = html.replace(
            /(<meta name="robots" content=")[^"]*(" \/>)/,
            "$1noindex, follow$2",
          )
        }
        html = html.replace(/<div id="root">[\s\S]*?<\/div>\s*<noscript>/, `<div id="root">${markup}</div>
    <noscript>`)
          .replace(/<noscript>[\s\S]*?<\/noscript>/, `<noscript>${escapeAttribute(content.noScript)}</noscript>`)
        const target = path.join(output, outputPath)
        mkdirSync(target, { recursive: true })
        writeFileSync(path.join(target, "index.html"), html)
      }
    },
  }
}

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(buildInfo.version),
    __GIT_SHA__: JSON.stringify(buildInfo.gitSha),
  },
  plugins: [react(), tailwindcss(), prerenderHomepages()],
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
