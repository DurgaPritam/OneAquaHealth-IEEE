import AxeBuilder from '@axe-core/playwright'
import { expect, type Page } from '@playwright/test'

/** Full axe run in a real browser, including colour contrast. The Leaflet map tiles are third-party and excluded. */
export async function expectNoAxeViolations(page: Page, label: string) {
  const result = await new AxeBuilder({ page }).exclude('.leaflet-container').analyze()
  const summary = result.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
  expect(summary, `axe on ${label}`).toEqual([])
}

export async function freshDemo(page: Page) {
  await page.goto('/')
  await page.evaluate(async () => {
    localStorage.clear()
    await new Promise((resolve) => {
      const req = indexedDB.deleteDatabase('aquasentinel-demo')
      req.onsuccess = req.onerror = req.onblocked = () => resolve(null)
    })
    await new Promise((resolve) => {
      const req = indexedDB.deleteDatabase('aquasentinel')
      req.onsuccess = req.onerror = req.onblocked = () => resolve(null)
    })
  })
  await page.reload()
}

export async function checkIn(page: Page, siteName: RegExp, opts: { strong?: boolean } = {}) {
  await page.getByRole('link', { name: 'Stream check', exact: true }).click()
  await page.getByRole('button', { name: siteName }).click()
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByRole('group', { name: /Still water/ }).getByText('Extensive', { exact: true }).click()
  if (opts.strong) await page.getByRole('group', { name: /Sewage smell/ }).getByText('Extensive', { exact: true }).click()
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByRole('spinbutton', { name: 'Dip 1: larvae counted' }).fill(opts.strong ? '60' : '5')
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByText('None', { exact: true }).first().click()
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByText('No', { exact: true }).click()
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Send check-in' }).click()
}
