/**
 * Check if the current browser environment supports copying images to the clipboard.
 */
export function canCopyImageToClipboard(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    Boolean(navigator.clipboard?.write) &&
    typeof ClipboardItem !== "undefined"
  )
}

/**
 * Copy an image Blob directly to the user's clipboard.
 */
export async function copyImageBlobToClipboard(blob: Blob): Promise<boolean> {
  if (!canCopyImageToClipboard()) {
    throw new Error("Clipboard image write is not supported in this browser.")
  }

  // Ensure PNG mime type for clipboard item compatibility
  const pngBlob =
    blob.type === "image/png" ? blob : new Blob([blob], { type: "image/png" })

  const item = new ClipboardItem({
    "image/png": pngBlob,
  })

  await navigator.clipboard.write([item])
  return true
}

/**
 * Copy an image from a blob/object URL to the clipboard.
 */
export async function copyImageUrlToClipboard(url: string): Promise<boolean> {
  const response = await fetch(url)
  const blob = await response.blob()
  return copyImageBlobToClipboard(blob)
}
