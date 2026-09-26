import { useTranslation } from 'react-i18next'
import { answerKeys, questions, type WizardState } from '../../lib/checkin'

export function StepReview({
  s,
  siteLabel,
  onConsent,
  onEdit,
  showConsentError,
  children,
}: {
  s: WizardState
  siteLabel: string
  onConsent: (v: boolean) => void
  onEdit: (step: number) => void
  showConsentError: boolean
  children?: React.ReactNode
}) {
  const { t } = useTranslation()
  const streamAnswered = questions.sections
    .filter((sec) => !s.skipped.includes(sec.id))
    .flatMap(answerKeys)
    .filter((k) => s.answers[k] !== undefined).length
  const total = s.dips.reduce((a, b) => a + b, 0)
  const photos = [s.cupPhoto, s.predatorPhoto, s.deadBirdsSeen === 'yes' ? s.deadBirdPhoto : undefined].filter(Boolean).length
  const predators = [
    s.amphibians && `${t('predators.amphibians')}: ${t(`predators.amph_${s.amphibians}`)}`,
    `${t('predators.birds')}: ${s.birds}`,
    s.bats && `${t('predators.bats')}: ${t(`predators.bats_${s.bats}`)}`,
  ].filter(Boolean)

  const rows: [string, React.ReactNode, number][] = [
    [t('review.site'), siteLabel, 0],
    [t('review.stream'), String(streamAnswered), 1],
    [t('review.larvae'), `${total} (${s.dips.join(', ')})`, 2],
    [t('review.predators'), predators.join('; '), 3],
    [t('review.deadBirds'), s.deadBirdsSeen === 'yes' ? String(s.deadBirds) : t('review.none'), 4],
    [t('review.photos'), String(photos), 2],
  ]

  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h1 id="step-heading" className="h1">
        {t('review.heading')}
      </h1>
      <dl className="card divide-y divide-slate-100">
        {rows.map(([label, value, step]) => (
          <div key={label} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <dt className="font-medium">{label}</dt>
            <dd className="flex items-center gap-2 text-slate-700">
              <span>{value}</span>
              <button type="button" className="btn-ghost text-sm" onClick={() => onEdit(step)} aria-label={`${t('review.edit')}: ${label}`}>
                {t('review.edit')}
              </button>
            </dd>
          </div>
        ))}
      </dl>
      {children}
      <div className="card">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            className="mt-1 h-6 w-6 shrink-0 accent-brand-700"
            checked={s.consent}
            onChange={(e) => onConsent(e.target.checked)}
            aria-describedby={showConsentError ? 'consent-error' : undefined}
          />
          <span>{t('review.consent')}</span>
        </label>
        {showConsentError && (
          <p id="consent-error" className="mt-2 font-medium text-red-800">
            {t('review.consentRequired')}
          </p>
        )}
      </div>
    </section>
  )
}
