import type { AiResponse, AiStatus, VisionType } from '../lib/ai'
import { scoreCalibration } from '../lib/calibration'
import type { DataClient } from '../lib/client'
import { HttpError } from '../lib/client'
import type { CheckInDraft, CheckInResult, Finding, Observer, Site } from '../lib/types'

export const SITES: Site[] = [
  { id: 'C1', name: 'Exploratório', city_id: 'CO', city_name: 'Coimbra', lat: 40.19787, lon: -8.42865, altitude: 20, synthetic: false },
  { id: 'C2', name: 'Estação Cbr-B', city_id: 'CO', city_name: 'Coimbra', lat: 40.22483, lon: -8.44135, altitude: 14, synthetic: false },
  { id: 'O1', name: 'Alna', city_id: 'OS', city_name: 'Oslo', lat: 59.93, lon: 10.8, altitude: null, synthetic: false },
]

/** In-memory backend that can be switched offline, mirroring the API's idempotency. */
export class FakeClient implements DataClient {
  readonly kind = 'http' as const
  offline = false
  observers = new Set<string>()
  checkins = new Map<string, CheckInResult>()
  photos: { findingId: number; size: number }[] = []
  private nextId = 1
  aiCalls: { type: VisionType; siteId?: string; keyResult?: string }[] = []
  aiAvailable = true
  nextAi: AiResponse = {
    available: true,
    provider: 'mock',
    model: 'mock-deterministic-1',
    mock: true,
    suggestions: [{ label: 'larvae_present', confidence: 0.82, reason: 'Demo AI (mock): placeholder suggestion.', text: 'Larvae visible in the cup' }],
    dropped: [{ label: 'Culex pipiens larva', why: 'not in the allowed label list' }],
  }

  private guard() {
    if (this.offline) throw new TypeError('Failed to fetch')
  }

  async listSites() {
    this.guard()
    return SITES
  }

  async registerObserver(id: string): Promise<Observer> {
    this.guard()
    this.observers.add(id)
    return { id, tier: 'new', team: null, calibration: {}, synthetic: false }
  }

  async submitCheckIn(draft: CheckInDraft): Promise<CheckInResult> {
    this.guard()
    if (!draft.consent) throw new HttpError(422, 'consent')
    const existing = this.checkins.get(draft.client_uuid)
    if (existing) return { ...existing, duplicate: true }
    const checkinId = this.nextId++
    const findings: Finding[] = draft.findings.map((f) => ({ ...f, id: this.nextId++, checkin_id: checkinId }))
    const { findings: _omit, ...rest } = draft
    void _omit
    const result = { checkin: { ...rest, id: checkinId, created_at: new Date().toISOString() }, findings, duplicate: false }
    this.checkins.set(draft.client_uuid, result)
    return result
  }

  async uploadPhoto(blob: Blob, findingId: number) {
    this.guard()
    this.photos.push({ findingId, size: blob.size })
  }

  async listMessages() {
    return []
  }

  async latestRisk() {
    return []
  }

  async computeRisk() {
    return []
  }

  async riskHistory() {
    return []
  }

  async measures() {
    return { source: '', source_url: '', drivers: {}, measures: {} }
  }

  async draftActions() {
    return []
  }

  async editAction(): Promise<never> {
    throw new Error('not in fake')
  }

  async decideAction(): Promise<never> {
    throw new Error('not in fake')
  }

  async listActions() {
    return []
  }

  async aiStatus(): Promise<AiStatus> {
    return { provider: 'mock', model: 'mock-deterministic-1', mock: true, available: true }
  }

  async suggest(_photo: Blob, type: VisionType, siteId?: string, keyResult?: string): Promise<AiResponse> {
    this.guard()
    this.aiCalls.push({ type, siteId, keyResult })
    if (!this.aiAvailable) return { available: false, error: 'down', suggestions: [], dropped: [] }
    return this.nextAi
  }

  calibrations: Record<string, Record<string, string>> = {}

  async submitCalibration(observerId: string, answers: Record<string, string>) {
    this.guard()
    this.calibrations[observerId] = answers
    return scoreCalibration(answers)
  }

  async engagementData() {
    return { observers: [], checkins: [], findings: [], scores: [], sites: SITES, latest: [] }
  }
}
