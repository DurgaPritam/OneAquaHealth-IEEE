import { describe, expect, it } from 'vitest'
import { answerKeys, buildDraft, emptyState, larvaKey, marginKey, questions } from '../checkin'
import { LocalDb } from '../db'
import { distanceM, getObserverCode, newObserverCode, roundCoord } from '../observer'
import { fitWithin } from '../photo'
import { enqueue, pendingCount, syncOutbox } from '../queue'
import { FakeClient } from '../../test/fakeClient'

const ctx = { observerId: 'OBS-ABC234', now: new Date('2026-09-20T09:00:00Z'), uuid: 'u-1', position: { lat: 40.197871, lon: -8.428651 } }

describe('observer', () => {
  it('creates pseudonymous codes', () => {
    expect(newObserverCode()).toMatch(/^OBS-[A-Z2-9]{6}$/)
  })
  it('keeps the same code on one device', () => {
    const store = new Map<string, string>()
    const storage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) } as Storage
    expect(getObserverCode(storage)).toBe(getObserverCode(storage))
  })
  it('rounds coordinates to about 100 m', () => {
    expect(roundCoord(40.197871)).toBe(40.198)
    expect(distanceM(40, -8, 40.001, -8)).toBeGreaterThan(100)
    expect(distanceM(40, -8, 40.001, -8)).toBeLessThan(120)
  })
})

describe('photo', () => {
  it('caps the longest edge at 1600 px and keeps the aspect ratio', () => {
    expect(fitWithin(4000, 3000)).toEqual({ width: 1600, height: 1200 })
    expect(fitWithin(1200, 900)).toEqual({ width: 1200, height: 900 })
    expect(fitWithin(1000, 5000)).toEqual({ width: 320, height: 1600 })
  })
})

describe('questions', () => {
  it('asks bank questions once per margin', () => {
    const banks = questions.sections.find((s) => s.id === 'banks')!
    expect(answerKeys(banks)).toContain('bank_right_CC')
    expect(answerKeys(banks)).toContain('bank_left_EA')
    expect(marginKey('bank_GA', 'left')).toBe('bank_left_GA')
  })
  it('every question comes from the cited protocol or is marked as an addition', () => {
    expect(questions.source).toBe('https://doi.org/10.5281/zenodo.20344421')
    for (const s of questions.sections) expect(s.protocol_section.length).toBeGreaterThan(5)
  })
})

describe('buildDraft', () => {
  it('rounds position, drops skipped sections and records larvae per dip', () => {
    const s = { ...emptyState(), siteId: 'C1', consent: true, dips: [2, 0, 5, 1, 0], posture: 'angled' as const }
    s.answers = { flow_NP: 'extensive', sub_MU: 'present' }
    s.skipped = ['channel_substrate']
    const { draft } = buildDraft(s, ctx)
    expect(draft.lat).toBe(40.198)
    expect(draft.answers).toEqual({ flow_NP: 'extensive' })
    const dips = draft.findings.find((f) => f.subject === 'larval_dips')!
    expect(dips.count).toBe(8)
    expect(dips.data).toEqual({ dips: [2, 0, 5, 1, 0] })
    expect(draft.findings.find((f) => f.subject === 'larval_posture')?.key_label).toBe('culex_or_aedes_type')
  })
  it('records dead birds only when reported and never as handled', () => {
    const s = { ...emptyState(), siteId: 'C1', deadBirdsSeen: 'yes' as const, deadBirds: 2 }
    const bird = buildDraft(s, ctx).draft.findings.find((f) => f.type === 'dead_bird')!
    expect(bird.count).toBe(2)
    expect(bird.data).toEqual({ handled: false })
    expect(bird.ai_label).toBeUndefined()
  })
  it('the guided key never names a species', () => {
    expect(larvaKey('flat')).toBe('anopheles_type')
    expect(larvaKey('unsure')).toBeNull()
  })
})

describe('offline queue', () => {
  it('keeps check-ins while offline and sends them once, with photos, when online', async () => {
    const store = new LocalDb('queue-test')
    const client = new FakeClient()
    const s = { ...emptyState(), siteId: 'C1', consent: true, dips: [3, 0, 0, 0, 0], cupPhoto: new Blob(['x'], { type: 'image/jpeg' }) }
    const { draft, photos } = buildDraft(s, ctx)
    await enqueue(draft, photos, store)

    client.offline = true
    const first = await syncOutbox(client, store)
    expect(first).toEqual({ sent: 0, failed: 1, remaining: 1 })
    expect((await store.outbox.get('u-1'))?.last_error).toBe('offline')

    client.offline = false
    const second = await syncOutbox(client, store)
    expect(second).toEqual({ sent: 1, failed: 0, remaining: 0 })
    expect(client.checkins.size).toBe(1)
    expect(client.photos).toHaveLength(1)
    expect(await store.submitted.count()).toBe(1)

    await enqueue(draft, photos, store) // same uuid again, e.g. a lost response
    await syncOutbox(client, store)
    expect(client.checkins.size).toBe(1)
    expect(client.photos).toHaveLength(1)
    expect(await pendingCount(store)).toBe(0)
  })
})
