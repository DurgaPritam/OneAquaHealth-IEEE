import '@testing-library/jest-dom/vitest'
import 'fake-indexeddb/auto'
import { vi } from 'vitest'

// Leaflet needs a real layout engine; the map is decorative (every map has a list alternative).
vi.mock('../components/SiteMap', () => ({
  default: ({ label }: { label: string }) => <div role="img" aria-label={label} />,
}))

if (!('randomUUID' in crypto)) {
  Object.defineProperty(crypto, 'randomUUID', { value: () => '00000000-0000-4000-8000-000000000000' })
}
window.scrollTo = () => {}

// jsdom has no canvas: photo re-encoding is tested in the browser suite. Here it passes the blob through.
vi.mock('../lib/photo', async (orig) => ({ ...(await orig<typeof import('../lib/photo')>()), sanitisePhoto: async (b: Blob) => b }))
