import { expect, test } from '@playwright/test'
import { checkIn, expectNoAxeViolations, freshDemo } from './helpers'

test('home and every check-in step pass axe, including colour contrast', async ({ page }) => {
  await freshDemo(page)
  await expectNoAxeViolations(page, 'home')
  await page.getByRole('link', { name: 'Stream check', exact: true }).click()
  await page.getByRole('button', { name: /Choose Estação Cbr-B/ }).click()
  await expectNoAxeViolations(page, 'site step')
  const steps = ['stream', 'larvae', 'predators', 'dead birds', 'review']
  for (const step of steps) {
    await page.getByRole('button', { name: 'Next' }).click()
    await expectNoAxeViolations(page, `${step} step`)
  }
})

test('the whole loop: check-in, risk update, drafted action, officer approval, volunteer message', async ({ page }) => {
  const started = Date.now()
  await freshDemo(page)
  await checkIn(page, /Choose Estação Cbr-B/, { strong: true })
  await expect(page.getByText('Your check-in has been sent.')).toBeVisible()

  await page.getByRole('link', { name: 'City view', exact: true }).click()
  const row = page.getByRole('row', { name: /Estação Cbr-B/ })
  await expect(row.getByText('Alert')).toBeVisible()
  await page.getByRole('button', { name: /Show details for Estação Cbr-B/ }).click()
  await expect(page.getByRole('heading', { name: /Why Estação Cbr-B scores/ })).toBeVisible()
  await expectNoAxeViolations(page, 'city view')

  await page.getByRole('button', { name: 'Check for new alerts' }).click()
  await page.getByLabel('Officer name or code').fill('officer:CO-01')
  const card = page.getByRole('listitem').filter({ hasText: '(C2)' }).first() // the alert draft is created before the vet notification
  await card.getByRole('button', { name: 'Approve' }).click()
  await expect(page.getByText(/Approved by officer:CO-01/)).toBeVisible()

  await page.getByRole('link', { name: 'My impact', exact: true }).click()
  await expect(page.getByText(/led to an action/).first()).toBeVisible()
  await expectNoAxeViolations(page, 'my impact')
  const seconds = (Date.now() - started) / 1000
  test.info().annotations.push({ type: 'loop-seconds', description: seconds.toFixed(1) })
  expect(seconds).toBeLessThan(300)
})

test('calibration round gives a tier and bias feedback', async ({ page }) => {
  await freshDemo(page)
  await page.getByRole('link', { name: 'Practice', exact: true }).click()
  await page.getByRole('button', { name: 'Start practice' }).click()
  await expectNoAxeViolations(page, 'practice item')
  for (let i = 0; i < 19; i += 1) {
    await page.getByRole('radio').first().check({ force: true })
    const last = i === 18
    await page.getByRole('button', { name: last ? 'See my results' : 'Next' }).click()
  }
  await expect(page.getByText(/Your observer tier:/)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'What to look for next time' })).toBeVisible()
  await expectNoAxeViolations(page, 'practice results')
})

test('offline: a check-in is queued on the device and sent when back online', async ({ page, context }) => {
  await freshDemo(page)
  await page.getByRole('link', { name: 'Stream check', exact: true }).click()
  await expect(page.getByRole('button', { name: /Choose Exploratório/ })).toBeVisible()
  await context.setOffline(true)
  await page.getByRole('link', { name: 'Home', exact: true }).click()
  await checkIn(page, /Choose Exploratório/)
  await expect(page.getByText('Your check-in is saved on this device and will be sent when you are online.')).toBeVisible()
  await expect(page.getByText('1 check-in waiting to send')).toBeVisible()
  await context.setOffline(false)
  await expect(page.getByText('1 check-in waiting to send')).toBeHidden({ timeout: 15000 })
  await page.getByRole('link', { name: 'My impact', exact: true }).click()
  await expect(page.getByText(/C1 ·/)).toBeVisible()
})
