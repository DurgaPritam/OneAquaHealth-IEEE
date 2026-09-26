// TypeScript port of api/reliability/dawid_skene.py (MAP Dawid-Skene EM).
// data/fixtures/risk_golden.json checks that scores built on it match Python.

export type Label = [item: string, observer: string, cls: string]

export interface DSOptions {
  classes: string[]
  priorAccuracy?: Record<string, number>
  priorStrength?: number
  defaultAccuracy?: number | null
  classPriorShare?: number
  smoothing?: number
  maxIter?: number
  tol?: number
}

export interface DSResult {
  classes: string[]
  items: string[]
  observers: string[]
  posterior: number[][]
  prior: number[]
  confusion: number[][][]
  reliability: Record<string, number>
}

export function dawidSkene(labels: Label[], opts: DSOptions): DSResult {
  if (labels.length === 0) throw new Error('No labels')
  const { classes, priorAccuracy = {}, priorStrength = 2, defaultAccuracy = 0.7, classPriorShare = 1 / 3, smoothing = 0.01, maxIter = 200, tol = 1e-6 } = opts
  const items = [...new Set(labels.map((l) => l[0]))]
  const observers = [...new Set(labels.map((l) => l[1]))]
  const K = classes.length
  const I = items.length
  const O = observers.length
  const ki = new Map(classes.map((c, n) => [c, n]))
  const ii = new Map(items.map((c, n) => [c, n]))
  const oi = new Map(observers.map((c, n) => [c, n]))

  const counts = Array.from({ length: I }, () => Array.from({ length: O }, () => new Array<number>(K).fill(0)))
  for (const [item, obs, lab] of labels) {
    const k = ki.get(lab)
    if (k === undefined) throw new Error(`Label ${lab} not in classes`)
    counts[ii.get(item)!][oi.get(obs)!][k] += 1
  }

  const pseudo = observers.map((obs) => {
    const acc0 = obs in priorAccuracy ? priorAccuracy[obs] : defaultAccuracy
    if (acc0 === null || acc0 === undefined) return Array.from({ length: K }, () => new Array<number>(K).fill(0))
    const acc = Math.min(0.999, Math.max(1 / K, acc0))
    const off = K > 1 ? (1 - acc) / (K - 1) : 0
    return Array.from({ length: K }, (_, a) => Array.from({ length: K }, (_, b) => priorStrength * (a === b ? acc : off)))
  })
  const classAlpha = classPriorShare * I

  let t = counts.map((row) => {
    const s = new Array<number>(K).fill(1e-9)
    for (const o of row) for (let k = 0; k < K; k += 1) s[k] += o[k]
    const z = s.reduce((a, b) => a + b, 0)
    return s.map((v) => v / z)
  })

  const mStep = (tt: number[][]) => {
    const alpha = smoothing + classAlpha
    const prior = new Array<number>(K).fill(0)
    for (const row of tt) for (let k = 0; k < K; k += 1) prior[k] += row[k]
    for (let k = 0; k < K; k += 1) prior[k] = (prior[k] + alpha) / (I + alpha * K)
    const conf = observers.map((_, o) => {
      const mtx = Array.from({ length: K }, (_, k) => Array.from({ length: K }, (_, l) => pseudo[o][k][l] + smoothing))
      for (let i = 0; i < I; i += 1) for (let k = 0; k < K; k += 1) for (let l = 0; l < K; l += 1) mtx[k][l] += tt[i][k] * counts[i][o][l]
      return mtx.map((row) => {
        const z = row.reduce((a, b) => a + b, 0)
        return row.map((v) => v / z)
      })
    })
    return { prior, conf }
  }

  const eStep = (prior: number[], conf: number[][][]) => {
    let ll = 0
    const post = counts.map((row) => {
      const lp = prior.map((p) => Math.log(p))
      for (let o = 0; o < O; o += 1) for (let l = 0; l < K; l += 1) {
        const c = row[o][l]
        if (c) for (let k = 0; k < K; k += 1) lp[k] += c * Math.log(conf[o][k][l])
      }
      const mx = Math.max(...lp)
      const e = lp.map((v) => Math.exp(v - mx))
      const z = e.reduce((a, b) => a + b, 0)
      ll += Math.log(z) + mx
      return e.map((v) => v / z)
    })
    return { post, ll }
  }

  let prev: number | null = null
  for (let it = 1; it <= maxIter; it += 1) {
    const { prior, conf } = mStep(t)
    const { post, ll } = eStep(prior, conf)
    t = post
    if (prev !== null && Math.abs(ll - prev) < tol * Math.max(1, Math.abs(prev))) break
    prev = ll
  }
  const { prior, conf } = mStep(t)
  const reliability = Object.fromEntries(observers.map((obs, o) => [obs, classes.reduce((s, _, k) => s + conf[o][k][k] * prior[k], 0)]))
  return { classes, items, observers, posterior: t, prior, confusion: conf, reliability }
}

export function argmax(xs: number[]): number {
  let best = 0
  for (let i = 1; i < xs.length; i += 1) if (xs[i] > xs[best]) best = i
  return best
}
