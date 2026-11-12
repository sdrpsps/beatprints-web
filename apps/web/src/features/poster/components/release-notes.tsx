import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { Button } from "@/components/ui/button"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { fetchReleaseNotes } from "@/features/poster/api"
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
    let timedOut = false
    const timer = window.setTimeout(() => { timedOut = true; controller.abort() }, 10000)
    fetchReleaseNotes(version, controller.signal)
      .then((release) => {
        if (typeof release.body !== "string" || !release.body.trim()) throw new Error("Release notes unavailable")
        setBody(release.body)
        setError(false)
        if (autoShow) setOpen(true)
      })
      .catch(() => { if (!controller.signal.aborted || timedOut) setError(true) })
      .finally(() => window.clearTimeout(timer))
    return () => { window.clearTimeout(timer); controller.abort() }
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
          <div className="max-h-[50vh] overflow-auto break-words text-sm leading-relaxed [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_h1]:mt-4 [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:mt-4 [&_h2]:text-base [&_h2]:font-semibold [&_h3]:mt-4 [&_h3]:font-semibold [&_li]:pl-1 [&_ol]:my-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-3 [&_pre]:overflow-auto [&_pre]:rounded [&_pre]:bg-muted [&_pre]:p-3 [&_ul]:my-3 [&_ul]:list-disc [&_ul]:pl-5 [&>:first-child]:mt-0">
            <Markdown
              remarkPlugins={[remarkGfm]}
              components={{ a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}
            >
              {body}
            </Markdown>
          </div>
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
