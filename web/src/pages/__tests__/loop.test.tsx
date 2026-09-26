import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { axeViolations } from '../../test/axe'
import { localClient } from '../../test/localClient'
import { renderApp } from '../../test/render'

describe('the full One Health loop (static demo backend)', () => {
  it('check-in -> risk update -> drafted action -> officer approval -> volunteer message', { timeout: 30000 }, async () => {
    const user = userEvent.setup()
    const client = localClient()
    const before = structuredClone((await client.latestRisk('CO')).find((r) => r.site_id === 'C2')!)
    const { container } = renderApp('/check', client)

    // 1. Citizen check-in at C2 (index 0.53, just under the 0.55 threshold) with strong evidence
    await user.click(await screen.findByRole('button', { name: /Choose Estação Cbr-B/ }))
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await user.click(within(screen.getByRole('group', { name: /Still water/ })).getByRole('radio', { name: 'Extensive' }))
    await user.click(within(screen.getByRole('group', { name: /Sewage smell/ })).getByRole('radio', { name: 'Extensive' }))
    await user.click(screen.getByRole('button', { name: 'Next' }))
    const dip = screen.getByRole('spinbutton', { name: 'Dip 1: larvae counted' })
    await user.clear(dip)
    await user.type(dip, '60')
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await user.click(screen.getByRole('radio', { name: 'None' }))
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await user.click(screen.getByRole('radio', { name: 'Yes' }))
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Send check-in' }))
    expect(await screen.findByText('Your check-in has been sent.')).toBeInTheDocument()

    // 2. Risk updated with the new evidence
    const after = (await client.latestRisk('CO')).find((r) => r.site_id === 'C2')!
    expect(after.total).toBeGreaterThan(before.total)
    expect(after.alert).toBe(true)

    // 3. City view: the site is ranked and alerting; draft actions
    await user.click(screen.getByRole('link', { name: 'City view' }))
    expect(await screen.findByRole('button', { name: /Show details for Estação Cbr-B/ })).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
    await user.click(screen.getByRole('button', { name: /Show details for Estação Cbr-B/ }))
    expect(await screen.findByRole('heading', { name: /Why Estação Cbr-B scores/ })).toBeInTheDocument()
    expect(screen.getAllByText(/not a diagnosis/).length).toBeGreaterThan(0)
    expect(await axeViolations(container)).toEqual([])
    await user.click(screen.getByRole('button', { name: 'Check for new alerts' }))
    await screen.findByText(/new draft\(s\)/)

    // 4. Officer must be named; approves the C3 action
    const queue = screen.getByRole('region', { name: 'Alert queue' })
    const card = within(queue).getAllByRole('listitem').find((li) => li.textContent?.includes('(C2)') && !li.textContent.includes('veterinary'))!
    await user.click(within(card).getByRole('button', { name: 'Approve' }))
    expect(within(card).getByText('Enter your officer name or code first.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Officer name or code'), 'officer:CO-01')
    await user.click(within(card).getByRole('button', { name: 'Approve' }))
    expect(await screen.findByText(/Approved by officer:CO-01\. \d+ volunteer message\(s\) sent\./)).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])

    // 5. The volunteer sees that their observation led to an action
    await user.click(screen.getByRole('link', { name: 'My impact' }))
    await waitFor(() => expect(screen.getByText(/led to an action/)).toBeInTheDocument())
    expect(screen.getByText('Led to an action')).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
  })

  it('never sends anything without approval and routes dead birds to the vet team', async () => {
    const client = localClient()
    const drafts = await client.draftActions('CO')
    expect(drafts.length).toBeGreaterThan(0)
    expect(drafts.every((a) => a.status === 'drafted')).toBe(true)
    expect((await client.listMessages('OBS-SYN000')).length).toBe(0)
    expect(drafts.some((a) => a.measure_id === 'veterinary_notification')).toBe(true)
    const edited = await client.editAction(drafts[0].id, { measure_id: 'M4.6.7' })
    expect(edited.warnings[0]).toMatch(/mosquito/)
  })
})
