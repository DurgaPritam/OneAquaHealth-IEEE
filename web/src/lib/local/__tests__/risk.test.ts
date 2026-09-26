import { describe, expect, it } from 'vitest'
import golden from '../../../../../data/fixtures/risk_golden.json'
import snapshotFile from '../../../../public/demo/snapshot.json'
import { computeCity, isoWeek, type RiskConfig } from '../risk'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const snapshot = snapshotFile as any

describe('TypeScript risk engine matches Python', () => {
  it('reproduces every golden site score, factor and flag', () => {
    const rows = computeCity(snapshot, 'CO', golden.as_of, snapshot.config as RiskConfig)
    const byId = Object.fromEntries(rows.map((r) => [r.site_id, r]))
    expect(rows).toHaveLength(golden.rows.length)
    for (const g of golden.rows) {
      const r = byId[g.site_id]
      expect(r.total, g.site_id).toBeCloseTo(g.total, 3)
      expect(r.range_low, g.site_id).toBeCloseTo(g.range_low, 3)
      expect(r.range_high, g.site_id).toBeCloseTo(g.range_high, 3)
      expect(r.coverage).toBeCloseTo(g.coverage, 3)
      expect(r.band).toBe(g.band)
      expect(r.alert).toBe(g.alert)
      expect(r.needs_data).toBe(g.needs_data)
      expect(r.dominant).toBe(g.dominant)
      expect(r.checkin_ids).toEqual(g.checkin_ids)
      for (const f of r.factors) {
        const gv = (g.factors as Record<string, number | null>)[f.name]
        if (gv === null) expect(f.value, `${g.site_id} ${f.name}`).toBeNull()
        else expect(f.value, `${g.site_id} ${f.name}`).toBeCloseTo(gv, 3)
      }
    }
  })

  it('iso weeks match Python', () => {
    expect(isoWeek('2026-09-20')).toBe('2026-W38')
    expect(isoWeek('2026-01-01')).toBe('2026-W01')
    expect(isoWeek('2027-01-03')).toBe('2026-W53')
  })
})
