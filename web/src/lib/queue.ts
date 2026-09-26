import type { DataClient } from './client'
import { HttpError } from './client'
import { db, type LocalDb } from './db'
import type { CheckInDraft, QueuedPhoto } from './types'

/** Put a check-in in the offline outbox. It stays there until a sync succeeds. */
export async function enqueue(draft: CheckInDraft, photos: QueuedPhoto[] = [], store: LocalDb = db): Promise<void> {
  await store.outbox.put({
    client_uuid: draft.client_uuid,
    draft,
    photos,
    queued_at: new Date().toISOString(),
    attempts: 0,
    last_error: null,
  })
}

export function pendingCount(store: LocalDb = db): Promise<number> {
  return store.outbox.count()
}

export interface SyncReport {
  sent: number
  failed: number
  remaining: number
}

/**
 * Send every queued check-in. The server is idempotent on client_uuid, so a
 * retry after a lost response cannot create a duplicate. Items rejected with a
 * 4xx other than 404/408/429 stay queued with the error shown to the user.
 */
export async function syncOutbox(client: DataClient, store: LocalDb = db): Promise<SyncReport> {
  const items = await store.outbox.orderBy('queued_at').toArray()
  let sent = 0
  let failed = 0
  const registered = new Set<string>()
  for (const item of items) {
    try {
      const observer = item.draft.observer_id
      if (!registered.has(observer)) {
        await client.registerObserver(observer)
        registered.add(observer)
      }
      const result = await client.submitCheckIn(item.draft)
      for (const photo of item.photos) {
        const finding = result.findings.find((f) => f.subject === photo.subject)
        if (finding && !result.duplicate) await client.uploadPhoto(photo.blob, finding.id)
      }
      await store.transaction('rw', store.outbox, store.submitted, async () => {
        await store.submitted.put({
          client_uuid: item.client_uuid,
          site_id: item.draft.site_id,
          observed_at: item.draft.observed_at,
          checkin_id: result.checkin.id,
          synced_at: new Date().toISOString(),
        })
        await store.outbox.delete(item.client_uuid)
      })
      sent += 1
    } catch (err) {
      failed += 1
      const message = err instanceof HttpError ? `HTTP ${err.status}` : 'offline'
      await store.outbox.update(item.client_uuid, { attempts: item.attempts + 1, last_error: message })
      if (!(err instanceof HttpError)) break // network is down; stop trying the rest
    }
  }
  return { sent, failed, remaining: await store.outbox.count() }
}
