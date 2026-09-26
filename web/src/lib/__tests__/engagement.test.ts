import { describe, expect, it } from 'vitest'
import snapshotFile from '../../../public/demo/snapshot.json'
import { campaigns, checkinQuality, leaderboard, MIN_QUALITY } from '../engagement'
import { computeCity, type RiskConfig } from '../local/risk'
import type { CheckIn, Finding, Observer, RiskScore, Site } from '../types'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const snap = snapshotFile as any
const cfg = snap.config as RiskConfig

function world(extra: { checkins: CheckIn[]; findings: Finding[]; observers: Observer[] }) {
  const data = {
    ...snap,
    checkins: [...snap.checkins, ...extra.checkins],
    findings: [...snap.findings, ...extra.findings],
    observers: [...snap.observers, ...extra.observers],
  }
  const scores = computeCity(data, 'CO', snap.as_of, cfg) as unknown as RiskScore[]
  return { ...data, scores }
}

let id = 100000
function checkin(observer: string, site: string, answers: Record<string, string>, withFindings = true): { c: CheckIn; f: Finding[] } {
  const c: CheckIn = {
    id: id++, client_uuid: `g-${id}`, site_id: site, observer_id: observer, observed_at: `${snap.as_of}T10:00:00Z`,
    lat: null, lon: null, consent: true, answers, created_at: '', synthetic: true,
  }
  const f: Finding[] = withFindings
    ? [
        { id: id++, checkin_id: c.id, type: 'larvae', subject: 'larval_dips', count: 2, status: 'manual', data: { dips: [2, 0, 0, 0, 0] } },
        { id: id++, checkin_id: c.id, type: 'predator', subject: 'amphibians', citizen_answer: 'heard', status: 'manual' },
      ]
    : []
  return { c, f }
}

const observer = (oid: string, team: string): Observer => ({ id: oid, tier: 'new', team, calibration: {}, synthetic: true })

describe('leaderboard rewards evidence quality, never volume', () => {
  it('fifty low-quality check-ins earn nothing', () => {
    const spam = Array.from({ length: 50 }, (_, i) => checkin('OBS-SPAMMY', `C${(i % 20) + 1}`, {}, false))
    const w = world({ checkins: spam.map((x) => x.c), findings: spam.flatMap((x) => x.f), observers: [observer('OBS-SPAMMY', 'Spam team')] })
    for (const x of spam) expect(checkinQuality(x.c, x.f, w.scores).quality).toBeLessThan(MIN_QUALITY)
    const me = leaderboard(w.observers, w.checkins, w.findings, w.scores).people.find((p) => p.observer === 'OBS-SPAMMY')!
    expect(me.points).toBe(0)
    expect(me.ignored).toBe(50)
  })

  it('repeating a good check-in at the same site and week earns no more than doing it once', () => {
    // Answer as the consensus at C1 does, so quality is high
    const consensus = { flow_NP: 'present', sub_OM: 'present', water_sewage_smell: 'absent', water_foam: 'absent', water_colour_unusual: 'absent', mac_free_floating: 'absent' }
    const once = checkin('OBS-CAREFU', 'C1', consensus)
    const w1 = world({ checkins: [once.c], findings: once.f, observers: [observer('OBS-CAREFU', 'Careful team')] })
    const p1 = leaderboard(w1.observers, w1.checkins, w1.findings, w1.scores).people.find((p) => p.observer === 'OBS-CAREFU')!
    expect(p1.points).toBeGreaterThan(0)

    const many = Array.from({ length: 20 }, () => checkin('OBS-CAREFU', 'C1', consensus))
    const w2 = world({ checkins: many.map((x) => x.c), findings: many.flatMap((x) => x.f), observers: [observer('OBS-CAREFU', 'Careful team')] })
    const p2 = leaderboard(w2.observers, w2.checkins, w2.findings, w2.scores).people.find((p) => p.observer === 'OBS-CAREFU')!
    expect(p2.points).toBeLessThanOrEqual(p1.points + 1) // consensus shifts slightly with more copies; never 20x
    expect(p2.counted).toBe(1)
  })

  it('a careful volunteer outranks a volume spammer', () => {
    const good = checkin('OBS-CAREFU', 'C12', { flow_NP: 'present', sub_OM: 'absent', water_sewage_smell: 'absent', water_foam: 'absent', water_colour_unusual: 'absent', mac_free_floating: 'absent' })
    const spam = Array.from({ length: 30 }, (_, i) => checkin('OBS-SPAMMY', `C${(i % 20) + 1}`, {}, false))
    const w = world({ checkins: [good.c, ...spam.map((x) => x.c)], findings: [...good.f, ...spam.flatMap((x) => x.f)], observers: [observer('OBS-CAREFU', 'A'), observer('OBS-SPAMMY', 'B')] })
    const board = leaderboard(w.observers, w.checkins, w.findings, w.scores)
    const rank = (o: string) => board.people.findIndex((p) => p.observer === o)
    expect(rank('OBS-CAREFU')).toBeLessThan(rank('OBS-SPAMMY'))
    expect(board.teams.find((t) => t.team === 'A')!.pointsPerMember).toBeGreaterThan(board.teams.find((t) => t.team === 'B')!.pointsPerMember)
  })
})

describe('campaigns target data gaps', () => {
  it('puts sites with no data first', () => {
    const latest = computeCity(snap, 'CO', snap.as_of, cfg) as unknown as RiskScore[]
    const list = campaigns(latest, snap.sites as Site[])
    expect(list[0].reason).toBe('no_data')
    expect(list[0].site.id).toBe('C12')
    expect(list.every((c) => ['no_data', 'stale', 'uncertain'].includes(c.reason))).toBe(true)
  })
})
