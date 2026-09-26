// Engagement: campaigns from data gaps, and a leaderboard that rewards evidence quality, never volume.
import type { CheckIn, Finding, Observer, RiskScore, Site } from './types'
import { isoWeek } from './local/risk'

const HABITAT_QUESTIONS = ['flow_NP', 'sub_OM', 'water_sewage_smell', 'water_foam', 'water_colour_unusual', 'mac_free_floating']
export const MIN_QUALITY = 0.4 // below this a check-in earns nothing
export const MAX_POINTS = 10
export const STALE_DAYS = 10
export const WIDE_RANGE = 0.3

// ------------------------------------------------------------------ campaigns

export interface CampaignSite {
  site: Site
  reason: 'no_data' | 'stale' | 'uncertain'
  detail: number | null
}

function newestAge(r: RiskScore): number | null {
  const ages = r.factors.filter((f) => !['temperature', 'dry_spell'].includes(f.name) && f.value !== null && f.data_age_days !== null).map((f) => f.data_age_days as number)
  return ages.length ? Math.min(...ages) : null
}

/** Sites a "mosquito season" campaign should send volunteers to, most urgent first. */
export function campaigns(latest: RiskScore[], sites: Site[]): CampaignSite[] {
  const byId = new Map(sites.map((s) => [s.id, s]))
  const out: (CampaignSite & { rank: number })[] = []
  for (const r of latest) {
    const site = byId.get(r.site_id)
    if (!site) continue
    const age = newestAge(r)
    const width = r.range_high - r.range_low
    if (r.needs_data) out.push({ site, reason: 'no_data', detail: null, rank: 0 })
    else if (age !== null && age > STALE_DAYS) out.push({ site, reason: 'stale', detail: age, rank: 1 + 1 / (age + 1) })
    else if (width > WIDE_RANGE) out.push({ site, reason: 'uncertain', detail: Math.round(width * 100) / 100, rank: 2 + (1 - width) })
  }
  return out.sort((a, b) => a.rank - b.rank).map(({ rank: _rank, ...c }) => {
    void _rank
    return c
  })
}

// ------------------------------------------------------------------ quality

export interface Quality {
  completeness: number
  consistency: number
  quality: number
}

/**
 * Evidence quality of one check-in, in [0, 1]:
 * 60 % consistency (how probable the observer's habitat answers are under the
 * reliability-weighted consensus at that site) and 40 % completeness.
 */
export function checkinQuality(c: CheckIn, findings: Finding[], scores: RiskScore[]): Quality {
  const answered = HABITAT_QUESTIONS.filter((q) => c.answers[q] !== undefined).length / HABITAT_QUESTIONS.length
  const subjects = new Set(findings.map((f) => f.subject))
  const completeness = 0.6 * answered + 0.2 * (subjects.has('larval_dips') ? 1 : 0) + 0.2 * (subjects.has('amphibians') || subjects.has('insectivorous_birds') ? 1 : 0)
  const row = scores.find((r) => r.site_id === c.site_id && r.checkin_ids.includes(c.id))
  const habitat = row?.factors.find((f) => f.name === 'habitat')
  const qs = ((habitat?.inputs as { questions?: Record<string, { posterior: Record<string, number> }> })?.questions) ?? {}
  const probs = Object.entries(qs)
    .filter(([q]) => c.answers[q] !== undefined)
    .map(([q, v]) => v.posterior[String(c.answers[q])] ?? 0)
  const consistency = probs.length ? probs.reduce((a, b) => a + b, 0) / probs.length : 0
  const quality = 0.6 * consistency + 0.4 * completeness
  return { completeness: round2(completeness), consistency: round2(consistency), quality: round2(quality) }
}

const round2 = (x: number) => Math.round(x * 100) / 100

// ------------------------------------------------------------------ leaderboard

export interface ObserverScore {
  observer: string
  team: string | null
  tier: Observer['tier']
  points: number
  counted: number
  ignored: number
  meanQuality: number
}

export interface TeamScore {
  team: string
  points: number
  members: number
  pointsPerMember: number
}

/**
 * Points: for each observer, site and ISO week only the single best check-in counts,
 * and only if its quality reaches MIN_QUALITY. Repeating a check-in or sending many
 * poor ones earns nothing extra; checking more sites well does.
 */
export function leaderboard(observers: Observer[], checkins: CheckIn[], findings: Finding[], scores: RiskScore[]): { people: ObserverScore[]; teams: TeamScore[] } {
  const byCheckin = new Map<number, Finding[]>()
  for (const f of findings) byCheckin.set(f.checkin_id, [...(byCheckin.get(f.checkin_id) ?? []), f])
  const best = new Map<string, number>()
  const perObserver = new Map<string, { qualities: number[]; total: number }>()
  for (const c of checkins) {
    const q = checkinQuality(c, byCheckin.get(c.id) ?? [], scores).quality
    const key = `${c.observer_id}|${c.site_id}|${isoWeek(c.observed_at.slice(0, 10))}`
    best.set(key, Math.max(best.get(key) ?? 0, q))
    const po = perObserver.get(c.observer_id) ?? { qualities: [], total: 0 }
    po.qualities.push(q)
    po.total += 1
    perObserver.set(c.observer_id, po)
  }
  const points = new Map<string, { points: number; counted: number }>()
  for (const [key, q] of best) {
    const obs = key.split('|')[0]
    const p = points.get(obs) ?? { points: 0, counted: 0 }
    if (q >= MIN_QUALITY) {
      p.points += Math.round(q * MAX_POINTS)
      p.counted += 1
    }
    points.set(obs, p)
  }
  const obsById = new Map(observers.map((o) => [o.id, o]))
  const people: ObserverScore[] = [...perObserver.entries()].map(([id, po]) => {
    const p = points.get(id) ?? { points: 0, counted: 0 }
    const o = obsById.get(id)
    return {
      observer: id, team: o?.team ?? null, tier: o?.tier ?? 'new', points: p.points, counted: p.counted,
      ignored: po.total - p.counted, meanQuality: round2(po.qualities.reduce((a, b) => a + b, 0) / po.qualities.length),
    }
  }).sort((a, b) => b.points - a.points || b.meanQuality - a.meanQuality)
  const teamMap = new Map<string, { points: number; members: number }>()
  for (const p of people) {
    if (!p.team) continue
    const t = teamMap.get(p.team) ?? { points: 0, members: 0 }
    t.points += p.points
    t.members += 1
    teamMap.set(p.team, t)
  }
  const teams = [...teamMap.entries()]
    .map(([team, t]) => ({ team, points: t.points, members: t.members, pointsPerMember: Math.round((t.points / t.members) * 10) / 10 }))
    .sort((a, b) => b.pointsPerMember - a.pointsPerMember)
  return { people, teams }
}
