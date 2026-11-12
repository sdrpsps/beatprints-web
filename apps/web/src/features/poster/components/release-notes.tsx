import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { buildInfo } from "@/lib/build-info"

const version = buildInfo.version.replace(/^v/, "")
const tag = `v${version}`
const storageKey = `beatprints.release-notes.${tag}`
const releaseUrl = `https://github.com/sdrpsps/beatprints-web/releases/tag/${encodeURIComponent(tag)}`

function unseenRelease() {
  if (!/^\d+\.\d+\.\d+$/.test(version)) return false
  try { return localStorage.getItem(storageKey) !== "seen" } catch { return false }
}

export function ReleaseNotes() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [body, setBody] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [autoShow] = useState(unseenRelease)

  useEffect(() => {
    if ((!open && !autoShow) || body !== null) return
    const controller = new AbortController()
    fetch(`https://api.github.com/repos/sdrpsps/beatprints-web/releases/tags/${encodeURIComponent(tag)}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Release unavailable")
        return response.json()
      })
      .then((release: { body?: unknown }) => {
        if (typeof release.body !== "string" || !release.body.trim()) throw new Error("Release notes unavailable")
        setBody(release.body)
        setError(false)
        if (autoShow) setOpen(true)
      })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
    return () => controller.abort()
  }, [open, autoShow, body, attempt])

  function onOpenChange(nextOpen: boolean) {
    setOpen(nextOpen)
    if (!nextOpen && body !== null) {
      try { localStorage.setItem(storageKey, "seen") } catch { /* Storage is optional. */ }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger render={<Button variant="link" size="sm" />}>{t("app.releaseNotes")}</DialogTrigger>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>{t("app.releaseTitle", { version })}</DialogTitle>
          <DialogDescription>{t("app.releaseDescription")}</DialogDescription>
        </DialogHeader>
        {body !== null ? (
          <div className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap break-words text-sm leading-relaxed">{body}</div>
        ) : error ? (
          <div className="flex flex-col items-start gap-2 text-sm">
            <p>{t("app.releaseError")}</p>
            <Button variant="outline" size="sm" onClick={() => { setError(false); setAttempt((value) => value + 1) }}>{t("app.releaseRetry")}</Button>
          </div>
        ) : <p className="text-sm" role="status">{t("app.releaseLoading")}</p>}
        <DialogFooter>
          <Button variant="outline" render={<a href={releaseUrl} target="_blank" rel="noreferrer" />}>{t("app.releaseView")}</Button>
          <DialogClose render={<Button />}>{t("app.releaseDismiss")}</DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
