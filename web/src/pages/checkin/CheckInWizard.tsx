import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { buildDraft, emptyState, type WizardState } from '../../lib/checkin'
import { useApp } from '../../lib/context'
import { enqueue } from '../../lib/queue'
import type { Site } from '../../lib/types'
import { StepDeadBirds, StepLarvae, StepPredators } from './StepModules'
import { StepReview } from './StepReview'
import { StepSite, type Position } from './StepSite'
import { StepStream } from './StepStream'

const STEP_KEYS = ['site', 'stream', 'larvae', 'predators', 'deadBirds', 'review'] as const

export function CheckInWizard({ uuid = () => crypto.randomUUID() }: { uuid?: () => string }) {
  const { t } = useTranslation()
  const { client, observerId, online, sync, refreshPending, store } = useApp()
  const [step, setStep] = useState(0)
  const [s, setS] = useState<WizardState>(emptyState)
  const [position, setPosition] = useState<Position | null>(null)
  const [site, setSite] = useState<Site | undefined>()
  const [consentError, setConsentError] = useState(false)
  const [done, setDone] = useState<null | 'queued' | 'sent'>(null)
  const headingRef = useRef<HTMLParagraphElement>(null)

  const patch = (p: Partial<WizardState>) => setS((prev) => ({ ...prev, ...p }))

  useEffect(() => {
    if (!s.siteId) return
    void client.listSites().then((all) => setSite(all.find((x) => x.id === s.siteId)))
  }, [client, s.siteId])

  function go(next: number) {
    setStep(next)
    window.scrollTo?.({ top: 0 })
    requestAnimationFrame(() => headingRef.current?.focus())
  }

  async function submit() {
    if (!s.consent) {
      setConsentError(true)
      return
    }
    const { draft, photos } = buildDraft(s, { observerId, now: new Date(), uuid: uuid(), position })
    await enqueue(draft, photos, store)
    await refreshPending()
    if (online) await sync()
    const left = await store.outbox.get(draft.client_uuid)
    setDone(left ? 'queued' : 'sent')
  }

  if (done) {
    return (
      <section aria-labelledby="done-heading" className="card mx-auto max-w-xl space-y-3 text-center">
        <h2 id="done-heading" className="h1">
          {t('done.heading')}
        </h2>
        <p>{done === 'sent' ? t('done.sent') : t('done.queued')}</p>
        <p className="muted">{t('done.next')}</p>
        <div className="flex flex-wrap justify-center gap-3">
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              setS(emptyState())
              setDone(null)
              go(0)
            }}
          >
            {t('done.another')}
          </button>
          <Link to="/" className="btn-secondary">
            {t('done.home')}
          </Link>
        </div>
      </section>
    )
  }

  const canNext = step !== 0 || Boolean(s.siteId)
  const last = step === STEP_KEYS.length - 1

  return (
    <div className="space-y-5">
      <ol className="flex gap-1" aria-hidden="true">
        {STEP_KEYS.map((k, i) => (
          <li key={k} className={`h-2 flex-1 rounded-full ${i <= step ? 'bg-brand-600' : 'bg-slate-200'}`} />
        ))}
      </ol>
      <p ref={headingRef} tabIndex={-1} className="muted font-medium" aria-live="polite">
        {t('steps.progress', { current: step + 1, total: STEP_KEYS.length, name: t(`steps.${STEP_KEYS[step]}`) })}
      </p>

      {step === 0 && <StepSite siteId={s.siteId} onSelect={(id) => patch({ siteId: id })} position={position} onPosition={setPosition} />}
      {step === 1 && (
        <StepStream
          answers={s.answers}
          skipped={s.skipped}
          onAnswer={(k, v) =>
            setS((prev) => {
              const answers = { ...prev.answers }
              if (v === undefined) delete answers[k]
              else answers[k] = v
              return { ...prev, answers }
            })
          }
          onToggleSkip={(id) =>
            setS((prev) => ({ ...prev, skipped: prev.skipped.includes(id) ? prev.skipped.filter((x) => x !== id) : [...prev.skipped, id] }))
          }
        />
      )}
      {step === 2 && <StepLarvae s={s} patch={patch} />}
      {step === 3 && <StepPredators s={s} patch={patch} />}
      {step === 4 && <StepDeadBirds s={s} patch={patch} />}
      {step === 5 && (
        <StepReview
          s={s}
          siteLabel={site ? `${site.name} (${site.id})` : (s.siteId ?? '')}
          onConsent={(v) => {
            patch({ consent: v })
            if (v) setConsentError(false)
          }}
          onEdit={go}
          showConsentError={consentError}
        />
      )}

      <div className="sticky bottom-0 -mx-4 flex items-center justify-between gap-3 border-t border-slate-200 bg-slate-50/95 px-4 py-3 backdrop-blur">
        <button type="button" className="btn-secondary" onClick={() => go(step - 1)} disabled={step === 0}>
          {t('common.back')}
        </button>
        {!canNext && <span className="muted">{t('site.none')}</span>}
        {last ? (
          <button type="button" className="btn-primary" onClick={() => void submit()}>
            {t('review.submit')}
          </button>
        ) : (
          <button type="button" className="btn-primary" onClick={() => go(step + 1)} disabled={!canNext}>
            {t('common.next')}
          </button>
        )}
      </div>
    </div>
  )
}
