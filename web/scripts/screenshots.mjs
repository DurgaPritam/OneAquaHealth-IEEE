// Regenerates docs/img/*.png from the static demo. Run: npm run build:static && npx vite preview --port 4175 & node scripts/screenshots.mjs
import { fileURLToPath } from 'node:url'
import { chromium, devices } from '@playwright/test'

const base = process.env.BASE ?? 'http://localhost:4175/#'
const out = fileURLToPath(new URL('../../docs/img/', import.meta.url))
const browser = await chromium.launch()

async function fresh(ctx) {
  const page = await ctx.newPage()
  await page.goto(base + '/')
  await page.evaluate(async () => {
    localStorage.clear()
    for (const n of ['aquasentinel-demo', 'aquasentinel']) await new Promise((r) => { const q = indexedDB.deleteDatabase(n); q.onsuccess = q.onerror = q.onblocked = r })
  })
  await page.reload()
  await page.waitForTimeout(800)
  return page
}

// Phone shots
const phone = await browser.newContext({ ...devices['Pixel 7'] })
let p = await fresh(phone)
await p.screenshot({ path: out + 'phone-home.png' })
await p.getByRole('link', { name: 'Stream check', exact: true }).click()
await p.getByRole('button', { name: /Choose Estação Cbr-B/ }).click()
await p.getByRole('button', { name: 'Next' }).click()
await p.getByRole('group', { name: /Still water/ }).scrollIntoViewIfNeeded()
await p.screenshot({ path: out + 'phone-stream-check.png' })
await p.getByRole('button', { name: 'Next' }).click()
await p.getByRole('spinbutton', { name: 'Dip 1: larvae counted' }).fill('14')
await p.locator('input[type=file]').first().setInputFiles(fileURLToPath(new URL('./sample-cup.jpg', import.meta.url)))
await p.getByRole('group', { name: /AI suggestion, waiting/ }).waitFor()
await p.getByRole('group', { name: /AI suggestion, waiting/ }).scrollIntoViewIfNeeded()
await p.screenshot({ path: out + 'phone-ai-chip.png' })
await p.getByRole('button', { name: 'Next' }).click()
await p.getByRole('button', { name: 'Next' }).click()
await p.getByRole('alert').scrollIntoViewIfNeeded()
await p.screenshot({ path: out + 'phone-dead-birds.png' })

// Practice results
p = await fresh(phone)
await p.getByRole('link', { name: 'Practice', exact: true }).click()
await p.getByRole('button', { name: 'Start practice' }).click()
for (let i = 0; i < 19; i++) {
  await p.getByRole('radio').nth(i < 5 ? 0 : 1).check({ force: true })
  await p.getByRole('button', { name: i === 18 ? 'See my results' : 'Next' }).click()
}
await p.getByRole('heading', { name: 'What to look for next time' }).scrollIntoViewIfNeeded()
await p.screenshot({ path: out + 'phone-practice-feedback.png' })

// Desktop city view
const desk = await browser.newContext({ viewport: { width: 1280, height: 860 } })
p = await fresh(desk)
await p.getByRole('link', { name: 'City view', exact: true }).click()
await p.waitForTimeout(2500)
await p.screenshot({ path: out + 'city-overview.png' })
await p.getByRole('button', { name: /Show details for Exploratório/ }).click()
await p.locator('section[aria-labelledby=panel-heading]').screenshot({ path: out + 'city-site-panel.png' })
await p.getByRole('button', { name: 'Check for new alerts' }).click()
await p.waitForTimeout(400)
const card = p.getByRole('listitem').filter({ hasText: '(C1)' }).first() // the alert draft is created before the vet notification
await card.getByRole('button', { name: 'Change measure' }).click()
await card.getByRole('combobox').selectOption('M4.6.7')
await p.waitForTimeout(400)
await p.locator('section[aria-labelledby=queue-heading]').screenshot({ path: out + 'city-alert-queue.png' })
await browser.close()
console.log('screenshots written to', out)
