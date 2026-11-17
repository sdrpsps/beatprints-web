import type { SupportedLanguage } from "@/i18n/resources"

const summaryStart = "<!-- release-summary:start -->"
const summaryEnd = "<!-- release-summary:end -->"

export function localizedReleaseNotes(body: string, language: SupportedLanguage): string {
  const start = body.indexOf(summaryStart)
  const end = body.indexOf(summaryEnd, start + summaryStart.length)
  if (start < 0 || end < 0) return body

  const summary = body.slice(start + summaryStart.length, end)
  function section(locale: SupportedLanguage) {
    const beginMarker = `<!-- release-summary:${locale}:start -->`
    const endMarker = `<!-- release-summary:${locale}:end -->`
    const begin = summary.indexOf(beginMarker)
    const finish = summary.indexOf(endMarker, begin + beginMarker.length)
    if (begin < 0 || finish < 0) return ""
    return summary.slice(begin + beginMarker.length, finish).trim()
  }
  return section(language) || section("en") || body
}
