import { Combobox as ComboboxPrimitive } from "@base-ui/react/combobox"
import { useVirtualizer } from "@tanstack/react-virtual"
import { useCallback, useImperativeHandle, useRef } from "react"

import { ComboboxItem, ComboboxList } from "@/components/ui/combobox"

export type Region = { code: string; flag: string; name: string; label: string; search: string }
export type RegionVirtualizer = ReturnType<typeof useVirtualizer<HTMLDivElement, Element>>

export function RegionList({ open, virtualizerRef }: {
  open: boolean
  virtualizerRef: React.RefObject<RegionVirtualizer | null>
}) {
  const regions = ComboboxPrimitive.useFilteredItems<Region>()
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const virtualizer = useVirtualizer({
    enabled: open,
    count: regions.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 40,
    overscan: 5,
    paddingStart: 8,
    paddingEnd: 8,
    scrollPaddingStart: 8,
    scrollPaddingEnd: 8,
  })
  useImperativeHandle(virtualizerRef, () => virtualizer)
  const setScrollElement = useCallback((element: HTMLDivElement | null) => {
    scrollRef.current = element
    if (element) virtualizer.measure()
  }, [virtualizer])

  return (
    <ComboboxList className="min-h-0 p-0">
      {regions.length > 0 && (
        <div
          ref={setScrollElement}
          role="presentation"
          className="max-h-64 overflow-y-auto overscroll-contain px-2 [scrollbar-width:thin] [scrollbar-color:var(--muted-foreground)_transparent] [&::-webkit-scrollbar]:block [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-2 [&::-webkit-scrollbar-thumb]:border-solid [&::-webkit-scrollbar-thumb]:border-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/50 [&::-webkit-scrollbar-thumb]:bg-clip-padding"
          style={{ height: Math.min(256, virtualizer.getTotalSize()) }}
        >
          <div role="presentation" className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((virtualItem) => {
              const region = regions[virtualItem.index]
              return (
                <ComboboxItem
                  key={region.code}
                  value={region}
                  index={virtualItem.index}
                  aria-setsize={regions.length}
                  aria-posinset={virtualItem.index + 1}
                  className="min-h-10 gap-3 py-2 pr-9 pl-2.5 data-selected:bg-secondary/60"
                  style={{ position: "absolute", top: 0, left: 0, height: virtualItem.size, transform: `translateY(${virtualItem.start}px)` }}
                >
                  <span aria-hidden="true" className="w-6 shrink-0 text-center text-lg leading-none">{region.flag}</span>
                  <span className="min-w-0 flex-1 truncate">{region.name}</span>
                  <span className="font-utility text-[0.65rem] tracking-wide text-muted-foreground">{region.code}</span>
                </ComboboxItem>
              )
            })}
          </div>
        </div>
      )}
    </ComboboxList>
  )
}
