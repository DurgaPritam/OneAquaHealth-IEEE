// TypeScript port of api/actions/drafting.py for the static demo.
import measuresFile from '../../../../data/measures.json'
import type { Action, MeasureCatalogue, Message, RiskScore, Site } from '../types'

export const MEASURES = measuresFile as unknown as MeasureCatalogue
const POLLUTION = new Set(['water_sewage_smell', 'water_foam', 'water_colour_unusual', 'sub_OM'])

export function warningsFor(measureId: string): string[] {
  const m = MEASURES.measures[measureId]
  if (!m) throw new Error(`Unknown measure ${measureId}`)
  return m.mosquito_warning ? [m.mosquito_warning] : []
}

export function driverFor(score: RiskScore): string | null {
  if (score.dominant !== 'habitat') return score.dominant
  const habitat = score.factors.find((f) => f.name === 'habitat')
  const qs = ((habitat?.inputs as { questions?: Record<string, { expected: number }> })?.questions) ?? {}
  const keys = Object.keys(qs)
  if (!keys.length) return 'stagnation'
  const top = keys.reduce((a, b) => (qs[b].expected > qs[a].expected ? b : a))
  return POLLUTION.has(top) ? 'organic_pollution' : 'stagnation'
}

function deadBirds(score: RiskScore): number {
  const host = score.factors.find((f) => f.name === 'host_signal')
  return Number((host?.inputs as { count?: number })?.count ?? 0)
}

export interface ActionState {
  actions: Action[]
  messages: Message[]
  nextId: () => number
}

export function draftForCity(state: ActionState, latest: RiskScore[], contributorsOf: (s: RiskScore) => string[]): Action[] {
  const drafted: Action[] = []
  const open = (siteId: string, measureId: string) => state.actions.some((a) => a.site_id === siteId && a.measure_id === measureId && a.status === 'drafted')
  const make = (score: RiskScore, driver: string, measureId: string, rationale: string) => {
    if (open(score.site_id, measureId)) return
    const a: Action = {
      id: state.nextId(), site_id: score.site_id, risk_score_id: score.id ?? null, driver, measure_id: measureId,
      title: MEASURES.measures[measureId].title, rationale, status: 'drafted', approved_by: null, decision_note: null, decided_at: null,
      contributors: contributorsOf(score), warnings: warningsFor(measureId), created_at: new Date().toISOString(), synthetic: score.synthetic,
    }
    state.actions.push(a)
    drafted.push(a)
  }
  for (const score of latest) {
    let driver = score.alert ? driverFor(score) : null
    if (driver) {
      if (driver === 'host_signal') driver = 'stagnation'
      const d = MEASURES.drivers[driver]
      make(score, driver, d.measures[0], `Index ${score.total.toFixed(2)} (${score.band.replace('_', ' ')}) in week ${score.week}. Main driver: ${d.label.toLowerCase()}. ${score.explanation}`)
    }
    const n = deadBirds(score)
    if (n > 0) make(score, 'host_signal', 'veterinary_notification', `${n} dead bird(s) reported in week ${score.week}. Route to the veterinary team; no diagnosis is made.`)
  }
  return drafted
}

export function editAction(a: Action, edit: { title?: string; rationale?: string; measure_id?: string }): Action {
  if (a.status !== 'drafted') throw new Error('Only drafted actions can be edited')
  if (edit.measure_id) {
    a.measure_id = edit.measure_id
    a.warnings = warningsFor(edit.measure_id)
    a.title = edit.title || MEASURES.measures[edit.measure_id].title
  } else if (edit.title) a.title = edit.title
  if (edit.rationale) a.rationale = edit.rationale
  return a
}

export function decide(state: ActionState, a: Action, approve: boolean, officer: string, note: string | undefined, site?: Site): Message[] {
  if (a.status !== 'drafted') throw new Error('This action has already been decided')
  if (!officer.trim()) throw new Error('An officer must be named')
  a.status = approve ? 'approved' : 'dismissed'
  a.approved_by = officer.trim()
  a.decision_note = note ?? null
  a.decided_at = new Date().toISOString()
  const place = site ? `${site.name} (${site.id})` : a.site_id
  const [kind, text] = approve
    ? ['action_taken', `Your observation at ${place} led to an action: ${a.title}. Approved by the city.`]
    : ['alert_raised', `Your observation at ${place} helped raise an alert. The city reviewed it and decided no action is needed now.`]
  const msgs: Message[] = a.contributors.map((o) => ({ id: state.nextId(), observer_id: o, action_id: a.id, kind, text, read: false, created_at: new Date().toISOString(), synthetic: a.synthetic }))
  state.messages.push(...msgs)
  return msgs
}
