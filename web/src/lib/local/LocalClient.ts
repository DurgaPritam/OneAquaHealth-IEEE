// In-browser backend for the static demo: same DataClient interface as the FastAPI
// server, running the TypeScript ports (risk, Dawid-Skene, drafting, calibration, mock AI)
// over a snapshot exported by analysis/export_demo.py. State persists in IndexedDB.
import Dexie, { type Table } from 'dexie'
import type { AiResponse, AiStatus, VisionType } from '../ai'
import { scoreCalibration } from '../calibration'
import type { DataClient } from '../client'
import { HttpError } from '../client'
import type { Action, CheckIn, CheckInDraft, CheckInResult, DecisionResult, Finding, Message, Observer, RiskScore, Site } from '../types'
import { decide, draftForCity, editAction, MEASURES } from './actions'
import { mockSuggest } from './mockAi'
import { computeCity, type RiskConfig, type WeatherDay } from './risk'

export interface Snapshot {
  about: string
  city: string
  as_of: string
  config: RiskConfig
  sites: Site[]
  observers: Observer[]
  checkins: CheckIn[]
  findings: Finding[]
  risk_scores: RiskScore[]
  weather: Record<string, WeatherDay[]>
}

interface State {
  as_of: string
  config: RiskConfig
  sites: Site[]
  observers: Observer[]
  checkins: CheckIn[]
  findings: Finding[]
  risk_scores: RiskScore[]
  weather: Record<string, WeatherDay[]>
  actions: Action[]
  messages: Message[]
  photos: number
  next_id: number
}

class DemoDb extends Dexie {
  state!: Table<{ key: string; value: State }, string>
  constructor(name: string) {
    super(name)
    this.version(1).stores({ state: 'key' })
  }
}

export const DEMO_DB_NAME = 'aquasentinel-demo'

export class LocalClient implements DataClient {
  readonly kind = 'local' as const
  private state: State | null = null
  private loading: Promise<State> | null = null
  private readonly db: DemoDb
  private readonly loadSnapshot: () => Promise<Snapshot>

  constructor(loadSnapshot?: () => Promise<Snapshot>, dbName = DEMO_DB_NAME) {
    this.loadSnapshot =
      loadSnapshot ??
      (async () => {
        const res = await fetch(`${import.meta.env.BASE_URL}demo/snapshot.json`)
        return (await res.json()) as Snapshot
      })
    this.db = new DemoDb(dbName)
  }

  /** The demo clock: the synthetic season ends on this date. */
  async demoDate(): Promise<string> {
    return (await this.s()).as_of
  }

  async reset(): Promise<void> {
    await this.db.state.clear()
    this.state = null
    this.loading = null
    await this.s()
  }

  private async s(): Promise<State> {
    if (this.state) return this.state
    this.loading ??= (async () => {
      const saved = await this.db.state.get('state')
      if (saved) return saved.value
      const snap = await this.loadSnapshot()
      const ids = [...snap.checkins.map((c) => c.id), ...snap.findings.map((f) => f.id), ...snap.risk_scores.map((r) => r.id ?? 0)]
      return {
        as_of: snap.as_of, config: snap.config, sites: snap.sites, observers: snap.observers, checkins: snap.checkins,
        findings: snap.findings, risk_scores: snap.risk_scores, weather: snap.weather, actions: [], messages: [], photos: 0,
        next_id: Math.max(0, ...ids) + 1,
      }
    })()
    this.state = await this.loading
    return this.state
  }

  private async save() {
    if (this.state) await this.db.state.put({ key: 'state', value: this.state })
  }

  private nextId = () => this.state!.next_id++

  private latest(state: State, cityId: string): RiskScore[] {
    const ids = new Set(state.sites.filter((s) => s.city_id === cityId).map((s) => s.id))
    const latest = new Map<string, RiskScore>()
    for (const r of [...state.risk_scores].sort((a, b) => a.week.localeCompare(b.week))) if (ids.has(r.site_id)) latest.set(r.site_id, r)
    return [...latest.values()]
  }

  private recompute(state: State, cityId: string) {
    const rows = computeCity(state, cityId, state.as_of, state.config)
    for (const row of rows) {
      const existing = state.risk_scores.find((r) => r.site_id === row.site_id && r.week === row.week)
      const merged: RiskScore = { ...row, id: existing?.id ?? this.nextId() }
      if (existing) Object.assign(existing, merged)
      else state.risk_scores.push(merged)
    }
    return rows
  }

  async listSites() {
    return (await this.s()).sites
  }

  async registerObserver(id: string, team: string | null = null): Promise<Observer> {
    if (!/^OBS-[A-Z0-9]{6}$/.test(id)) throw new HttpError(422, 'Observer id must be pseudonymous')
    const st = await this.s()
    let o = st.observers.find((x) => x.id === id)
    if (!o) {
      o = { id, tier: 'new', team, calibration: {}, synthetic: false }
      st.observers.push(o)
      await this.save()
    }
    return o
  }

  async submitCheckIn(draft: CheckInDraft): Promise<CheckInResult> {
    if (!draft.consent) throw new HttpError(422, 'Consent is required')
    const st = await this.s()
    const site = st.sites.find((x) => x.id === draft.site_id)
    if (!site) throw new HttpError(404, 'Site not found')
    const dup = st.checkins.find((c) => c.client_uuid === draft.client_uuid)
    if (dup) return { checkin: dup, findings: st.findings.filter((f) => f.checkin_id === dup.id), duplicate: true }
    const { findings, ...rest } = draft
    // Demo clock: the check-in is dated on the last day of the synthetic season so it counts in this week's index.
    const observed = `${st.as_of}${draft.observed_at.slice(10)}`
    const checkin: CheckIn = { ...rest, observed_at: observed, id: this.nextId(), created_at: new Date().toISOString(), synthetic: false }
    const stored = findings.map((f) => ({ ...f, id: this.nextId(), checkin_id: checkin.id, data: f.data ?? {} }) as Finding)
    st.checkins.push(checkin)
    st.findings.push(...stored)
    this.recompute(st, site.city_id)
    await this.save()
    return { checkin, findings: stored, duplicate: false }
  }

  async uploadPhoto() {
    const st = await this.s()
    st.photos += 1 // photos stay on this device in the demo
    await this.save()
  }

  async listMessages(observerId: string) {
    return (await this.s()).messages.filter((m) => m.observer_id === observerId)
  }

  async latestRisk(cityId: string) {
    return this.latest(await this.s(), cityId)
  }

  async computeRisk(cityId: string) {
    const st = await this.s()
    this.recompute(st, cityId)
    await this.save()
    return this.latest(st, cityId)
  }

  async riskHistory(siteId: string) {
    return (await this.s()).risk_scores.filter((r) => r.site_id === siteId).sort((a, b) => a.week.localeCompare(b.week))
  }

  async listActions(status?: string) {
    const all = (await this.s()).actions
    return status ? all.filter((a) => a.status === status) : all
  }

  async measures() {
    return MEASURES
  }

  async draftActions(cityId: string) {
    const st = await this.s()
    const contributorsOf = (score: RiskScore) =>
      [...new Set(st.checkins.filter((c) => score.checkin_ids.includes(c.id)).map((c) => c.observer_id))].sort()
    const made = draftForCity({ actions: st.actions, messages: st.messages, nextId: this.nextId }, this.latest(st, cityId), contributorsOf)
    await this.save()
    return made
  }

  async editAction(id: number, edit: { title?: string; rationale?: string; measure_id?: string }) {
    const st = await this.s()
    const a = st.actions.find((x) => x.id === id)
    if (!a) throw new HttpError(404, 'Action not found')
    try {
      editAction(a, edit)
    } catch (e) {
      throw new HttpError(409, (e as Error).message)
    }
    await this.save()
    return a
  }

  async decideAction(id: number, approve: boolean, officer: string, note?: string): Promise<DecisionResult> {
    const st = await this.s()
    const a = st.actions.find((x) => x.id === id)
    if (!a) throw new HttpError(404, 'Action not found')
    let messages: Message[]
    try {
      messages = decide({ actions: st.actions, messages: st.messages, nextId: this.nextId }, a, approve, officer, note, st.sites.find((x) => x.id === a.site_id))
    } catch (e) {
      throw new HttpError(409, (e as Error).message)
    }
    await this.save()
    return { action: a, messages }
  }

  async aiStatus(): Promise<AiStatus> {
    return { provider: 'mock', model: 'mock-deterministic-1', mock: true, available: true }
  }

  async suggest(photo: Blob, type: VisionType): Promise<AiResponse> {
    return mockSuggest(photo, type)
  }

  async submitCalibration(observerId: string, answers: Record<string, string>) {
    const o = await this.registerObserver(observerId)
    const result = scoreCalibration(answers)
    o.calibration = { per_question: result.per_question, overall_kappa: result.overall_kappa, n: result.n }
    o.tier = result.tier
    await this.save()
    return result
  }
}
