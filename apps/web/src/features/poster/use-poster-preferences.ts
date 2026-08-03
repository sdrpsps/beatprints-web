import { useEffect, useMemo, useState } from "react"

import type {
  PosterKind,
  PosterPreferences,
  Theme,
} from "@/features/poster/types"

const PREFERENCES_KEY = "beatprints.preferences"
const defaultPreferences: PosterPreferences = {
  kind: "track",
  theme: "Light",
  accent: true,
}

function loadPreferences(): PosterPreferences {
  try {
    const value = localStorage.getItem(PREFERENCES_KEY)
    return value
      ? { ...defaultPreferences, ...JSON.parse(value) }
      : defaultPreferences
  } catch {
    return defaultPreferences
  }
}

export function usePosterPreferences() {
  const initial = useMemo(loadPreferences, [])
  const [kind, setKind] = useState<PosterKind>(initial.kind)
  const [theme, setTheme] = useState<Theme>(initial.theme)
  const [accent, setAccent] = useState(initial.accent)

  useEffect(() => {
    localStorage.setItem(
      PREFERENCES_KEY,
      JSON.stringify({ kind, theme, accent } satisfies PosterPreferences),
    )
  }, [kind, theme, accent])

  return { kind, setKind, theme, setTheme, accent, setAccent }
}
