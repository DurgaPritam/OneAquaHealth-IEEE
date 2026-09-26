import Dexie, { type Table } from 'dexie'
import type { CheckInDraft, QueuedPhoto } from './types'

export interface OutboxItem {
  client_uuid: string
  draft: CheckInDraft
  photos: QueuedPhoto[]
  queued_at: string
  attempts: number
  last_error: string | null
}

export interface SubmittedItem {
  client_uuid: string
  site_id: string
  observed_at: string
  checkin_id: number
  synced_at: string
}

/** Local IndexedDB store: the offline outbox and a log of synced check-ins. */
export class LocalDb extends Dexie {
  outbox!: Table<OutboxItem, string>
  submitted!: Table<SubmittedItem, string>

  constructor(name = 'aquasentinel') {
    super(name)
    this.version(1).stores({
      outbox: 'client_uuid, queued_at',
      submitted: 'client_uuid, synced_at, site_id',
    })
  }
}

export const db = new LocalDb()
