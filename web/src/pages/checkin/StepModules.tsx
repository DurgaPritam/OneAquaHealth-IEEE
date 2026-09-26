import { useTranslation } from 'react-i18next'
import { Callout, PhotoInput, Segmented, Stepper } from '../../components/controls'
import { DipIllustration, PostureAngled, PostureFlat } from '../../illustrations'
import { larvaKey, type WizardState } from '../../lib/checkin'

type Patch = (p: Partial<WizardState>) => void

export function StepLarvae({ s, patch, aiSlot }: { s: WizardState; patch: Patch; aiSlot?: React.ReactNode }) {
  const { t } = useTranslation()
  const total = s.dips.reduce((a, b) => a + b, 0)
  const key = larvaKey(s.posture)
  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h2 id="step-heading" className="h1">
        {t('larvae.heading')}
      </h2>
      <p className="text-slate-700">{t('larvae.intro')}</p>
      <Callout tone="why" title={t('common.whyItMatters')}>
        {t('larvae.why')}
      </Callout>
      <div className="card space-y-3">
        <h3 className="h2">{t('larvae.howHeading')}</h3>
        <DipIllustration title={t('larvae.how2')} />
        <ol className="list-decimal space-y-1 pl-5">
          {[1, 2, 3, 4].map((i) => (
            <li key={i}>{t(`larvae.how${i}`)}</li>
          ))}
        </ol>
        <p className="muted">{t('larvae.safety')}</p>
      </div>
      <div className="card">
        <div className="grid gap-x-6 sm:grid-cols-2">
          {s.dips.map((n, i) => (
            <Stepper
              key={i}
              label={t('larvae.dip', { n: i + 1 })}
              value={n}
              max={500}
              onChange={(v) => patch({ dips: s.dips.map((d, j) => (j === i ? v : d)) })}
            />
          ))}
        </div>
        <p className="mt-2 font-semibold" aria-live="polite">
          {total > 0 ? t('larvae.total', { count: total }) : t('larvae.noLarvae')}
        </p>
        <PhotoInput label={t('larvae.cupPhoto')} photo={s.cupPhoto} onChange={(b) => patch({ cupPhoto: b })} />
        {aiSlot}
      </div>
      {total > 0 && (
        <div className="card space-y-2">
          <div className="flex flex-wrap gap-4">
            <figure className="text-center text-sm">
              <PostureAngled title={t('larvae.posture_angled')} />
              <figcaption>{t('larvae.posture_angled')}</figcaption>
            </figure>
            <figure className="text-center text-sm">
              <PostureFlat title={t('larvae.posture_flat')} />
              <figcaption>{t('larvae.posture_flat')}</figcaption>
            </figure>
          </div>
          <Segmented
            legend={t('larvae.postureQuestion')}
            hint={t('larvae.postureHelp')}
            options={(['angled', 'flat', 'unsure'] as const).map((v) => ({ value: v, label: t(`larvae.posture_${v}`) }))}
            value={s.posture}
            onChange={(v) => patch({ posture: v as WizardState['posture'] })}
          />
          {key && (
            <Callout tone="info">
              {key === 'anopheles_type' ? t('larvae.keyAnopheles') : t('larvae.keyCulex')} {t('larvae.keyNote')}
            </Callout>
          )}
        </div>
      )}
    </section>
  )
}

export function StepPredators({ s, patch, aiSlot }: { s: WizardState; patch: Patch; aiSlot?: React.ReactNode }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h2 id="step-heading" className="h1">
        {t('predators.heading')}
      </h2>
      <p className="text-slate-700">{t('predators.intro')}</p>
      <Callout tone="why" title={t('common.whyItMatters')}>
        {t('predators.why')}
      </Callout>
      <div className="card">
        <Segmented
          legend={t('predators.amphibians')}
          options={(['none', 'heard', 'seen'] as const).map((v) => ({ value: v, label: t(`predators.amph_${v}`) }))}
          value={s.amphibians}
          onChange={(v) => patch({ amphibians: v as WizardState['amphibians'] })}
        />
        <Stepper label={t('predators.birds')} value={s.birds} onChange={(v) => patch({ birds: v })} max={200} />
        <Segmented
          legend={t('predators.bats')}
          options={(['none', 'seen'] as const).map((v) => ({ value: v, label: t(`predators.bats_${v}`) }))}
          value={s.bats}
          onChange={(v) => patch({ bats: v as WizardState['bats'] })}
        />
        <PhotoInput label={t('predators.photo')} photo={s.predatorPhoto} onChange={(b) => patch({ predatorPhoto: b })} />
        {aiSlot}
      </div>
    </section>
  )
}

export function StepDeadBirds({ s, patch }: { s: WizardState; patch: Patch }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h2 id="step-heading" className="h1">
        {t('deadBirds.heading')}
      </h2>
      <Callout tone="danger" title={t('deadBirds.warningTitle')}>
        <ul className="list-disc space-y-1 pl-5 text-base">
          <li>{t('deadBirds.warning1')}</li>
          <li>{t('deadBirds.warning2')}</li>
          <li>{t('deadBirds.warning3')}</li>
        </ul>
      </Callout>
      <Callout tone="why" title={t('common.whyItMatters')}>
        {t('deadBirds.why')}
      </Callout>
      <div className="card">
        <Segmented
          legend={t('deadBirds.question')}
          options={[
            { value: 'no', label: t('deadBirds.no') },
            { value: 'yes', label: t('deadBirds.yes') },
          ]}
          value={s.deadBirdsSeen}
          onChange={(v) => patch({ deadBirdsSeen: v as WizardState['deadBirdsSeen'], deadBirds: v === 'yes' ? Math.max(1, s.deadBirds) : 0 })}
        />
        {s.deadBirdsSeen === 'yes' && (
          <>
            <Stepper label={t('deadBirds.count')} value={s.deadBirds} min={1} max={500} onChange={(v) => patch({ deadBirds: v })} />
            <PhotoInput label={t('deadBirds.photo')} photo={s.deadBirdPhoto} onChange={(b) => patch({ deadBirdPhoto: b })} />
            <p className="muted">{t('deadBirds.routing')}</p>
          </>
        )}
      </div>
    </section>
  )
}
