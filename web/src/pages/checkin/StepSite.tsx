import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../lib/context'
import { distanceM } from '../../lib/observer'
import type { Site } from '../../lib/types'

const SiteMap = lazy(() => import('../../components/SiteMap'))

export interface Position {
  lat: number
  lon: number
}

export function StepSite({
  siteId,
  onSelect,
  position,
  onPosition,
}: {
  siteId?: string
  onSelect: (id: string) => void
  position: Position | null
  onPosition: (p: Position | null) => void
}) {
  const { t } = useTranslation()
  const { client } = useApp()
  const [sites, setSites] = useState<Site[] | null>(null)
  const [error, setError] = useState(false)
  const [city, setCity] = useState<string>('')
  const [locating, setLocating] = useState<'idle' | 'busy' | 'denied'>('idle')

  const load = useMemo(
    () => () => {
      setError(false)
      client.listSites().then(setSites, () => setError(true))
    },
    [client],
  )
  useEffect(load, [load])

  const cities = useMemo(() => [...new Map((sites ?? []).map((s) => [s.city_id, s.city_name])).entries()], [sites])

  const visible = useMemo(() => {
    const list = (sites ?? []).filter((s) => !city || s.city_id === city)
    if (!position) return list
    return [...list].sort((a, b) => distanceM(position.lat, position.lon, a.lat, a.lon) - distanceM(position.lat, position.lon, b.lat, b.lon))
  }, [sites, city, position])

  function locate() {
    if (!('geolocation' in navigator)) return setLocating('denied')
    setLocating('busy')
    navigator.geolocation.getCurrentPosition(
      (p) => {
        onPosition({ lat: p.coords.latitude, lon: p.coords.longitude })
        setCity('')
        setLocating('idle')
      },
      () => setLocating('denied'),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    )
  }

  const selected = sites?.find((s) => s.id === siteId)

  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h2 id="step-heading" className="h1">
        {t('site.heading')}
      </h2>
      <p className="text-slate-700">{t('site.intro')}</p>

      <div className="flex flex-wrap items-end gap-3">
        <button type="button" className="btn-secondary" onClick={locate} disabled={locating === 'busy'}>
          {locating === 'busy' ? t('site.locating') : t('site.useLocation')}
        </button>
        <div>
          <label htmlFor="city" className="mb-1 block text-sm font-medium">
            {t('site.city')}
          </label>
          <select id="city" value={city} onChange={(e) => setCity(e.target.value)} className="min-h-11 rounded-lg border-2 border-slate-300 bg-white px-2">
            <option value="">{t('site.allCities')}</option>
            {cities.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {locating === 'denied' && <p className="text-sm text-amber-900">{t('site.locationDenied')}</p>}

      {error && (
        <div className="card">
          <p>{t('site.loadError')}</p>
          <button type="button" className="btn-secondary mt-2" onClick={load}>
            {t('site.retry')}
          </button>
        </div>
      )}
      {!sites && !error && <p aria-live="polite">{t('site.loading')}</p>}

      {sites && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Suspense fallback={<div className="h-80 rounded-xl bg-slate-200" />}>
            <SiteMap points={visible.map((site) => ({ site }))} selectedId={siteId} onSelect={onSelect} label={t('site.mapLabel')} />
          </Suspense>
          <div>
            <h3 className="mb-2 font-semibold">{t('site.listLabel')}</h3>
            <ul className="max-h-80 space-y-2 overflow-y-auto pr-1">
              {visible.slice(0, 40).map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    aria-pressed={s.id === siteId}
                    aria-label={t('site.choose', { name: `${s.name} (${s.id}, ${s.city_name})` })}
                    onClick={() => onSelect(s.id)}
                    className={`flex min-h-12 w-full items-center justify-between rounded-lg border-2 px-3 py-2 text-left ${
                      s.id === siteId ? 'border-brand-700 bg-brand-50' : 'border-slate-200 bg-white hover:border-brand-600'
                    }`}
                  >
                    <span>
                      <span className="font-medium">{s.name}</span>
                      <span className="muted block">
                        {s.id} · {s.city_name}
                      </span>
                    </span>
                    {position && (
                      <span className="muted">{t('site.distance', { km: (distanceM(position.lat, position.lon, s.lat, s.lon) / 1000).toFixed(1) })}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      <p aria-live="polite" className="font-medium text-brand-900">
        {selected ? t('site.selected', { name: `${selected.name} (${selected.id})` }) : ''}
      </p>
    </section>
  )
}
