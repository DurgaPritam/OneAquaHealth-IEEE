import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { RiskScore } from '../lib/types'

// Palette from the dataviz reference instance: one blue series, light blue range band,
// recessive grid and axes, text in ink tokens (never the series colour).
const C = { line: '#2a78d6', band: '#cde2fb', grid: '#e1e0d9', axis: '#c3c2b7', muted: '#6b6a66', ink: '#0b0b0b', surface: '#fcfcfb' }

export function TrendChart({ history, name, threshold }: { history: RiskScore[]; name: string; threshold: number }) {
  const { t } = useTranslation()
  const titleId = useId()
  const [hover, setHover] = useState<number | null>(null)
  if (history.length === 0) return null
  const W = 520
  const H = 200
  const pad = { l: 36, r: 12, t: 12, b: 28 }
  const iw = W - pad.l - pad.r
  const ih = H - pad.t - pad.b
  const x = (i: number) => pad.l + (history.length === 1 ? iw / 2 : (i * iw) / (history.length - 1))
  const y = (v: number) => pad.t + ih * (1 - v)
  const line = history.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(r.total).toFixed(1)}`).join(' ')
  const band =
    history.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(r.range_high).toFixed(1)}`).join(' ') +
    ' ' +
    [...history].reverse().map((r, j) => `L${x(history.length - 1 - j).toFixed(1)} ${y(r.range_low).toFixed(1)}`).join(' ') +
    ' Z'
  const h = hover !== null ? history[hover] : null

  return (
    <figure className="space-y-2">
      <figcaption id={titleId} className="font-semibold">
        {t('city.trend')}
      </figcaption>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={titleId} aria-describedby={`${titleId}-d`} className="h-auto w-full rounded-lg" style={{ background: C.surface }}
          onMouseLeave={() => setHover(null)}>
          <desc id={`${titleId}-d`}>{t('city.trendLabel', { name, threshold })}</desc>
          {[0, 0.25, 0.5, 0.75, 1].map((v) => (
            <g key={v}>
              <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke={C.grid} strokeWidth={1} />
              <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" fontSize={11} fill={C.muted}>
                {v.toFixed(2)}
              </text>
            </g>
          ))}
          <path d={band} fill={C.band} opacity={0.8} />
          <line x1={pad.l} x2={W - pad.r} y1={y(threshold)} y2={y(threshold)} stroke={C.ink} strokeWidth={1} strokeDasharray="5 4" />
          <text x={W - pad.r} y={y(threshold) - 5} textAnchor="end" fontSize={11} fill={C.ink}>
            {t('city.threshold')} {threshold}
          </text>
          <path d={line} fill="none" stroke={C.line} strokeWidth={2} strokeLinejoin="round" />
          {history.map((r, i) => (
            <g key={r.week}>
              <circle cx={x(i)} cy={y(r.total)} r={4} fill={C.line} stroke={C.surface} strokeWidth={2} />
              <text x={x(i)} y={H - 8} textAnchor="middle" fontSize={11} fill={C.muted}>
                {r.week.slice(5)}
              </text>
              <rect x={x(i) - iw / (2 * Math.max(1, history.length - 1))} y={pad.t} width={iw / Math.max(1, history.length - 1)} height={ih}
                fill="transparent" onMouseEnter={() => setHover(i)} />
            </g>
          ))}
          {h && hover !== null && <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={pad.t + ih} stroke={C.axis} strokeWidth={1} pointerEvents="none" />}
        </svg>
        {h && hover !== null && (
          <div className="pointer-events-none absolute top-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs shadow"
            style={{ left: `${Math.min(70, (x(hover) / W) * 100)}%` }}>
            <p className="font-semibold">{h.week}</p>
            <p>{t('city.index')}: {h.total.toFixed(2)}</p>
            <p>{t('city.range')}: {h.range_low.toFixed(2)} to {h.range_high.toFixed(2)}</p>
          </div>
        )}
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer font-medium text-brand-700">{t('city.trendTable')}</summary>
        <table className="mt-2 w-full text-left">
          <thead>
            <tr><th scope="col">Week</th><th scope="col">{t('city.index')}</th><th scope="col">{t('city.range')}</th><th scope="col">{t('city.band')}</th></tr>
          </thead>
          <tbody>
            {history.map((r) => (
              <tr key={r.week}><td>{r.week}</td><td>{r.total.toFixed(2)}</td><td>{r.range_low.toFixed(2)} to {r.range_high.toFixed(2)}</td><td>{t(`city.band_${r.band}`)}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
