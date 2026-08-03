import type { PosterDestination } from "@/features/poster/destinations/types"

const destinations = new Map<string, PosterDestination>()

export function registerDestination(destination: PosterDestination) {
  destinations.set(destination.key, destination)
  return destination
}

export function enabledDestinations() {
  return [...destinations.values()].sort(
    (left, right) => left.order - right.order,
  )
}

export function getDestination(key: string) {
  return destinations.get(key)
}
