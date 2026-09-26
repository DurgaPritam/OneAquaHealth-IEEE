import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { AiAssist } from '../../components/AiAssist'
import { Explainer } from '../../components/Explainer'
import { Callout, PhotoInput, Segmented, Stepper } from '../../components/controls'
import { DipIllustration, PostureAngled, PostureFlat } from '../../illustrations'
import { keyPath, KEYS, type AiItem } from '../../lib/ai'
import { adultKeyResult, larvaKey, type WizardState } from '../../lib/checkin'

export type Patch = (p: Partial<WizardState> | ((prev: WizardState) => Partial<WizardState>)) => void

/** Functional update: an AI answer can arrive after other fields have changed. */
function useAiSetter(patch: Patch, _s: WizardState, subject: string) {
  return useCallback((item: AiItem | undefined) => patch((prev) => ({ ai: { ...prev.ai, [subject]: item } })), [patch, subject])
}

export function StepLarvae({ s, patch }: { s: WizardState; patch: Patch }) {
  const { t } = useTranslation()
  const setAi = useAiSetter(patch, s, 'larval_dips')
  const total = s.dips.reduce((a, b) => a + b, 0)
  const key = larvaKey(s.posture)
  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h1 id="step-heading" className="h1">
        {t('larvae.heading')}
      </h1>
      <p className="text-slate-700">{t('larvae.intro')}</p>
      <Callout tone="why" title={t('common.whyItMatters')}>
        {t('larvae.why')}
      </Callout>
      <Explainer module="larvae" />
      <div className="card space-y-3">
        <h2 className="h2">{t('larvae.howHeading')}</h2>
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
        <AiAssist type="larvae" photo={s.cupPhoto} siteId={s.siteId} item={s.ai.larval_dips} onChange={setAi} />
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
      <AdultMosquito s={s} patch={patch} />
    </section>
  )
}

function AdultMosquito({ s, patch }: { s: WizardState; patch: Patch }) {
  const { t } = useTranslation()
  const setAi = useAiSetter(patch, s, 'adult_mosquito')
  const result = adultKeyResult(s.adultKey)
  return (
    <div className="card">
      <h2 className="h2">{t('adult.heading')}</h2>
      <p className="muted mt-1">{t('adult.intro')}</p>
      <Segmented
        legend={t('adult.question')}
        options={[
          { value: 'no', label: t('adult.no') },
          { value: 'yes', label: t('adult.yes') },
        ]}
        value={s.adultSeen}
        onChange={(v) => patch({ adultSeen: v as WizardState['adultSeen'] })}
      />
      {s.adultSeen === 'yes' && (
        <>
          {keyPath(KEYS.adult_mosquito, s.adultKey).map((nodeId) => (
            <Segmented
              key={nodeId}
              legend={t(`adult.q_${nodeId}`)}
              options={Object.keys(KEYS.adult_mosquito.nodes[nodeId].options).map((v) => ({ value: v, label: t(`adult.key_${v}`) }))}
              value={s.adultKey[nodeId]}
              onChange={(v) => {
                const next = { ...s.adultKey }
                if (v === undefined) delete next[nodeId]
                else next[nodeId] = v
                const kept = Object.fromEntries(keyPath(KEYS.adult_mosquito, next).filter((k) => next[k]).map((k) => [k, next[k]]))
                patch({ adultKey: kept })
              }}
            />
          ))}
          {result && (
            <Callout tone="info">
              {t('adult.result', { result: t(`adult.result_${result}`) })}
              {result === 'striped_aedes_type' && <> {t('adult.tigerNote')}</>}
            </Callout>
          )}
          <PhotoInput label={t('adult.photo')} photo={s.adultPhoto} onChange={(b) => patch({ adultPhoto: b })} />
          <AiAssist type="adult_mosquito" photo={s.adultPhoto} siteId={s.siteId} keyResult={result} item={s.ai.adult_mosquito} onChange={setAi} />
        </>
      )}
    </div>
  )
}

export function StepPredators({ s, patch }: { s: WizardState; patch: Patch }) {
  const { t } = useTranslation()
  const setAi = useAiSetter(patch, s, 'predator_photo')
  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h1 id="step-heading" className="h1">
        {t('predators.heading')}
      </h1>
      <p className="text-slate-700">{t('predators.intro')}</p>
      <Callout tone="why" title={t('common.whyItMatters')}>
        {t('predators.why')}
      </Callout>
      <Explainer module="predators" />
      <Callout tone="info">{t('predators.protected')}</Callout>
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
        <AiAssist type="predator" photo={s.predatorPhoto} siteId={s.siteId} item={s.ai.predator_photo} onChange={setAi} />
      </div>
    </section>
  )
}

export function StepDeadBirds({ s, patch }: { s: WizardState; patch: Patch }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="step-heading" className="space-y-4">
      <h1 id="step-heading" className="h1">
        {t('deadBirds.heading')}
      </h1>
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
      <Explainer module="deadBirds" />
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
