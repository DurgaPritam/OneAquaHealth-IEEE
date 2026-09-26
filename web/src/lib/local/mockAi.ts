// TypeScript port of api/ai/mock.py and the validation gate, for the static demo.
import type { AiResponse, VisionType } from '../ai'
import { allowedLabels } from '../ai'

const INVENTED: Record<VisionType, string> = {
  larvae: 'Culex pipiens larva',
  adult_mosquito: 'Aedes albopictus (confirmed)',
  predator: 'Pelophylax kl. esculentus',
  habitat: 'West Nile hotspot',
}

async function digest(bytes: Uint8Array): Promise<Uint8Array> {
  if (globalThis.crypto?.subtle) return new Uint8Array(await crypto.subtle.digest('SHA-256', bytes as BufferSource))
  // Fallback: simple deterministic hash (tests without WebCrypto)
  const out = new Uint8Array(32)
  bytes.forEach((b, i) => (out[i % 32] = (out[i % 32] * 31 + b + i) & 255))
  return out
}

export async function mockSuggest(photo: Blob, type: VisionType): Promise<AiResponse> {
  const buf = new Uint8Array(await photo.arrayBuffer())
  const tag = new TextEncoder().encode(type)
  const joined = new Uint8Array(buf.length + tag.length)
  joined.set(buf)
  joined.set(tag, buf.length)
  const d = await digest(joined)
  const allowed = allowedLabels(type)
  const choices = allowed.filter((l) => l.id !== 'not_sure')
  const pick = choices[d[0] % choices.length]
  const raw = [{ label: pick.id, confidence: Math.round((0.5 + (d[1] / 255) * 0.45) * 100) / 100, reason: 'Demo AI (mock): placeholder suggestion, the photo was not analysed.' }]
  if (d[2] % 5 === 0) raw.push({ label: INVENTED[type], confidence: 0.9, reason: 'Demo AI (mock): invented label to show the validation gate.' })
  // validation gate: only labels in data/labels.json survive
  const ids = new Set(allowed.map((l) => l.id))
  const kept = raw.filter((s) => ids.has(s.label))
  const dropped = raw.filter((s) => !ids.has(s.label)).map((s) => ({ label: s.label, why: 'not in the allowed label list' }))
  return {
    available: true,
    provider: 'mock',
    model: 'mock-deterministic-1',
    mock: true,
    suggestions: kept.map((s) => ({ ...s, text: allowed.find((l) => l.id === s.label)!.text, plausibility: type === 'predator' ? { status: 'unchecked' } : undefined })),
    dropped,
  }
}
