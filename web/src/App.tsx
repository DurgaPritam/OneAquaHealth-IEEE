import { useTranslation } from 'react-i18next'
import { HashRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import type { DataClient } from './lib/client'
import { AppProvider } from './lib/context'
import type { LocalDb } from './lib/db'
import { CheckInWizard } from './pages/checkin/CheckInWizard'
import { Home } from './pages/Home'
import { Practice } from './pages/Practice'
import { Placeholder } from './pages/Placeholder'

export function AppRoutes() {
  const { t } = useTranslation()
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="check" element={<CheckInWizard />} />
        <Route path="practice" element={<Practice />} />
        <Route path="me" element={<Placeholder title={t('nav.feed')} />} />
        <Route path="city" element={<Placeholder title={t('nav.city')} />} />
      </Route>
    </Routes>
  )
}

export default function App({ client, store }: { client: DataClient; store?: LocalDb }) {
  return (
    <AppProvider client={client} store={store}>
      <HashRouter>
        <AppRoutes />
      </HashRouter>
    </AppProvider>
  )
}
