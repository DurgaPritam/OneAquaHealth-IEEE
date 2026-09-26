import type { AiResponse, AiStatus, VisionType } from './ai'
import type { Action, CheckInDraft, CheckInResult, Message, Observer, RiskScore, Site } from './types'

/**
 * Everything the UI needs from a backend. HttpClient talks to the FastAPI
 * server; the static demo swaps in an in-browser implementation.
 */
export interface DataClient {
  readonly kind: 'http' | 'local'
  listSites(): Promise<Site[]>
  registerObserver(id: string, team?: string | null): Promise<Observer>
  submitCheckIn(draft: CheckInDraft): Promise<CheckInResult>
  uploadPhoto(blob: Blob, findingId: number): Promise<void>
  listMessages(observerId: string): Promise<Message[]>
  listRiskScores(week?: string): Promise<RiskScore[]>
  listActions(status?: string): Promise<Action[]>
  aiStatus(): Promise<AiStatus>
  suggest(photo: Blob, type: VisionType, siteId?: string, keyResult?: string): Promise<AiResponse>
}

export class HttpError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export class HttpClient implements DataClient {
  readonly kind = 'http' as const
  private readonly base: string

  constructor(base = '') {
    this.base = base
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(this.base + path, init)
    if (!res.ok) throw new HttpError(res.status, `${init?.method ?? 'GET'} ${path} failed with ${res.status}`)
    return (res.status === 204 ? undefined : await res.json()) as T
  }

  private json<T>(path: string, method: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  }

  listSites() {
    return this.request<Site[]>('/api/sites?limit=5000')
  }

  registerObserver(id: string, team: string | null = null) {
    return this.json<Observer>(`/api/observers/${encodeURIComponent(id)}`, 'PUT', { team })
  }

  submitCheckIn(draft: CheckInDraft) {
    return this.json<CheckInResult>('/api/checkins', 'POST', draft)
  }

  async uploadPhoto(blob: Blob, findingId: number) {
    const form = new FormData()
    form.append('file', blob, 'photo.jpg')
    await this.request(`/api/photos?finding_id=${findingId}`, { method: 'POST', body: form })
  }

  listMessages(observerId: string) {
    return this.request<Message[]>(`/api/messages?observer_id=${encodeURIComponent(observerId)}`)
  }

  listRiskScores(week?: string) {
    return this.request<RiskScore[]>(`/api/risk-scores${week ? `?week=${week}` : ''}`)
  }

  listActions(status?: string) {
    return this.request<Action[]>(`/api/actions${status ? `?status=${status}` : ''}`)
  }

  aiStatus() {
    return this.request<AiStatus>('/api/ai/status')
  }

  suggest(photo: Blob, type: VisionType, siteId?: string, keyResult?: string) {
    const form = new FormData()
    form.append('file', photo, 'photo.jpg')
    const q = new URLSearchParams({ finding_type: type })
    if (siteId) q.set('site_id', siteId)
    if (keyResult) q.set('key_result', keyResult)
    return this.request<AiResponse>(`/api/ai/suggest?${q}`, { method: 'POST', body: form })
  }
}
