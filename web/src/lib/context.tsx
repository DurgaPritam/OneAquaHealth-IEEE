import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { DataClient } from './client'
import { db, type LocalDb } from './db'
import { getObserverCode } from './observer'
import { pendingCount, syncOutbox, type SyncReport } from './queue'

interface AppState {
  client: DataClient
  store: LocalDb
  observerId: string
  online: boolean
  pending: number
  syncing: boolean
  lastSync: SyncReport | null
  sync: () => Promise<void>
  refreshPending: () => Promise<void>
}

const Ctx = createContext<AppState | null>(null)

export function AppProvider({ client, store = db, children }: { client: DataClient; store?: LocalDb; children: ReactNode }) {
  const [observerId] = useState(() => getObserverCode())
  const [online, setOnline] = useState(() => (typeof navigator === 'undefined' ? true : navigator.onLine))
  const [pending, setPending] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState<SyncReport | null>(null)

  const refreshPending = useCallback(async () => setPending(await pendingCount(store)), [store])

  const sync = useCallback(async () => {
    setSyncing(true)
    try {
      setLastSync(await syncOutbox(client, store))
    } finally {
      setSyncing(false)
      await refreshPending()
    }
  }, [client, store, refreshPending])

  useEffect(() => {
    void refreshPending()
    const up = () => {
      setOnline(true)
      void sync()
    }
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => {
      window.removeEventListener('online', up)
      window.removeEventListener('offline', down)
    }
  }, [refreshPending, sync])

  const value = useMemo(
    () => ({ client, store, observerId, online, pending, syncing, lastSync, sync, refreshPending }),
    [client, store, observerId, online, pending, syncing, lastSync, sync, refreshPending],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useApp(): AppState {
  const value = useContext(Ctx)
  if (!value) throw new Error('useApp must be used inside AppProvider')
  return value
}
