// TypeScript port of api/risk (factors.py, index.py, service.py) for the static demo.
// Pinned to Python by data/fixtures/risk_golden.json (web/src/lib/local/__tests__).
import questionsFile from '../../../../data/questions.json'
import type { Band, CheckIn, Finding, Observer, RiskFactor, RiskScore } from '../types'
import { dawidSkene } from './dawidSkene'

export interface RiskConfig {
  window_days: number
  bands: { name: Band; below: number }[]
  alert_threshold: number
  min_coverage: number
  season_weights: Record<string, number>
  site_weights: Record<string, number>
  temperature: { base_c: number; degree_days_target: number; upper_optimum_c: number; upper_limit_c: number }
  dry_spell: { dry_day_max_mm: number; days_to_saturate: number }
  habitat: { questions: Record<string, number> }
  vector_presence: { scale_per_dip: number }
  predator_deficit: { birds_to_saturate: number; parts: Record<string, number> }
  host_signal: { reports_to_saturate: number }
  fingerprint: string
}

export interface WeatherDay {
  date: string
  tmean: number | null
  precip: number | null
}

const APE = ['absent', 'present', 'extensive']
const APE_SCORE: Record<string, number> = { absent: 0, present: 0.5, extensive: 1 }
const AMPHIBIAN_SCORE: Record<string, number> = { none: 0, heard: 0.7, seen: 1 }
const SEASON = ['temperature', 'dry_spell']
const SITE = ['habitat', 'vector_presence', 'predator_deficit', 'host_signal']

const r4 = (x: number) => Math.round(x * 1e4) / 1e4
const clip = (x: number) => Math.max(0, Math.min(1, x))

const QUESTION_LABELS: Record<string, string> = Object.fromEntries(
  (questionsFile as { sections: { questions: { id: string; label: string }[] }[] }).sections.flatMap((s) => s.questions.map((q) => [q.id, q.label])),
)

type F = RiskFactor

function factor(name: string, label: string, value: number | null, explanation: string, inputs: Record<string, unknown> = {}): F {
  return { name, label, value, explanation, inputs, data_age_days: null, weight: 0, contribution: 0 }
}

// ------------------------------------------------------------------ factors

export function temperature(days: WeatherDay[], cfg: RiskConfig): F {
  const c = cfg.temperature
  const temps = days.map((d) => d.tmean).filter((t): t is number => t !== null && t !== undefined)
  if (!temps.length) return factor('temperature', 'Temperature suitability', null, 'No weather data for this window.')
  const dd = temps.reduce((s, t) => s + Math.max(0, t - c.base_c), 0)
  const mean = temps.reduce((a, b) => a + b, 0) / temps.length
  let heat = 1
  if (mean > c.upper_optimum_c) heat = clip((c.upper_limit_c - mean) / (c.upper_limit_c - c.upper_optimum_c))
  const value = clip(dd / c.degree_days_target) * heat
  let text = `${dd.toFixed(0)} degree-days above ${c.base_c} °C in ${temps.length} days (about ${c.degree_days_target} are needed for the virus to develop in Culex mosquitoes); mean ${mean.toFixed(1)} °C.`
  if (heat < 1) text += ` Above ${c.upper_optimum_c} °C transmission declines, so the factor is reduced.`
  return factor('temperature', 'Temperature suitability', r4(value), text, { degree_days: r4(dd), mean_c: r4(mean), days, base_c: c.base_c })
}

export function drySpell(days: WeatherDay[], cfg: RiskConfig): F {
  const c = cfg.dry_spell
  const p = days.filter((d) => d.precip !== null && d.precip !== undefined)
  if (!p.length) return factor('dry_spell', 'Dry spell and stagnation', null, 'No rainfall data for this window.')
  let run = 0
  for (let i = p.length - 1; i >= 0; i -= 1) {
    if ((p[i].precip as number) >= c.dry_day_max_mm) break
    run += 1
  }
  const total = p.reduce((s, d) => s + (d.precip as number), 0)
  const text = `${run} dry days in a row (under ${c.dry_day_max_mm} mm); ${total.toFixed(0)} mm of rain in the window. Dry spells leave still pools behind weirs and in the channel.`
  return factor('dry_spell', 'Dry spell and stagnation', r4(clip(run / c.days_to_saturate)), text, { dry_days: run, rain_mm: r4(total) })
}

export interface HabitatQ {
  expected: number
  posterior: Record<string, number>
  n_reports: number
  raw: { checkin_id: number; observer: string; answer: string }[]
}

export function habitat(post: Record<string, HabitatQ>, cfg: RiskConfig): F {
  const w = cfg.habitat.questions
  const used = Object.keys(post).filter((q) => q in w)
  if (!used.length) return factor('habitat', 'Larval habitat (stream check)', null, 'No stream-check answers in this window.')
  const tw = used.reduce((s, q) => s + w[q], 0)
  const value = used.reduce((s, q) => s + w[q] * post[q].expected, 0) / tw
  const worst = used.reduce((a, b) => (post[b].expected > post[a].expected ? b : a))
  const n = used.reduce((s, q) => s + post[q].n_reports, 0)
  const text = `From ${n} answers to ${used.length} questions, weighted by observer reliability. Strongest signal: ${(QUESTION_LABELS[worst] ?? worst).toLowerCase()} (expected score ${post[worst].expected.toFixed(2)} of 1).`
  return factor('habitat', 'Larval habitat (stream check)', r4(value), text, { questions: Object.fromEntries(used.map((q) => [q, post[q]])) })
}

export interface LarvalReport { checkin_id: number; observer: string; per_dip: number; weight: number }
export interface PredatorReport { checkin_id: number; observer: string; weight: number; amphibians: string | null; birds: number | null; bats: string | null }
export interface DeadBirdReport { checkin_id: number; count: number; date: string }

export function vectorPresence(larval: LarvalReport[], cfg: RiskConfig): F {
  if (!larval.length) return factor('vector_presence', 'Mosquito larvae found', null, 'No larval dips in this window.')
  const ws = larval.reduce((s, r) => s + r.weight, 0)
  const mean = larval.reduce((s, r) => s + r.per_dip * r.weight, 0) / ws
  const value = 1 - Math.exp(-mean / cfg.vector_presence.scale_per_dip)
  return factor('vector_presence', 'Mosquito larvae found', r4(value), `${larval.length} larval dip sessions; reliability-weighted mean ${mean.toFixed(1)} larvae per dip.`, { mean_per_dip: r4(mean), reports: larval })
}

export function predatorDeficit(reports: PredatorReport[], cfg: RiskConfig): F {
  if (!reports.length) return factor('predator_deficit', 'Missing mosquito predators', null, 'No predator observations in this window.')
  const c = cfg.predator_deficit
  let num = 0
  let ws = 0
  for (const r of reports) {
    const pieces: Record<string, number> = {}
    if (r.amphibians !== null && r.amphibians in AMPHIBIAN_SCORE) pieces.amphibians = AMPHIBIAN_SCORE[r.amphibians]
    if (r.birds !== null && r.birds !== undefined) pieces.birds = clip(r.birds / c.birds_to_saturate)
    if (r.bats === 'none' || r.bats === 'seen') pieces.bats = r.bats === 'seen' ? 1 : 0
    const keys = Object.keys(pieces)
    if (!keys.length) continue
    const presence = keys.reduce((s, k) => s + c.parts[k] * pieces[k], 0) / keys.reduce((s, k) => s + c.parts[k], 0)
    num += presence * r.weight
    ws += r.weight
  }
  if (ws === 0) return factor('predator_deficit', 'Missing mosquito predators', null, 'No usable predator observations in this window.')
  const presence = num / ws
  return factor('predator_deficit', 'Missing mosquito predators', r4(1 - presence),
    `Predator presence ${presence.toFixed(2)} of 1 from ${reports.length} observations. Fewer frogs, insect-eating birds and bats means less natural mosquito control.`,
    { presence: r4(presence), reports })
}

export function hostSignal(dead: DeadBirdReport[] | null, cfg: RiskConfig): F {
  if (dead === null) return factor('host_signal', 'Dead bird reports', null, 'No visits in this window, so no dead-bird information.')
  const n = dead.reduce((s, r) => s + r.count, 0)
  const text = n === 0 ? 'No dead birds reported in this window.' : `${n} dead bird(s) reported. Reports go to the veterinary team; this is not a diagnosis of any bird or place.`
  return factor('host_signal', 'Dead bird reports', r4(clip(n / cfg.host_signal.reports_to_saturate)), text, { count: n, reports: dead })
}

// ------------------------------------------------------------------ combination

function weighted(xs: F[], w: Record<string, number>) {
  const total = xs.reduce((s, x) => s + w[x.name], 0)
  const present = xs.filter((x) => x.value !== null)
  const pw = present.reduce((s, x) => s + w[x.name], 0)
  const known = present.reduce((s, x) => s + w[x.name] * (x.value as number), 0)
  return { mean: pw ? known / pw : null, cov: pw / total, lo: known / total, hi: (known + total - pw) / total }
}

export function bandFor(total: number, cfg: RiskConfig): Band {
  for (const b of cfg.bands) if (total < b.below) return b.name
  return cfg.bands[cfg.bands.length - 1].name
}

export interface Combined {
  total: number
  band: Band
  season: number | null
  site: number | null
  dominant: string | null
  coverage: number
  range_low: number
  range_high: number
  needs_data: boolean
  alert: boolean
  factors: F[]
  explanation: string
  config_version: string
}

export function combine(fs: F[], cfg: RiskConfig): Combined {
  const sw = cfg.season_weights
  const tw = cfg.site_weights
  const seasonF = fs.filter((x) => SEASON.includes(x.name))
  const siteF = fs.filter((x) => SITE.includes(x.name))
  const s = weighted(seasonF, sw)
  const t = weighted(siteF, tw)
  const gate = s.mean ?? 1
  const total = r4(gate * (t.mean ?? 0))
  const rangeLow = r4((s.mean !== null ? s.lo : 0) * t.lo)
  const rangeHigh = r4((s.mean !== null ? s.hi : 1) * t.hi)
  const presentSite = siteF.filter((x) => x.value !== null)
  const pw = presentSite.reduce((a, x) => a + tw[x.name], 0)
  for (const x of seasonF) {
    x.weight = sw[x.name]
    x.contribution = 0
  }
  for (const x of siteF) {
    x.weight = tw[x.name]
    x.contribution = x.value !== null && pw ? r4((gate * tw[x.name] * x.value) / pw) : 0
  }
  const needs = t.cov < cfg.min_coverage
  const band = bandFor(total, cfg)
  const dominant = presentSite.length ? presentSite.reduce((a, b) => (b.contribution > a.contribution ? b : a)).name : null
  const parts = [...presentSite].sort((a, b) => b.contribution - a.contribution).map((x) => `${x.label} ${(x.value as number).toFixed(2)}`)
  let explanation = `Index ${total.toFixed(2)} (${band.replace('_', ' ')}) = seasonal suitability ${s.mean === null ? 'n/a' : s.mean.toFixed(2)} x site conditions ${t.mean === null ? 'n/a' : t.mean.toFixed(2)}.`
  if (parts.length) explanation += ' Site factors: ' + parts.join('; ') + '.'
  if (s.mean === null) explanation += ' No weather data: seasonal suitability assumed 1 (upper bound).'
  const missing = siteF.filter((x) => x.value === null).map((x) => x.label)
  if (missing.length) explanation += ` No data for: ${missing.join(', ')} (site data coverage ${Math.round(t.cov * 100)}%); the index could be ${rangeLow.toFixed(2)} to ${rangeHigh.toFixed(2)}.`
  if (needs) explanation += ' Too little site data to raise an alert: this site needs a stream check.'
  return {
    total, band, season: s.mean === null ? null : r4(s.mean), site: t.mean === null ? null : r4(t.mean), dominant,
    coverage: Math.round(t.cov * 1000) / 1000, range_low: rangeLow, range_high: rangeHigh, needs_data: needs,
    alert: total >= cfg.alert_threshold && !needs, factors: fs, explanation, config_version: cfg.fingerprint,
  }
}

// ------------------------------------------------------------------ service

export interface CityData {
  sites: { id: string; city_id: string; lat: number; lon: number }[]
  checkins: CheckIn[]
  findings: Finding[]
  observers: Observer[]
  weather: Record<string, WeatherDay[]>
}

const day = (iso: string) => iso.slice(0, 10)

function addDays(isoDate: string, n: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(`${a}T00:00:00Z`) - Date.parse(`${b}T00:00:00Z`)) / 86400000)
}

export function isoWeek(isoDate: string): string {
  const d = new Date(`${isoDate}T00:00:00Z`)
  const dayNum = (d.getUTCDay() + 6) % 7
  d.setUTCDate(d.getUTCDate() - dayNum + 3)
  const year = d.getUTCFullYear()
  const firstThursday = new Date(Date.UTC(year, 0, 4))
  const week = 1 + Math.round(((d.getTime() - firstThursday.getTime()) / 86400000 - 3 + ((firstThursday.getUTCDay() + 6) % 7)) / 7)
  return `${year}-W${String(week).padStart(2, '0')}`
}

export const cellKey = (lat: number, lon: number) => `${Math.round(lat * 10) / 10}_${Math.round(lon * 10) / 10}`

function priorAccuracy(observers: Observer[]): Record<string, Record<string, number>> {
  const out: Record<string, Record<string, number>> = {}
  for (const o of observers) {
    const perQ = ((o.calibration ?? {}) as { per_question?: Record<string, { agreement: number }> }).per_question ?? {}
    const qs = Object.keys(perQ)
    if (!qs.length) continue
    const mean = qs.reduce((s, q) => s + perQ[q].agreement, 0) / qs.length
    out[o.id] = { _mean: mean, ...Object.fromEntries(qs.map((q) => [q, perQ[q].agreement])) }
  }
  return out
}

export function computeCity(data: CityData, cityId: string, asOf: string, cfg: RiskConfig): (RiskScore & Combined)[] {
  const start = addDays(asOf, -(cfg.window_days - 1))
  const sites = data.sites.filter((s) => s.city_id === cityId)
  const siteIds = new Set(sites.map((s) => s.id))
  const checkins = data.checkins
    .filter((c) => siteIds.has(c.site_id) && day(c.observed_at) >= start && day(c.observed_at) <= asOf)
    .sort((a, b) => a.id - b.id)
  const byCheckin = new Map<number, Finding[]>()
  for (const f of data.findings) if (checkins.some((c) => c.id === f.checkin_id)) byCheckin.set(f.checkin_id, [...(byCheckin.get(f.checkin_id) ?? []), f])
  const obsIds = new Set(checkins.map((c) => c.observer_id))
  const priors = priorAccuracy(data.observers.filter((o) => obsIds.has(o.id)))

  // habitat posteriors, city-wide per question
  const habitatBySite: Record<string, Record<string, HabitatQ>> = {}
  const relSum: Record<string, number> = {}
  const relN: Record<string, number> = {}
  for (const q of Object.keys(cfg.habitat.questions)) {
    const labels = checkins.filter((c) => APE.includes(String(c.answers[q]))).map((c) => [c.site_id, c.observer_id, String(c.answers[q])] as [string, string, string])
    if (!labels.length) continue
    const prior = Object.fromEntries(Object.entries(priors).map(([o, p]) => [o, q in p ? p[q] : p._mean]))
    const res = dawidSkene(labels, { classes: APE, priorAccuracy: prior, priorStrength: 5 })
    for (const [o, r] of Object.entries(res.reliability)) {
      relSum[o] = (relSum[o] ?? 0) + r
      relN[o] = (relN[o] ?? 0) + 1
    }
    res.items.forEach((site, i) => {
      const post = res.posterior[i]
      const used = checkins.filter((c) => c.site_id === site && APE.includes(String(c.answers[q])))
      habitatBySite[site] = habitatBySite[site] ?? {}
      habitatBySite[site][q] = {
        expected: r4(post.reduce((s, p, k) => s + p * APE_SCORE[APE[k]], 0)),
        posterior: Object.fromEntries(APE.map((k, n) => [k, r4(post[n])])),
        n_reports: used.length,
        raw: used.map((c) => ({ checkin_id: c.id, observer: c.observer_id, answer: String(c.answers[q]) })),
      }
    })
  }
  const reliability: Record<string, number> = Object.fromEntries(Object.keys(relSum).map((o) => [o, relSum[o] / relN[o]]))

  return sites.map((site) => {
    const mine = checkins.filter((c) => c.site_id === site.id)
    const larval: LarvalReport[] = []
    const predators: PredatorReport[] = []
    const dead: DeadBirdReport[] = []
    for (const c of mine) {
      const w = r4(reliability[c.observer_id] ?? 0.7)
      const fs = byCheckin.get(c.id) ?? []
      const by = Object.fromEntries(fs.map((f) => [f.subject, f]))
      const dips = by.larval_dips
      if (dips && dips.count !== null && dips.count !== undefined) {
        const n = ((dips.data?.dips as number[] | undefined)?.length) || 5
        larval.push({ checkin_id: c.id, observer: c.observer_id, per_dip: Math.round((dips.count / n) * 1000) / 1000, weight: w })
      }
      const amph = by.amphibians
      const birds = by.insectivorous_birds
      const bats = by.bats
      if (amph || birds || bats) {
        predators.push({
          checkin_id: c.id, observer: c.observer_id, weight: w,
          amphibians: amph ? (amph.citizen_answer ?? null) : null,
          birds: birds ? (birds.count ?? null) : null,
          bats: bats ? (bats.citizen_answer ?? null) : null,
        })
      }
      for (const f of fs) if (f.type === 'dead_bird' && f.count) dead.push({ checkin_id: c.id, count: f.count, date: day(c.observed_at) })
    }
    const all = data.weather[cellKey(site.lat, site.lon)] ?? []
    const weather = all.filter((d) => d.date >= start && d.date <= asOf)
    const latest = mine.length ? mine.map((c) => day(c.observed_at)).sort().at(-1)! : null
    const age = latest ? daysBetween(asOf, latest) : null
    const wAge = weather.length ? daysBetween(asOf, weather[weather.length - 1].date) : null
    const fs = [
      temperature(weather, cfg),
      drySpell(weather, cfg),
      habitat(habitatBySite[site.id] ?? {}, cfg),
      vectorPresence(larval, cfg),
      predatorDeficit(predators, cfg),
      hostSignal(mine.length ? dead : null, cfg),
    ]
    const ages: Record<string, number | null> = { temperature: wAge, dry_spell: wAge, habitat: age, vector_presence: age, predator_deficit: age, host_signal: age }
    for (const x of fs) x.data_age_days = ages[x.name]
    const out = combine(fs, cfg)
    return {
      ...out,
      site_id: site.id,
      week: isoWeek(asOf),
      as_of: asOf,
      checkin_ids: mine.map((c) => c.id),
      synthetic: mine.some((c) => c.synthetic),
    }
  })
}
