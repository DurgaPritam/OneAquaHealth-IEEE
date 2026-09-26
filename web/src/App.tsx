import { HashRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import type { DataClient } from './lib/client'
import { AppProvider } from './lib/context'
import type { LocalDb } from './lib/db'
import { CheckInWizard } from './pages/checkin/CheckInWizard'
import { City } from './pages/City'
import { Home } from './pages/Home'
import { Me } from './pages/Me'
import { Practice } from './pages/Practice'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="check" element={<CheckInWizard />} />
        <Route path="practice" element={<Practice />} />
        <Route path="me" element={<Me />} />
        <Route path="city" element={<City />} />
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
