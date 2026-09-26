import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App'
import { HttpClient, type DataClient } from './lib/client'
import { LocalClient } from './lib/local/LocalClient'

// VITE_STATIC=1 builds the no-server demo: the whole backend runs in the browser.
const client: DataClient = import.meta.env.VITE_STATIC === '1' ? new LocalClient() : new HttpClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App client={client} />
  </StrictMode>,
)
