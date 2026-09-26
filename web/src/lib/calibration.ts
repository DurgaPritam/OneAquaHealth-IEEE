// TypeScript port of api/reliability/calibration.py and kappa.py.
// data/fixtures/calibration_golden.json pins it to the Python results.
import itemsFile from '../../../data/reference_set/items.json'

export interface ReferenceItem {
  id: string
  question_id: string
  scale: 'ape' | 'cover5' | 'posture'
  image: string
  answer: string
  rationale: string
  labelled_by: string
  review_status: string
  synthetic: boolean
}

export interface FeedbackExample {
  item: string
  reference: string
  answered: string
  rationale: string
}

export interface Feedback {
  question: string
  direction: 'under' | 'over' | 'swap'
  key: string
  count: number
  examples: FeedbackExample[]
}

export interface CalibrationResult {
  per_question: Record<string, { kappa: number; agreement: number; n: number }>
  overall_kappa: number
  tier: 'new' | 'calibrated' | 'trusted'
  n: number
  feedback: Feedback[]
}

export const REFERENCE_ITEMS = (itemsFile as unknown as { items: ReferenceItem[] }).items

export const SCALE_OPTIONS: Record<ReferenceItem['scale'], string[]> = {
  ape: ['absent', 'present', 'extensive'],
  cover5: ['1', '2', '3', '4', '5'],
  posture: ['angled', 'flat'],
}

const round3 = (x: number) => Math.round(x * 1000) / 1000

export function cohenKappa(reference: string[], answers: string[]): number {
  if (reference.length !== answers.length || reference.length === 0) throw new Error('Need two equal, non-empty sequences')
  const n = reference.length
  const po = reference.filter((r, i) => r === answers[i]).length / n
  const count = (xs: string[]) => xs.reduce<Record<string, number>>((m, x) => ({ ...m, [x]: (m[x] ?? 0) + 1 }), {})
  const rc = count(reference)
  const ac = count(answers)
  const cats = new Set([...Object.keys(rc), ...Object.keys(ac)])
  let pe = 0
  for (const c of cats) pe += (rc[c] ?? 0) * (ac[c] ?? 0)
  pe /= n * n
  if (pe >= 1) return po === 1 ? 1 : 0
  return (po - pe) / (1 - pe)
}

export function tierFor(kappa: number | null): CalibrationResult['tier'] {
  if (kappa === null) return 'new'
  if (kappa >= 0.7) return 'trusted'
  if (kappa >= 0.4) return 'calibrated'
  return 'new'
}

export function direction(scale: string, reference: string, answered: string): Feedback['direction'] {
  const order = scale === 'ape' || scale === 'cover5' ? SCALE_OPTIONS[scale] : null
  if (order && order.includes(reference) && order.includes(answered)) return order.indexOf(answered) < order.indexOf(reference) ? 'under' : 'over'
  return 'swap'
}

export function scoreCalibration(answers: Record<string, string>, items: ReferenceItem[] = REFERENCE_ITEMS): CalibrationResult {
  const answered = items.filter((it) => it.id in answers)
  if (answered.length === 0) throw new Error('No reference items answered')
  const byQ = new Map<string, ReferenceItem[]>()
  for (const it of answered) byQ.set(it.question_id, [...(byQ.get(it.question_id) ?? []), it])

  const per_question: CalibrationResult['per_question'] = {}
  for (const [q, its] of byQ) {
    const ref = its.map((it) => it.answer)
    const ans = its.map((it) => answers[it.id])
    per_question[q] = {
      kappa: round3(cohenKappa(ref, ans)),
      agreement: round3(ref.filter((r, i) => r === ans[i]).length / its.length),
      n: its.length,
    }
  }
  const total = Object.values(per_question).reduce((s, v) => s + v.n, 0)
  const overall = round3(Object.values(per_question).reduce((s, v) => s + v.kappa * v.n, 0) / total)

  const groups = new Map<string, FeedbackExample[]>()
  const order: string[] = []
  for (const it of answered) {
    const given = answers[it.id]
    if (given === it.answer) continue
    const k = `${it.question_id}|${direction(it.scale, it.answer, given)}`
    if (!groups.has(k)) order.push(k)
    groups.set(k, [...(groups.get(k) ?? []), { item: it.id, reference: it.answer, answered: given, rationale: it.rationale }])
  }
  // Same as Python: first-seen order, then a stable sort by count descending
  const sortedKeys = [...order].sort((a, b) => groups.get(b)!.length - groups.get(a)!.length)
  const feedback = sortedKeys.map((k) => {
    const [question, dir] = k.split('|')
    return { question, direction: dir as Feedback['direction'], key: `calib.fb.${question}.${dir}`, count: groups.get(k)!.length, examples: groups.get(k)! }
  })
  return { per_question, overall_kappa: overall, tier: tierFor(overall), n: total, feedback }
}
