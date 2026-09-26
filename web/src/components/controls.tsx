import { useId, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { sanitisePhoto } from '../lib/photo'

export interface Option {
  value: string
  label: string
}

/** A radio group drawn as large buttons. Native radios keep it keyboard and screen reader friendly. */
export function Segmented({
  legend,
  options,
  value,
  onChange,
  hint,
  allowClear = true,
}: {
  legend: ReactNode
  options: Option[]
  value: string | undefined
  onChange: (value: string | undefined) => void
  hint?: ReactNode
  allowClear?: boolean
}) {
  const { t } = useTranslation()
  const name = useId()
  return (
    <fieldset className="py-2">
      <legend className="mb-1.5 font-medium text-slate-900">{legend}</legend>
      {hint && <p className="muted mb-2">{hint}</p>}
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label
            key={o.value}
            className={`inline-flex min-h-11 cursor-pointer items-center rounded-lg border-2 px-3.5 text-sm font-medium has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-brand-600 ${
              value === o.value ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300 bg-white text-slate-800 hover:border-brand-600'
            }`}
          >
            <input
              type="radio"
              className="sr-only"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
            />
            {o.label}
          </label>
        ))}
        {allowClear && value !== undefined && (
          <button type="button" className="btn-ghost text-sm" onClick={() => onChange(undefined)}>
            {t('common.clear')}
          </button>
        )}
      </div>
    </fieldset>
  )
}

/** Whole-number input with large plus and minus buttons. */
export function Stepper({
  label,
  value,
  onChange,
  min = 0,
  max = 999,
}: {
  label: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
}) {
  const { t } = useTranslation()
  const id = useId()
  const set = (n: number) => onChange(Math.max(min, Math.min(max, Number.isFinite(n) ? Math.round(n) : min)))
  return (
    <div className="py-2">
      <label htmlFor={id} className="mb-1.5 block font-medium text-slate-900">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <button type="button" className="btn-secondary w-12 text-xl" aria-label={t('common.decrease', { label })} onClick={() => set(value - 1)}>
          −
        </button>
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          value={value}
          onChange={(e) => set(Number(e.target.value))}
          className="min-h-11 w-20 rounded-lg border-2 border-slate-300 text-center text-lg font-semibold"
        />
        <button type="button" className="btn-secondary w-12 text-xl" aria-label={t('common.increase', { label })} onClick={() => set(value + 1)}>
          +
        </button>
      </div>
    </div>
  )
}

/** Photo picker. The photo is re-encoded on the device, which removes EXIF and GPS. */
export function PhotoInput({
  label,
  photo,
  onChange,
  sanitise = sanitisePhoto,
}: {
  label: string
  photo: Blob | undefined
  onChange: (blob: Blob | undefined) => void
  sanitise?: (file: Blob) => Promise<Blob>
}) {
  const { t } = useTranslation()
  const id = useId()
  const [error, setError] = useState(false)
  const [url, setUrl] = useState<string>()

  async function pick(file: File | undefined) {
    if (!file) return
    setError(false)
    try {
      const clean = await sanitise(file)
      if (url) URL.revokeObjectURL(url)
      setUrl(typeof URL.createObjectURL === 'function' ? URL.createObjectURL(clean) : undefined)
      onChange(clean)
    } catch {
      setError(true)
    }
  }

  return (
    <div className="py-2">
      <span className="mb-1.5 block font-medium text-slate-900">{label}</span>
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor={id} className="btn-secondary cursor-pointer">
          {photo ? t('common.replacePhoto') : t('common.addPhoto')}
        </label>
        <input id={id} type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => void pick(e.target.files?.[0])} />
        {photo && (
          <button type="button" className="btn-ghost" onClick={() => onChange(undefined)}>
            {t('common.removePhoto')}
          </button>
        )}
      </div>
      {photo && url && <img src={url} alt="" className="mt-2 max-h-40 rounded-lg border border-slate-200" />}
      <p aria-live="polite" className="muted mt-1">
        {photo ? t('common.photoAdded') : error ? t('common.photoError') : ''}
      </p>
    </div>
  )
}

export function Callout({ tone = 'info', title, children }: { tone?: 'info' | 'danger' | 'why'; title?: ReactNode; children: ReactNode }) {
  const styles = {
    info: 'border-sky-300 bg-sky-50 text-sky-950',
    danger: 'border-red-700 bg-red-50 text-red-950',
    why: 'border-brand-600 bg-brand-50 text-brand-900',
  }[tone]
  return (
    <div className={`rounded-lg border-l-4 p-3 ${styles}`} role={tone === 'danger' ? 'alert' : undefined}>
      {title && <p className="mb-1 font-bold">{title}</p>}
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  )
}
