import type {
  CatalogProvider,
  PosterKind,
  PosterPlatform,
  SearchResult,
  Theme,
} from "@/features/poster/types"

export type PosterHistorySnapshot = {
  provider: CatalogProvider
  catalogId: number | string
  selectedItem: SearchResult
  lyrics?: string
  instrumentalText?: string
  qrPlatform?: PosterPlatform
  platformUrl?: string
  indexing?: boolean
  shuffle?: boolean
}

export type PosterHistoryItem = {
  id: string
  createdAt: number
  kind: PosterKind
  title: string
  artists: string[]
  coverUrl?: string
  theme: Theme
  accent: boolean
  filename: string
  processTime?: string
  blob: Blob
  snapshot?: PosterHistorySnapshot
}

const DB_NAME = "beatprints_history_db"
const DB_VERSION = 1
const STORE_NAME = "posters"
const MAX_HISTORY_ITEMS = 20

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB is not supported in this environment"))
      return
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" })
        store.createIndex("createdAt", "createdAt", { unique: false })
      }
    }

    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function getAllHistory(): Promise<PosterHistoryItem[]> {
  try {
    const db = await openDatabase()
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readonly")
      const store = transaction.objectStore(STORE_NAME)
      const index = store.index("createdAt")
      const request = index.openCursor(null, "prev")
      const items: PosterHistoryItem[] = []

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result
        if (cursor) {
          items.push(cursor.value as PosterHistoryItem)
          cursor.continue()
        } else {
          resolve(items)
        }
      }

      request.onerror = () => reject(request.error)
    })
  } catch {
    return []
  }
}

export async function saveHistoryItem(
  item: PosterHistoryItem,
  maxItems = MAX_HISTORY_ITEMS,
): Promise<void> {
  try {
    const db = await openDatabase()
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readwrite")
      const store = transaction.objectStore(STORE_NAME)

      store.put(item)

      // Prune old items if count exceeds maxItems
      const index = store.index("createdAt")
      const countRequest = index.count()

      countRequest.onsuccess = () => {
        const total = countRequest.result
        if (total > maxItems) {
          const deleteCount = total - maxItems
          let deleted = 0
          const cursorRequest = index.openCursor(null, "next") // oldest first

          cursorRequest.onsuccess = (e) => {
            const cursor = (e.target as IDBRequest<IDBCursorWithValue>).result
            if (cursor && deleted < deleteCount) {
              cursor.delete()
              deleted += 1
              cursor.continue()
            }
          }
        }
      }

      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(transaction.error)
    })
  } catch {
    // Fail silently without blocking UI if storage is disabled or quota exceeded
  }
}

export async function deleteHistoryItem(id: string): Promise<void> {
  try {
    const db = await openDatabase()
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readwrite")
      const store = transaction.objectStore(STORE_NAME)
      store.delete(id)
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(transaction.error)
    })
  } catch {
    // Ignore storage deletion errors
  }
}

export async function clearAllHistory(): Promise<void> {
  try {
    const db = await openDatabase()
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readwrite")
      const store = transaction.objectStore(STORE_NAME)
      store.clear()
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(transaction.error)
    })
  } catch {
    // Ignore storage clear errors
  }
}
