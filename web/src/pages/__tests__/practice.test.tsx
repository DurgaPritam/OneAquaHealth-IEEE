import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import golden from '../../../../data/fixtures/calibration_golden.json'
import { cohenKappa, REFERENCE_ITEMS, scoreCalibration } from '../../lib/calibration'
import { axeViolations } from '../../test/axe'
import { renderApp } from '../../test/render'

describe('calibration scoring (TypeScript port)', () => {
  it('reproduces every Python golden result exactly', () => {
    for (const c of golden as { answers: Record<string, string>; result: unknown }[]) {
      expect(scoreCalibration(c.answers)).toEqual(c.result)
    }
  })
  it('kappa edge cases match Python', () => {
    expect(cohenKappa(['a', 'a'], ['a', 'a'])).toBe(1)
    expect(cohenKappa(['a', 'a'], ['b', 'b'])).toBe(0)
  })
  it('no reference item was labelled by AI', () => {
    expect(REFERENCE_ITEMS.length).toBeGreaterThanOrEqual(15)
    for (const it of REFERENCE_ITEMS) expect(it.labelled_by.toLowerCase()).not.toContain('ai')
  })
})

describe('practice round', () => {
  it('runs a full round, explains the bank bias, sets the tier and has no axe violations', async () => {
    const user = userEvent.setup()
    const { container, client } = renderApp('/practice')
    expect(await axeViolations(container)).toEqual([])
    await user.click(screen.getByRole('button', { name: 'Start practice' }))
    for (const item of REFERENCE_ITEMS) {
      const wrongBank = item.id === 'rs01' || item.id === 'rs02'
      const optionName = {
        absent: 'Absent', present: 'Present', extensive: 'Extensive', angled: 'Hanging at an angle', flat: 'Lying flat',
        '1': '0 to 20%', '2': '21 to 40%', '3': '41 to 60%', '4': '61 to 80%', '5': '81 to 100%',
      }[wrongBank ? 'absent' : item.answer]!
      await user.click(screen.getByRole('radio', { name: optionName }))
      if (item.id === 'rs01') expect(await axeViolations(container)).toEqual([])
      await user.click(screen.getByRole('button', { name: item === REFERENCE_ITEMS.at(-1) ? 'See my results' : 'Next' }))
    }
    expect(await screen.findByText(/You tend to rate banks as natural when hard revetment is visible/)).toBeInTheDocument()
    expect(screen.getByText(/Your observer tier: Trusted/)).toBeInTheDocument()
    expect(await screen.findByText('Your tier has been saved.')).toBeInTheDocument()
    expect(Object.keys(client.calibrations)).toHaveLength(1)
    expect(await axeViolations(container)).toEqual([])
  })
})
