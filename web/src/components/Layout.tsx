import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router-dom'
import { changeLanguage, LANGUAGES, type LanguageCode } from '../i18n'
import { useApp } from '../lib/context'
import { LocalClient } from '../lib/local/LocalClient'

const NAV = [
  { to: '/', key: 'nav.home', end: true },
  { to: '/check', key: 'nav.checkin', end: false },
  { to: '/practice', key: 'nav.calibrate', end: false },
  { to: '/me', key: 'nav.feed', end: false },
  { to: '/city', key: 'nav.city', end: false },
]

export function Layout() {
  const { t, i18n } = useTranslation()
  const current = LANGUAGES.find((l) => l.code === i18n.language) ?? LANGUAGES[0]
  const { client } = useApp()
  const [mockAi, setMockAi] = useState(false)
  useEffect(() => {
    client.aiStatus().then((s) => setMockAi(s.mock), () => setMockAi(false))
  }, [client])
  return (
    <div className="flex min-h-full flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[2000] focus:rounded focus:bg-white focus:p-3">
        {t('app.skip')}
      </a>
      <header className="bg-brand-900 text-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-semibold">
            <Logo />
            {t('app.title')}
          </NavLink>
          <div className="ml-auto flex items-center gap-2">
            {mockAi && <span className="rounded-full border border-violet-300 bg-violet-100 px-2 py-1 text-xs font-semibold text-violet-950">{t('app.demoAi')}</span>}
            <label htmlFor="lang" className="sr-only">
              {t('lang.label')}
            </label>
            <select
              id="lang"
              value={current.code}
              onChange={(e) => void changeLanguage(e.target.value as LanguageCode)}
              className="min-h-11 rounded-md border border-white/40 bg-brand-900 px-2 text-white"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <nav aria-label={t('nav.label')} className="mx-auto max-w-5xl px-2">
          <ul className="flex flex-wrap gap-x-1">
            {NAV.map((n) => (
              <li key={n.to}>
                <NavLink
                  to={n.to}
                  end={n.end}
                  className={({ isActive }) =>
                    `inline-flex min-h-11 items-center whitespace-nowrap rounded-t-md px-3 text-sm font-medium ${
                      isActive ? 'bg-slate-50 text-brand-900' : 'text-white hover:bg-white/10'
                    }`
                  }
                >
                  {t(n.key)}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      {current.machine && (
        <p role="note" className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-950">
          {t('lang.machineTranslated')}
        </p>
      )}
      <DemoBanner />
      <StatusBar />
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

function DemoBanner() {
  const { t } = useTranslation()
  const { client } = useApp()
  const [date, setDate] = useState<string | null>(null)
  useEffect(() => {
    if (client instanceof LocalClient) void client.demoDate().then(setDate)
  }, [client])
  if (!(client instanceof LocalClient) || !date) return null
  return (
    <div className="border-b border-violet-200 bg-violet-50">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-2 text-sm text-violet-950">
        <span className="font-semibold">{t('demo.banner')}</span>
        <span>{t('demo.clock', { date })}</span>
        <button type="button" className="btn-ghost ml-auto text-sm text-violet-950" onClick={() => void client.reset().then(() => window.location.reload())}>
          {t('demo.reset')}
        </button>
      </div>
    </div>
  )
}

function StatusBar() {
  const { t } = useTranslation()
  const { online, pending, syncing, sync, lastSync } = useApp()
  if (online && pending === 0 && !lastSync?.failed) return null
  return (
    <div role="status" className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-2 text-sm">
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${online ? 'bg-emerald-600' : 'bg-slate-500'}`} aria-hidden />
        <span>{online ? t('app.online') : t('app.offline')}</span>
        {pending > 0 && <span className="font-medium">{t('app.pending', { count: pending })}</span>}
        {pending > 0 && online && (
          <button type="button" onClick={() => void sync()} disabled={syncing} className="btn-secondary ml-auto">
            {syncing ? t('app.syncing') : t('app.syncNow')}
          </button>
        )}
      </div>
    </div>
  )
}

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 3c5 7 9 11.5 9 16a9 9 0 0 1-18 0c0-4.5 4-9 9-16z" fill="#5eead4" />
      <path d="M10 21c2.5 2 9.5 2 12 0" stroke="#053a30" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  )
}
