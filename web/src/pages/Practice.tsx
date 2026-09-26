import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Callout, Segmented } from '../components/controls'
import { REFERENCE_ITEMS, SCALE_OPTIONS, scoreCalibration, type CalibrationResult, type ReferenceItem } from '../lib/calibration'
import { useApp } from '../lib/context'

const IMAGES = import.meta.glob('../../../data/reference_set/*.svg', { query: '?url', import: 'default', eager: true }) as Record<string, string>

function imageUrl(item: ReferenceItem): string {
  return Object.entries(IMAGES).find(([path]) => path.endsWith(`/${item.image}`))?.[1] ?? ''
}

function useQuestionText() {
  const { t } = useTranslation()
  return (item: ReferenceItem) => (item.question_id === 'larval_posture' ? t('calib.q_larval_posture') : t(`q.${item.question_id}`))
}

function useOptionLabel() {
  const { t } = useTranslation()
  return (scale: ReferenceItem['scale'], v: string) =>
    scale === 'posture' ? t(`calib.posture_${v}`) : scale === 'cover5' ? t(`scale.cover_${v}`) : t(`scale.${v}`)
}

export function Practice({ items = REFERENCE_ITEMS }: { items?: ReferenceItem[] }) {
  const { t } = useTranslation()
  const { client, observerId } = useApp()
  const [index, setIndex] = useState(-1)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<CalibrationResult | null>(null)
  const [saved, setSaved] = useState<'server' | 'local' | null>(null)
  const questionText = useQuestionText()
  const optionLabel = useOptionLabel()

  async function finish() {
    setResult(scoreCalibration(answers, items))
    try {
      await client.submitCalibration(observerId, answers)
      setSaved('server')
    } catch {
      setSaved('local')
    }
  }

  if (result) return <Results result={result} saved={saved} onAgain={() => { setAnswers({}); setResult(null); setIndex(0) }} />

  if (index < 0) {
    return (
      <section aria-labelledby="practice-heading" className="mx-auto max-w-2xl space-y-4">
        <h1 id="practice-heading" className="h1">
          {t('calib.heading')}
        </h1>
        <p>{t('calib.intro', { n: items.length })}</p>
        <Callout tone="why" title={t('common.whyItMatters')}>
          {t('calib.why')}
        </Callout>
        <p className="muted">{t('calib.referenceNote')}</p>
        <button type="button" className="btn-primary" onClick={() => setIndex(0)}>
          {t('calib.start')}
        </button>
      </section>
    )
  }

  const item = items[index]
  const last = index === items.length - 1
  return (
    <section aria-labelledby="practice-heading" className="mx-auto max-w-2xl space-y-4">
      <h1 id="practice-heading" className="h1">
        {t('calib.heading')}
      </h1>
      <p className="muted font-medium" aria-live="polite">
        {t('calib.progress', { current: index + 1, total: items.length })}
      </p>
      <div className="card space-y-3">
        <img src={imageUrl(item)} alt={t('calib.imageAlt', { id: item.id })} className="w-full rounded-lg border border-slate-200" width={400} height={260} />
        <Segmented
          legend={questionText(item)}
          options={SCALE_OPTIONS[item.scale].map((v) => ({ value: v, label: optionLabel(item.scale, v) }))}
          value={answers[item.id]}
          onChange={(v) => setAnswers((a) => {
            const next = { ...a }
            if (v === undefined) delete next[item.id]
            else next[item.id] = v
            return next
          })}
          allowClear={false}
        />
      </div>
      <div className="flex justify-between gap-3">
        <button type="button" className="btn-secondary" disabled={index === 0} onClick={() => setIndex(index - 1)}>
          {t('common.back')}
        </button>
        {last ? (
          <button type="button" className="btn-primary" disabled={!answers[item.id]} onClick={() => void finish()}>
            {t('calib.finish')}
          </button>
        ) : (
          <button type="button" className="btn-primary" disabled={!answers[item.id]} onClick={() => setIndex(index + 1)}>
            {t('common.next')}
          </button>
        )}
      </div>
    </section>
  )
}

function Results({ result, saved, onAgain }: { result: CalibrationResult; saved: 'server' | 'local' | null; onAgain: () => void }) {
  const { t } = useTranslation()
  const questionText = useQuestionText()
  const optionLabel = useOptionLabel()
  const byId = useMemo(() => Object.fromEntries(REFERENCE_ITEMS.map((i) => [i.id, i])), [])
  const tierColour = { new: 'bg-slate-200 text-slate-900', calibrated: 'bg-sky-100 text-sky-950', trusted: 'bg-emerald-100 text-emerald-950' }[result.tier]
  return (
    <section aria-labelledby="results-heading" className="mx-auto max-w-2xl space-y-4">
      <h1 id="results-heading" className="h1">
        {t('calib.resultsHeading')}
      </h1>
      <div className="card space-y-2">
        <p className="text-lg font-semibold">{t('calib.agreement', { kappa: result.overall_kappa.toFixed(2) })}</p>
        <p className="muted">{t('calib.kappaHelp')}</p>
        <p>
          <span className={`inline-block rounded-full px-3 py-1 font-semibold ${tierColour}`}>
            {t('calib.tierLabel', { tier: t(`calib.tier_${result.tier}`) })}
          </span>
        </p>
        <p className="muted">{t('calib.tierHelp')}</p>
        {saved && <p className="text-sm font-medium text-brand-900">{saved === 'server' ? t('calib.saved') : t('calib.savedOffline')}</p>}
      </div>

      <div className="card">
        <h2 className="h2">{t('calib.feedbackHeading')}</h2>
        {result.feedback.length === 0 && <p className="mt-2">{t('calib.noFeedback')}</p>}
        <ul className="mt-2 space-y-4">
          {result.feedback.map((f) => (
            <li key={f.key} className="border-l-4 border-amber-500 pl-3">
              <p className="font-medium">{t(f.key, { defaultValue: t('calib.fb.generic', { ref: f.examples[0].reference, ans: f.examples[0].answered }) })}</p>
              <ul className="mt-1 space-y-1 text-sm text-slate-700">
                {f.examples.map((ex) => {
                  const it = byId[ex.item]
                  return (
                    <li key={ex.item}>
                      {t('calib.lookAgain', { id: ex.item, rationale: ex.rationale })}{' '}
                      {t('calib.answeredVs', { ans: optionLabel(it.scale, ex.answered), ref: optionLabel(it.scale, ex.reference) })}
                    </li>
                  )
                })}
              </ul>
            </li>
          ))}
        </ul>
      </div>

      <div className="card overflow-x-auto">
        <h2 className="h2">{t('calib.perQuestion')}</h2>
        <table className="mt-2 w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th scope="col" className="py-1 pr-2">{t('calib.question')}</th>
              <th scope="col" className="py-1 pr-2">{t('calib.kappa')}</th>
              <th scope="col" className="py-1">{t('calib.matched')}</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(result.per_question).map(([q, v]) => (
              <tr key={q} className="border-b border-slate-100">
                <td className="py-1 pr-2">{questionText({ question_id: q } as ReferenceItem)}</td>
                <td className="py-1 pr-2">{v.kappa.toFixed(2)}</td>
                <td className="py-1">
                  {Math.round(v.agreement * v.n)} / {v.n}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button type="button" className="btn-secondary" onClick={onAgain}>
        {t('calib.again')}
      </button>
    </section>
  )
}
