import { useTranslation } from 'react-i18next'

const LINKS: Record<string, string> = {
  stream: 'https://doi.org/10.5281/zenodo.21476580',
  larvae: 'https://doi.org/10.5281/zenodo.20345207',
  predators: 'https://doi.org/10.5281/zenodo.20345207',
  deadBirds: 'https://doi.org/10.5281/zenodo.20344421',
}

/** Short One Health explainer per module, grounded in an OAH document with a page reference. */
export function Explainer({ module }: { module: keyof typeof LINKS }) {
  const { t } = useTranslation()
  return (
    <details className="rounded-lg border border-brand-100 bg-white p-3 text-sm">
      <summary className="cursor-pointer font-semibold text-brand-700">{t('explain.summary')}</summary>
      <p className="mt-2 leading-relaxed">{t(`explain.${module}`)}</p>
      <p className="muted mt-1">
        {t('explain.source')}:{' '}
        <a className="underline" href={LINKS[module]} target="_blank" rel="noreferrer">
          {t(`explain.${module}_src`)}
        </a>
      </p>
    </details>
  )
}
