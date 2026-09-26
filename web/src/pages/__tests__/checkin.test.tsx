import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { axeViolations } from '../../test/axe'
import { renderApp } from '../../test/render'

async function next(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Next' }))
}

function goOffline() {
  Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => false })
  window.dispatchEvent(new Event('offline'))
}

function goOnline() {
  Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => true })
  window.dispatchEvent(new Event('online'))
}

describe('citizen check-in', () => {
  it('completes a full check-in offline, then syncs it once when back online, with 0 axe violations on every screen', async () => {
    const user = userEvent.setup()
    const { container, client, store } = renderApp('/check')

    // Step 1: site (loaded while online), then the connection drops
    await screen.findByRole('button', { name: /Choose Exploratório/ })
    expect(await axeViolations(container)).toEqual([])
    await user.click(screen.getByRole('button', { name: /Choose Exploratório/ }))
    expect(screen.getByText(/Selected: Exploratório/)).toBeInTheDocument()
    act(() => goOffline())
    client.offline = true
    await next(user)

    // Step 2: stream check
    expect(screen.getByRole('heading', { name: 'Stream check' })).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
    const still = screen.getByRole('group', { name: /Still water/ })
    await user.click(within(still).getByRole('radio', { name: 'Extensive' }))
    await user.click(screen.getAllByRole('button', { name: 'Skip this section' })[1])
    await next(user)

    // Step 3: larvae
    expect(screen.getByRole('heading', { name: 'Larval dip' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Increase Dip 1: larvae counted' }))
    await user.click(screen.getByRole('button', { name: 'Increase Dip 1: larvae counted' }))
    await user.click(screen.getByRole('radio', { name: 'Hanging at an angle, head down' }))
    expect(screen.getByText(/Culex-type or Aedes-type/)).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
    await next(user)

    // Step 4: predators
    await user.click(screen.getByRole('radio', { name: 'Heard' }))
    expect(await axeViolations(container)).toEqual([])
    await next(user)

    // Step 5: dead birds, with the do-not-touch warning
    expect(screen.getByRole('alert')).toHaveTextContent('Do not touch dead birds')
    await user.click(screen.getByRole('radio', { name: 'Yes' }))
    expect(await axeViolations(container)).toEqual([])
    await next(user)

    // Step 6: review requires consent
    await user.click(screen.getByRole('button', { name: 'Send check-in' }))
    expect(screen.getByText('Please tick the box to send.')).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Send check-in' }))

    expect(await screen.findByText(/Your check-in is saved on this device/)).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
    expect(await store.outbox.count()).toBe(1)
    expect(client.checkins.size).toBe(0)

    // Back online: the queue sends automatically
    client.offline = false
    await act(async () => goOnline())
    await waitFor(async () => expect(await store.outbox.count()).toBe(0))
    expect(client.checkins.size).toBe(1)
    const sent = [...client.checkins.values()][0]
    expect(sent.checkin.answers).toEqual({ flow_NP: 'extensive' })
    expect(sent.findings.find((f) => f.subject === 'larval_dips')?.count).toBe(2)
    expect(sent.findings.find((f) => f.subject === 'dead_bird')?.count).toBe(1)
    expect(sent.checkin.consent).toBe(true)
  })

  it('home page has no axe violations and states the promises', async () => {
    const { container } = renderApp('/')
    expect(screen.getByText('AI only suggests. You decide every answer.')).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
  })
})

import { within } from '@testing-library/react'
