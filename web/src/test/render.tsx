import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '../App'
import '../i18n'
import { AppProvider } from '../lib/context'
import { LocalDb } from '../lib/db'
import { FakeClient } from './fakeClient'

let n = 0

export function renderApp(path = '/', client = new FakeClient()) {
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
