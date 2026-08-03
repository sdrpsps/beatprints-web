import { useState } from "react"

export function useAlbumOptions(markOutputStale: () => void) {
  const [indexing, setIndexingState] = useState(true)
  const [shuffle, setShuffleState] = useState(false)

  return {
    indexing,
    setIndexing: (value: boolean) => {
      setIndexingState(value)
      markOutputStale()
    },
    shuffle,
    setShuffle: (value: boolean) => {
      setShuffleState(value)
      markOutputStale()
    },
  }
}
