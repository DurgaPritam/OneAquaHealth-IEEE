import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

export function Home() {
  const { t } = useTranslation()
  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-br from-brand-900 to-brand-700 p-6 text-white sm:p-10">
        <h1 className="text-3xl font-bold sm:text-4xl">{t('home.heading')}</h1>
        <p className="mt-3 max-w-2xl text-lg text-brand-50">{t('home.intro')}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/check" className="btn-primary bg-white text-brand-900 hover:bg-brand-50">
            {t('home.start')}
          </Link>
          <Link to="/practice" className="btn-secondary border-white bg-transparent text-white hover:bg-white/10">
            {t('home.practice')}
          </Link>
        </div>
      </section>
      <section aria-labelledby="promises" className="card">
        <h2 id="promises" className="h2">
          {t('home.promisesHeading')}
        </h2>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <li key={i} className="flex gap-3">
              <span aria-hidden="true" className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-900">
                ✓
              </span>
              <span>{t(`home.promise${i}`)}</span>
            </li>
          ))}
        </ul>
        <p className="muted mt-4">
          {t('home.sourceNote')}{' '}
          <a className="underline" href="https://doi.org/10.5281/zenodo.21476580" target="_blank" rel="noreferrer">
            doi.org/10.5281/zenodo.21476580
          </a>
        </p>
      </section>
    </div>
  )
}
