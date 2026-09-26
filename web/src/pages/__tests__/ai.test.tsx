import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { aiFields, compareKeyVision, KEYS, keyPath, runKey } from '../../lib/ai'
import { buildDraft, emptyState } from '../../lib/checkin'
import { axeViolations } from '../../test/axe'
import { FakeClient } from '../../test/fakeClient'
import { renderApp } from '../../test/render'

const ctx = { observerId: 'OBS-ABC234', now: new Date('2026-09-20T09:00:00Z'), uuid: 'u' }
const response = new FakeClient().nextAi

describe('AI decisions', () => {
  it('unanswered suggestions are never submitted', () => {
    const s = { ...emptyState(), siteId: 'C1', cupPhoto: new Blob(['x']), ai: { larval_dips: { type: 'larvae' as const, response } } }
    const dips = buildDraft(s, ctx).draft.findings.find((f) => f.subject === 'larval_dips')!
    expect(dips.ai_label).toBeUndefined()
    expect(dips.status).toBe('manual')
  })

  it('stores the AI suggestion and the citizen answer separately', () => {
    const change = aiFields({ type: 'larvae', response, decision: { kind: 'change', label: 'larvae_absent' } })
    expect(change).toMatchObject({ ai_label: 'larvae_present', citizen_answer: 'larvae_absent', status: 'corrected', ai_provider: 'mock' })
    expect(aiFields({ type: 'larvae', response, decision: { kind: 'accept' } })).toMatchObject({ citizen_answer: 'larvae_present', status: 'confirmed' })
    expect(aiFields({ type: 'larvae', response, decision: { kind: 'reject' } })).toMatchObject({ citizen_answer: null, status: 'rejected' })
  })

  it('implausible species go to expert review even when accepted', () => {
    const r = { ...response, suggestions: [{ ...response.suggestions[0], label: 'Pelophylax perezi', plausibility: { status: 'implausible' as const, gbif_occurrences: 0 } }] }
    expect(aiFields({ type: 'predator', response: r, decision: { kind: 'accept' } }).status).toBe('expert_review')
  })

  it('the TypeScript key runner matches the JSON keys', () => {
    expect(runKey(KEYS.larvae, { posture: 'flat' })).toBe('anopheles_type')
    expect(runKey(KEYS.adult_mosquito, { stripes: 'yes', thorax_line: 'unsure' })).toBe('striped_aedes_type')
    expect(runKey(KEYS.adult_mosquito, { stripes: 'no', colour: 'yes' })).toBe('plain_culex_type')
    expect(keyPath(KEYS.adult_mosquito, { stripes: 'no' })).toEqual(['stripes', 'colour'])
    expect(compareKeyVision('striped_aedes_type', 'plain_culex_type')).toBe('disagree')
  })
})

async function toLarvae(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: /Choose Exploratório/ }))
  await user.click(screen.getByRole('button', { name: 'Next' }))
  await user.click(screen.getByRole('button', { name: 'Next' }))
}

function photoFile() {
  return new File([new Uint8Array([255, 216, 255])], 'cup.jpg', { type: 'image/jpeg' })
}

describe('AI chip in the wizard', () => {
  it('shows the mock badge, the suggestion, the dropped label, and requires a decision', async () => {
    const user = userEvent.setup()
    const { container, client } = renderApp('/check')
    expect(await screen.findAllByText('Demo AI (mock)')).not.toHaveLength(0)
    await toLarvae(user)
    // jsdom has no canvas: bypass re-encoding by uploading through the input with a stubbed sanitiser
    const input = container.querySelector('input[type=file]') as HTMLInputElement
    await user.upload(input, photoFile())
    const chip = await screen.findByRole('group', { name: /AI suggestion, waiting/ })
    expect(within(chip).getByText(/82% sure/)).toBeInTheDocument()
    expect(within(chip).getByText(/Unanswered suggestions are not sent/)).toBeInTheDocument()
    expect(screen.getByText('“Culex pipiens larva”')).toBeInTheDocument()
    expect(client.aiCalls[0]).toMatchObject({ type: 'larvae', siteId: 'C1' })
    expect(await axeViolations(container)).toEqual([])
    await user.click(within(chip).getByRole('button', { name: 'Change' }))
    await user.selectOptions(within(chip).getByRole('combobox'), 'larvae_absent')
    expect(screen.getByText(/You changed it to: No larvae visible/)).toBeInTheDocument()
  })

  it('says AI unavailable when the provider fails', async () => {
    const user = userEvent.setup()
    const client = new FakeClient()
    client.aiAvailable = false
    const { container } = renderApp('/check', client)
    await toLarvae(user)
    await user.upload(container.querySelector('input[type=file]') as HTMLInputElement, photoFile())
    await waitFor(() => expect(screen.getByText(/AI unavailable, answer manually/)).toBeInTheDocument())
  })

  it('never calls the AI for dead birds', async () => {
    const user = userEvent.setup()
    const { container, client } = renderApp('/check')
    await toLarvae(user)
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await user.click(screen.getByRole('radio', { name: 'Yes' }))
    await user.upload(container.querySelector('input[type=file]') as HTMLInputElement, photoFile())
    await screen.findByText(/Location data removed/)
    expect(client.aiCalls).toHaveLength(0)
  })
})
