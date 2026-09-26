import { defineConfig, devices } from '@playwright/test'

// End-to-end tests run against the static demo build (the whole backend in the browser),
// which is exactly what judges open.
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  fullyParallel: false,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:4174/', trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run build:static && npx vite preview --port 4174 --strictPort',
    url: 'http://localhost:4174/',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
  projects: [
    { name: 'phone', use: { ...devices['Pixel 7'] } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
  ],
})
