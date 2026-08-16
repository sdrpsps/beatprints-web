/**
 * Check if the browser supports sharing files via the Web Share API.
 */
export function canShareImage(blob?: Blob): boolean {
  if (
    typeof window === "undefined" ||
    typeof navigator === "undefined" ||
    !navigator.share
  ) {
    return false
  }

  if (blob && typeof navigator.canShare === "function") {
    try {
      const testFile = new File([blob], "poster.png", { type: "image/png" })
      return navigator.canShare({ files: [testFile] })
    } catch {
      return false
    }
  }

  return true
}

/**
 * Share a poster image file using the native OS share dialog.
 */
export async function shareImageBlob(
  blob: Blob,
  filename: string,
  title?: string,
  text?: string,
): Promise<boolean> {
  if (!navigator.share) {
    throw new Error("Web Share API is not supported in this environment.")
  }

  const pngFile = new File([blob], filename || "beatprints-poster.png", {
    type: "image/png",
  })

  if (navigator.canShare && !navigator.canShare({ files: [pngFile] })) {
    throw new Error("Sharing files is not supported by this browser.")
  }

  await navigator.share({
    title: title ?? "BeatPrints Poster",
    text: text ?? "Check out this music poster made with BeatPrints",
    files: [pngFile],
  })

  return true
}
