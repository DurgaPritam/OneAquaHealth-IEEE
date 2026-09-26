import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { TrendChart } from '../components/TrendChart'
import { useApp } from '../lib/context'
import type { Action, Band, MeasureCatalogue, RiskFactor, RiskScore, Site } from '../lib/types'

const SiteMap = lazy(() => import('../components/SiteMap'))

const THRESHOLD = 0.55
// Status palette (dataviz reference): never colour alone, always icon + label.
const BAND_STYLE: Record<Band, { colour: string; icon: string; chip: string }> = {
  low: { colour: '#0ca30c', icon: '●', chip: 'bg-green-100 text-green-950' },
  moderate: { colour: '#fab219', icon: '▲', chip: 'bg-amber-100 text-amber-950' },
  high: { colour: '#ec835a', icon: '◆', chip: 'bg-orange-100 text-orange-950' },
  very_high: { colour: '#d03b3b', icon: '■', chip: 'bg-red-100 text-red-950' },
}
const SEASON = new Set(['temperature', 'dry_spell'])

export function BandBadge({ band }: { band: Band }) {
  const { t } = useTranslation()
  const s = BAND_STYLE[band]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${s.chip}`}>
      <span aria-hidden="true" style={{ color: s.colour }}>{s.icon}</span>
      {t(`city.band_${band}`)}
    </span>
  )
}

export function City() {
  const { t } = useTranslation()
  const { client } = useApp()
  const [sites, setSites] = useState<Site[]>([])
  const [city, setCity] = useState('CO')
  const [scores, setScores] = useState<RiskScore[] | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setScores(await client.latestRisk(city))
  }, [client, city])

  useEffect(() => {
    void client.listSites().then(setSites)
  }, [client])
  useEffect(() => {
    void load()
  }, [load])

  const siteById = useMemo(() => Object.fromEntries(sites.map((s) => [s.id, s])), [sites])
  const cities = useMemo(() => [...new Map(sites.map((s) => [s.city_id, s.city_name])).entries()], [sites])
  const ranked = useMemo(() => [...(scores ?? [])].sort((a, b) => b.total - a.total), [scores])
  const season = ranked.find((r) => r.factors.some((f) => f.name === 'temperature' && f.value !== null))
  const seasonValue = season ? seasonOf(season) : null
  const current = ranked.find((r) => r.site_id === selected) ?? null

  async function recompute() {
    setBusy(true)
    try {
      await client.computeRisk(city)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <div className="mr-auto">
          <h1 className="h1">{t('city.heading')}</h1>
          <p className="max-w-2xl text-slate-700">{t('city.intro')}</p>
        </div>
        <div>
          <label htmlFor="city-select" className="mb-1 block text-sm font-medium">{t('city.city')}</label>
          <select id="city-select" value={city} onChange={(e) => { setCity(e.target.value); setSelected(null) }} className="min-h-11 rounded-lg border-2 border-slate-300 bg-white px-2">
            {cities.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void recompute()} disabled={busy}>
          {busy ? t('city.refreshing') : t('city.refresh')}
        </button>
      </div>

      {ranked.some((r) => r.synthetic) && (
        <p className="inline-block rounded-full bg-violet-100 px-3 py-1 text-sm font-semibold text-violet-950">{t('city.synthetic')}</p>
      )}

      {seasonValue !== null && (
        <div className="card">
          <p className="font-semibold">{t('city.season', { value: seasonValue.toFixed(2) })}</p>
          <p className="muted">{t('city.seasonHelp')} {t('city.weatherCredit')}</p>
        </div>
      )}

      {scores && scores.length === 0 && <p>{t('city.noScores')}</p>}

      {ranked.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
          <Suspense fallback={<div className="h-80 rounded-xl bg-slate-200" />}>
            <SiteMap
              label={t('city.mapLabel')}
              selectedId={selected ?? undefined}
              onSelect={setSelected}
              points={ranked.filter((r) => siteById[r.site_id]).map((r) => ({
                site: siteById[r.site_id],
                colour: r.needs_data ? '#898781' : BAND_STYLE[r.band].colour,
                label: `${siteById[r.site_id].name}: ${r.total.toFixed(2)} ${t(`city.band_${r.band}`)}`,
              }))}
            />
          </Suspense>
          <RankedTable ranked={ranked} siteById={siteById} selected={selected} onSelect={setSelected} />
        </div>
      )}

      {current && <SitePanel score={current} site={siteById[current.site_id]} />}

      <AlertQueue city={city} siteById={siteById} onDecided={load} />
    </div>
  )
}

function seasonOf(r: RiskScore): number | null {
  const w: Record<string, number> = { temperature: 0.75, dry_spell: 0.25 }
  const parts = r.factors.filter((f) => SEASON.has(f.name) && f.value !== null)
  const ws = parts.reduce((s, f) => s + w[f.name], 0)
  return ws ? parts.reduce((s, f) => s + w[f.name] * (f.value as number), 0) / ws : null
}

function newestAge(r: RiskScore): number | null {
  const ages = r.factors.filter((f) => !SEASON.has(f.name) && f.value !== null && f.data_age_days !== null).map((f) => f.data_age_days as number)
  return ages.length ? Math.min(...ages) : null
}

function RankedTable({ ranked, siteById, selected, onSelect }: { ranked: RiskScore[]; siteById: Record<string, Site>; selected: string | null; onSelect: (id: string) => void }) {
  const { t } = useTranslation()
  return (
    <div className="card max-h-[28rem] overflow-auto p-0">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{t('city.tableLabel')}</caption>
        <thead className="sticky top-0 bg-white">
          <tr className="border-b border-slate-200">
            <th scope="col" className="p-2">{t('city.site')}</th>
            <th scope="col" className="p-2">{t('city.index')}</th>
            <th scope="col" className="p-2">{t('city.band')}</th>
            <th scope="col" className="p-2">{t('city.coverage')}</th>
            <th scope="col" className="p-2">{t('city.age')}</th>
          </tr>
        </thead>
        <tbody>
          {ranked.map((r) => {
            const s = siteById[r.site_id]
            const age = newestAge(r)
            return (
              <tr key={r.site_id} className={`border-b border-slate-100 ${selected === r.site_id ? 'bg-brand-50' : ''}`}>
                <td className="p-2">
                  <button type="button" className="text-left font-medium text-brand-700 underline-offset-2 hover:underline" aria-pressed={selected === r.site_id}
                    aria-label={t('city.select', { name: s?.name ?? r.site_id })} onClick={() => onSelect(r.site_id)}>
                    {s?.name ?? r.site_id} <span className="muted">({r.site_id})</span>
                  </button>
                  {r.alert && <span className="ml-2 rounded bg-red-700 px-1.5 py-0.5 text-xs font-bold text-white">{t('city.alert')}</span>}
                  {r.needs_data && <span className="ml-2 rounded bg-slate-200 px-1.5 py-0.5 text-xs font-semibold text-slate-800">{t('city.needsData')}</span>}
                </td>
                <td className="p-2 tabular-nums">
                  {r.total.toFixed(2)}
                  <span className="muted block text-xs">{r.range_low.toFixed(2)} to {r.range_high.toFixed(2)}</span>
                </td>
                <td className="p-2"><BandBadge band={r.band} /></td>
                <td className="p-2 tabular-nums">{Math.round(r.coverage * 100)}%</td>
                <td className="p-2">{age === null ? t('city.noData') : age === 0 ? t('city.today') : t('city.days', { count: age })}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function SitePanel({ score, site }: { score: RiskScore; site?: Site }) {
  const { t } = useTranslation()
  const { client } = useApp()
  const [history, setHistory] = useState<RiskScore[]>([])
  useEffect(() => {
    void client.riskHistory(score.site_id).then(setHistory)
  }, [client, score.site_id, score.total])
  const name = site?.name ?? score.site_id
  const seasonF = score.factors.filter((f) => SEASON.has(f.name))
  const siteF = score.factors.filter((f) => !SEASON.has(f.name))
  return (
    <section aria-labelledby="panel-heading" className="card space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="panel-heading" className="h2 mr-2">{t('city.panelHeading', { name, total: score.total.toFixed(2) })}</h2>
        <BandBadge band={score.band} />
      </div>
      <p className="text-sm text-slate-700">{score.explanation}</p>
      <FactorTable title={t('city.seasonPart')} factors={seasonF} showContribution={false} />
      <FactorTable title={t('city.sitePart')} factors={siteF} showContribution />
      <TrendChart history={history} name={name} threshold={THRESHOLD} />
      {score.checkin_ids.length > 0 && <p className="muted">{t('city.checkins', { ids: score.checkin_ids.join(', ') })}</p>}
      <p className="muted">{score.config_version}</p>
    </section>
  )
}

function FactorTable({ title, factors, showContribution }: { title: string; factors: RiskFactor[]; showContribution: boolean }) {
  const { t } = useTranslation()
  return (
    <div>
      <h3 className="mb-2 font-semibold">{title}</h3>
      <ul className="space-y-3">
        {factors.map((f) => (
          <li key={f.name}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-medium">{f.label}</span>
              <span className="tabular-nums text-sm">
                {f.value === null ? t('city.noData') : `${t('city.value')} ${f.value.toFixed(2)}`}
                {' · '}{t('city.weight')} {f.weight}
                {showContribution && f.value !== null && ` · ${t('city.contribution')} ${f.contribution.toFixed(2)}`}
              </span>
            </div>
            <div className="mt-1 h-2 w-full rounded-full bg-slate-100" aria-hidden="true">
              <div className="h-2 rounded-full" style={{ width: `${Math.round((f.value ?? 0) * 100)}%`, background: f.value === null ? 'transparent' : '#2a78d6' }} />
            </div>
            <p className="mt-1 text-sm text-slate-700">{f.explanation}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}

const OFFICER_KEY = 'aquasentinel.officer'

function AlertQueue({ city, siteById, onDecided }: { city: string; siteById: Record<string, Site>; onDecided: () => void }) {
  const { t } = useTranslation()
  const { client } = useApp()
  const [actions, setActions] = useState<Action[]>([])
  const [catalogue, setCatalogue] = useState<MeasureCatalogue | null>(null)
  const [officer, setOfficer] = useState(() => {
    try { return localStorage.getItem(OFFICER_KEY) ?? '' } catch { return '' }
  })
  const [status, setStatus] = useState('')

  const load = useCallback(async () => {
    const all = await client.listActions()
    setActions(all.filter((a) => siteById[a.site_id]?.city_id === city))
  }, [client, city, siteById])
  useEffect(() => { void load() }, [load])
  useEffect(() => { void client.measures().then(setCatalogue) }, [client])

  async function draft() {
    const made = await client.draftActions(city)
    setStatus(t('city.drafted', { n: made.length }))
    await load()
  }

  const drafted = actions.filter((a) => a.status === 'drafted')
  const decided = actions.filter((a) => a.status !== 'drafted').slice(-5).reverse()

  return (
    <section aria-labelledby="queue-heading" className="card space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="queue-heading" className="h2 mr-auto">{t('city.queueHeading')}</h2>
        <button type="button" className="btn-secondary" onClick={() => void draft()}>{t('city.draftNow')}</button>
      </div>
      <p className="muted">{t('city.queueIntro')}</p>
      <p aria-live="polite" className="text-sm font-medium text-brand-900">{status}</p>
      <div className="max-w-sm">
        <label htmlFor="officer" className="mb-1 block text-sm font-medium">{t('city.officer')}</label>
        <input id="officer" value={officer} aria-describedby="officer-help"
          onChange={(e) => { setOfficer(e.target.value); try { localStorage.setItem(OFFICER_KEY, e.target.value) } catch { /* ignore */ } }}
          className="min-h-11 w-full rounded-lg border-2 border-slate-300 px-2" />
        <p id="officer-help" className="muted mt-1">{t('city.officerHelp')}</p>
      </div>
      {drafted.length === 0 && <p>{t('city.noDrafts')}</p>}
      <ul className="space-y-3">
        {drafted.map((a) => (
          <DraftCard key={a.id} action={a} site={siteById[a.site_id]} catalogue={catalogue} officer={officer}
            onDone={(msg) => { setStatus(msg); void load(); onDecided() }} />
        ))}
      </ul>
      {decided.length > 0 && (
        <div>
          <h3 className="mb-1 font-semibold">{t('city.decidedHeading')}</h3>
          <ul className="space-y-1 text-sm">
            {decided.map((a) => (
              <li key={a.id}>
                <span className="font-medium">{t(`city.status_${a.status}`)}</span>: {a.title} · {siteById[a.site_id]?.name ?? a.site_id} · {a.approved_by}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function DraftCard({ action, site, catalogue, officer, onDone }: { action: Action; site?: Site; catalogue: MeasureCatalogue | null; officer: string; onDone: (msg: string) => void }) {
  const { t } = useTranslation()
  const { client } = useApp()
  const [editing, setEditing] = useState(false)
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const m = catalogue?.measures[action.measure_id]

  async function decide(approve: boolean) {
    if (!officer.trim()) return setError(t('city.officerRequired'))
    setError('')
    const res = await client.decideAction(action.id, approve, officer.trim(), note || undefined)
    onDone(t(approve ? 'city.approved' : 'city.dismissed', { officer: officer.trim(), n: res.messages.length }))
  }

  async function change(measureId: string) {
    await client.editAction(action.id, { measure_id: measureId })
    setEditing(false)
    onDone('')
  }

  return (
    <li className="rounded-xl border-2 border-slate-200 p-3">
      <p className="font-semibold">{action.title}</p>
      <p className="muted">{site?.name ?? action.site_id} ({action.site_id}) · {t('city.contributors', { count: action.contributors.length })}</p>
      {m && (
        <p className="mt-1 text-sm">
          {m.catalogue && m.section ? (
            <a className="underline" href={catalogue?.source_url} target="_blank" rel="noreferrer">
              {t('city.measureSource', { section: m.section, page: m.page })}
            </a>
          ) : t('city.notCatalogue')}
        </p>
      )}
      {action.warnings.map((w) => (
        <div key={w} className="mt-2 rounded-lg border-l-4 border-amber-500 bg-amber-50 p-2 text-sm text-amber-950" role="note">
          <p className="font-semibold">{t('city.warningTitle')}</p>
          <p>{w}</p>
        </div>
      ))}
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer font-medium text-brand-700">{t('city.rationale')}</summary>
        <p className="mt-1 text-slate-700">{action.rationale}</p>
      </details>
      {editing && catalogue && (
        <div className="mt-2">
          <label htmlFor={`measure-${action.id}`} className="mb-1 block text-sm font-medium">{t('city.measure')}</label>
          <select id={`measure-${action.id}`} defaultValue={action.measure_id} onChange={(e) => void change(e.target.value)}
            className="min-h-11 w-full rounded-lg border-2 border-slate-300 bg-white px-2">
            {Object.entries(catalogue.measures).map(([id, md]) => <option key={id} value={id}>{md.title}</option>)}
          </select>
        </div>
      )}
      <div className="mt-2">
        <label htmlFor={`note-${action.id}`} className="mb-1 block text-sm font-medium">{t('city.note')}</label>
        <input id={`note-${action.id}`} value={note} onChange={(e) => setNote(e.target.value)} className="min-h-11 w-full rounded-lg border-2 border-slate-300 px-2" />
      </div>
      {error && <p className="mt-1 text-sm font-medium text-red-800">{error}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className="btn-primary" onClick={() => void decide(true)}>{t('city.approve')}</button>
        <button type="button" className="btn-secondary" onClick={() => setEditing((v) => !v)} aria-expanded={editing}>{t('city.edit')}</button>
        <button type="button" className="btn-secondary" onClick={() => void decide(false)}>{t('city.dismiss')}</button>
      </div>
    </li>
  )
}
