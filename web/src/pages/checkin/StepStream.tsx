import { useTranslation } from 'react-i18next'
import { Segmented, Stepper } from '../../components/controls'
import { answerKeys, answeredCount, marginKey, questions, type Question, type Section } from '../../lib/checkin'
import type { AnswerValue } from '../../lib/types'

const COVER = ['1', '2', '3', '4', '5']

export function StepStream({
  answers,
  skipped,
  onAnswer,
  onToggleSkip,
}: {
  answers: Record<string, AnswerValue>
  skipped: string[]
  onAnswer: (key: string, value: AnswerValue | undefined) => void
  onToggleSkip: (sectionId: string) => void
}) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h2 id="step-heading" className="h1">
        {t('stream.heading')}
      </h2>
      <p className="text-slate-700">{t('stream.intro')}</p>
      <p className="muted">
        {t('stream.source')}{' '}
        <a className="underline" href={questions.source} target="_blank" rel="noreferrer">
          {questions.source.replace('https://', '')}
        </a>
      </p>
      <p className="muted">{t('stream.scaleHelp')}</p>
      {questions.sections.map((section) => (
        <SectionCard
          key={section.id}
          section={section}
          answers={answers}
          skipped={skipped.includes(section.id)}
          onAnswer={onAnswer}
          onToggleSkip={() => onToggleSkip(section.id)}
        />
      ))}
    </section>
  )
}

function SectionCard({
  section,
  answers,
  skipped,
  onAnswer,
  onToggleSkip,
}: {
  section: Section
  answers: Record<string, AnswerValue>
  skipped: boolean
  onAnswer: (key: string, value: AnswerValue | undefined) => void
  onToggleSkip: () => void
}) {
  const { t } = useTranslation()
  const headingId = `sec-${section.id}`
  const total = answerKeys(section).length
  return (
    <div className="card" role="group" aria-labelledby={headingId}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 id={headingId} className="h2">
            {t(`sections.${section.id}`)}
          </h3>
          <p className="muted">
            {skipped ? t('common.skipped') : t('common.answered', { count: answeredCount(section, answers), total })}
            {section.aquasentinel_addition && ` · ${t('common.oahAddition')}`}
          </p>
        </div>
        <button type="button" className="btn-ghost text-sm" aria-pressed={skipped} onClick={onToggleSkip}>
          {t('common.skipSection')}
        </button>
      </div>
      {!skipped && (
        <div className="mt-2 divide-y divide-slate-100">
          {section.per_margin
            ? section.per_margin.map((margin) => (
                <div key={margin} className="py-2">
                  <p className="font-semibold text-brand-900">{t(`stream.margin_${margin}`)}</p>
                  {section.questions.map((q) => (
                    <QuestionInput key={q.id} q={q} answerKey={marginKey(q.id, margin)} answers={answers} onAnswer={onAnswer} />
                  ))}
                </div>
              ))
            : section.questions.map((q) => <QuestionInput key={q.id} q={q} answerKey={q.id} answers={answers} onAnswer={onAnswer} />)}
        </div>
      )}
    </div>
  )
}

function QuestionInput({
  q,
  answerKey,
  answers,
  onAnswer,
}: {
  q: Question
  answerKey: string
  answers: Record<string, AnswerValue>
  onAnswer: (key: string, value: AnswerValue | undefined) => void
}) {
  const { t } = useTranslation()
  const label = t(`q.${q.id}`, { defaultValue: q.label })
  if (q.scale === 'count') {
    return <Stepper label={label} value={Number(answers[answerKey] ?? 0)} onChange={(v) => onAnswer(answerKey, v)} max={99} />
  }
  const options =
    q.scale === 'cover5'
      ? COVER.map((c) => ({ value: c, label: t(`scale.cover_${c}`) }))
      : ['absent', 'present', 'extensive'].map((v) => ({ value: v, label: t(`scale.${v}`) }))
  return (
    <Segmented
      legend={
        <>
          {label}
          {q.protocol_code && <span className="muted ml-1 font-normal">({q.protocol_code})</span>}
        </>
      }
      options={options}
      value={answers[answerKey] as string | undefined}
      onChange={(v) => onAnswer(answerKey, v)}
    />
  )
}
