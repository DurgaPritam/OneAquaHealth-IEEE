import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { allowedLabels, labelText, type AiItem, type Decision, type VisionType } from '../lib/ai'
import { useApp } from '../lib/context'

/**
 * Asks the AI about a photo and shows the answer as a chip the citizen must
 * accept, change or reject. Nothing is submitted until they decide.
 */
export function AiAssist({
  type,
  photo,
  siteId,
  keyResult,
  item,
  onChange,
}: {
  type: VisionType
  photo: Blob | undefined
  siteId?: string
  keyResult?: string | null
  item: AiItem | undefined
  onChange: (item: AiItem | undefined) => void
}) {
  const { t } = useTranslation()
  const { client, online } = useApp()
  const [busy, setBusy] = useState(false)
  const asked = useRef<Blob | undefined>(undefined)

  useEffect(() => {
    if (!photo) {
      asked.current = undefined
      if (item) onChange(undefined)
      return
    }
    if (asked.current === photo) return
    asked.current = photo
    if (!online) {
      onChange({ type, response: { available: false, error: 'offline', suggestions: [], dropped: [] } })
      return
    }
    setBusy(true)
    client
      .suggest(photo, type, siteId, keyResult ?? undefined)
      .then((response) => onChange({ type, response }))
      .catch(() => onChange({ type, response: { available: false, error: 'network', suggestions: [], dropped: [] } }))
      .finally(() => setBusy(false))
  }, [photo, online, client, type, siteId, keyResult, item, onChange])

  if (!photo) return null
  if (busy) return <p className="muted py-2" aria-live="polite">{t('ai.thinking')}</p>
  const response = item?.response
  if (!response) return null
  if (!response.available || response.suggestions.length === 0) {
    return (
      <div className="mt-2 space-y-2" aria-live="polite">
        <p className="rounded-lg bg-slate-100 p-3 text-sm">{t('ai.unavailable')}</p>
        <Dropped dropped={response.dropped} />
      </div>
    )
  }
  return (
    <div className="mt-2 space-y-2">
      <Chip type={type} item={item!} keyResult={keyResult} onDecide={(decision) => onChange({ ...item!, decision })} />
      <Dropped dropped={response.dropped} />
    </div>
  )
}

function Chip({ type, item, keyResult, onDecide }: { type: VisionType; item: AiItem; keyResult?: string | null; onDecide: (d: Decision | undefined) => void }) {
  const { t } = useTranslation()
  const selectId = useId()
  const top = item.response!.suggestions[0]
  const [changing, setChanging] = useState(item.decision?.kind === 'change')
  const decision = item.decision
  const pct = Math.round(top.confidence * 100)
  const disagree = type === 'adult_mosquito' && keyResult && keyResult !== 'not_sure' && keyResult !== top.label

  return (
    <div className="rounded-xl border-2 border-violet-300 bg-violet-50 p-3" role="group" aria-label={t('ai.chipLabel')}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-violet-700 px-2 py-0.5 text-xs font-semibold text-white">{t('ai.suggestion')}</span>
        {item.response!.mock && <span className="rounded-full border border-violet-700 px-2 py-0.5 text-xs font-semibold text-violet-900">{t('app.demoAi')}</span>}
      </div>
      <p className="mt-2 font-semibold text-slate-900">
        {top.text} <span className="font-normal text-slate-700">({t('ai.confidence', { pct })})</span>
      </p>
      <p className="text-sm text-slate-700">{top.reason}</p>
      {top.plausibility?.status === 'implausible' && (
        <p className="mt-2 rounded bg-amber-100 p-2 text-sm text-amber-950">{t('ai.implausible', { n: top.plausibility.gbif_occurrences ?? 0 })}</p>
      )}
      {disagree && (
        <p className="mt-2 rounded bg-amber-100 p-2 text-sm text-amber-950">
          {t('ai.disagree', { key: labelText(type, keyResult!), ai: top.text })}
        </p>
      )}

      {decision ? (
        <p className="mt-2 text-sm font-medium text-brand-900" aria-live="polite">
          {decision.kind === 'accept' && t('ai.accepted')}
          {decision.kind === 'reject' && t('ai.rejected')}
          {decision.kind === 'change' && t('ai.changed', { label: labelText(type, decision.label) })}{' '}
          <button type="button" className="btn-ghost text-sm" onClick={() => { setChanging(false); onDecide(undefined) }}>
            {t('ai.undo')}
          </button>
        </p>
      ) : (
        <>
          <p className="mt-2 text-sm font-medium text-violet-950">{t('ai.mustDecide')}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" className="btn-primary min-h-11 px-4 text-sm" onClick={() => onDecide({ kind: 'accept' })}>
              {t('ai.accept')}
            </button>
            <button type="button" className="btn-secondary text-sm" onClick={() => setChanging(true)} aria-expanded={changing}>
              {t('ai.change')}
            </button>
            <button type="button" className="btn-secondary text-sm" onClick={() => onDecide({ kind: 'reject' })}>
              {t('ai.reject')}
            </button>
          </div>
        </>
      )}
      {changing && !decision && (
        <div className="mt-2">
          <label htmlFor={selectId} className="mb-1 block text-sm font-medium">
            {t('ai.changeTo')}
          </label>
          <select
            id={selectId}
            defaultValue=""
            className="min-h-11 w-full rounded-lg border-2 border-slate-300 bg-white px-2"
            onChange={(e) => e.target.value && onDecide({ kind: 'change', label: e.target.value })}
          >
            <option value="">{t('ai.choose')}</option>
            {allowedLabels(type).map((l) => (
              <option key={l.id} value={l.id}>
                {l.text}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}

function Dropped({ dropped }: { dropped: { label: string; why: string }[] }) {
  const { t } = useTranslation()
  if (dropped.length === 0) return null
  return (
    <div className="rounded-lg border border-slate-300 bg-white p-3 text-sm">
      <p className="font-semibold">{t('ai.droppedTitle')}</p>
      <ul className="mt-1 list-disc pl-5">
        {dropped.map((d) => (
          <li key={d.label}>
            <span className="font-mono">“{d.label || '(empty)'}”</span>: {t('ai.droppedWhy')}
          </li>
        ))}
      </ul>
    </div>
  )
}
