import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '../App'
import '../i18n'
import { AppProvider } from '../lib/context'
import { LocalDb } from '../lib/db'
import type { DataClient } from '../lib/client'
import { FakeClient } from './fakeClient'

let n = 0

export function renderApp<C extends DataClient = FakeClient>(path = '/', client: C = new FakeClient() as unknown as C) {
  const store = new LocalDb(`test-${n++}`)
  const utils = render(
    <AppProvider client={client} store={store}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </AppProvider>,
  )
  return { ...utils, client, store }
}
