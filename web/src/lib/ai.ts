import labelsFile from '../../../data/labels.json'
import adultKey from '../../../data/keys/adult_mosquito.json'
import larvaeKey from '../../../data/keys/larvae.json'
import type { FindingIn, FindingStatus, FindingType } from './types'

export type VisionType = 'larvae' | 'adult_mosquito' | 'predator' | 'habitat'

export interface Plausibility {
  status: 'plausible' | 'implausible' | 'unchecked' | 'not_applicable'
  species?: string
  gbif_occurrences?: number
}

export interface AiSuggestion {
  label: string
  confidence: number
  reason: string
  text: string
  plausibility?: Plausibility
}

export interface AiResponse {
  available: boolean
  error?: string
  provider?: string
  model?: string
  mock?: boolean
  suggestions: AiSuggestion[]
  dropped: { label: string; why: string }[]
  key_vs_vision?: 'agree' | 'disagree' | 'incomplete' | null
}

export interface AiStatus {
  provider: string
  model: string | null
  mock: boolean
  available: boolean
}

/** What the citizen did with a suggestion. Undefined means unanswered, which is never submitted. */
export type Decision = { kind: 'accept' } | { kind: 'change'; label: string } | { kind: 'reject' }

export interface AiItem {
  type: VisionType
  response?: AiResponse
  decision?: Decision
}

// ------------------------------------------------------------- labels

interface LabelSpec {
  id: string
  text: string
  group?: string
}

const labelTypes = labelsFile.types as unknown as Record<string, { labels: LabelSpec[] }>

export function allowedLabels(type: FindingType): LabelSpec[] {
  return labelTypes[type]?.labels ?? []
}

export function labelText(type: FindingType, id: string): string {
  return allowedLabels(type).find((l) => l.id === id)?.text ?? id
}

// ------------------------------------------------------------- guided keys

interface KeyOption {
  next?: string
  result?: string | null
}
interface KeyNode {
  question: string
  optional?: boolean
  options: Record<string, KeyOption>
}
export interface KeySpec {
  id: string
  start: string
  nodes: Record<string, KeyNode>
  results: Record<string, string>
  source: string
}

export const KEYS: Record<'larvae' | 'adult_mosquito', KeySpec> = {
  larvae: larvaeKey as unknown as KeySpec,
  adult_mosquito: adultKey as unknown as KeySpec,
}

/** Same algorithm as api/ai/keys.py run_key. */
export function runKey(key: KeySpec, answers: Record<string, string>): string | null {
  let nodeId = key.start
  for (let i = 0; i <= Object.keys(key.nodes).length; i += 1) {
    const node = key.nodes[nodeId]
    const answer = answers[nodeId]
    if (answer === undefined) {
      const results = new Set(Object.values(node.options).map((o) => o.result))
      if (node.optional && results.size === 1 && !results.has(undefined) && !results.has(null)) return [...results][0] as string
      return null
    }
    const option = node.options[answer]
    if (!option) return null
    if ('result' in option) return option.result ?? null
    nodeId = option.next!
  }
  throw new Error(`Key ${key.id} has a cycle`)
}

/** Which questions to show, following the path the citizen's answers take. */
export function keyPath(key: KeySpec, answers: Record<string, string>): string[] {
  const path: string[] = []
  let nodeId: string | undefined = key.start
  while (nodeId && !path.includes(nodeId)) {
    path.push(nodeId)
    const option: KeyOption | undefined = key.nodes[nodeId].options[answers[nodeId]]
    nodeId = option?.next
  }
  return path
}

export function compareKeyVision(keyResult: string | null, vision: string | undefined): 'agree' | 'disagree' | 'incomplete' {
  if (!keyResult || !vision || keyResult === 'not_sure' || vision === 'not_sure') return 'incomplete'
  return keyResult === vision ? 'agree' : 'disagree'
}

// ------------------------------------------------------------- findings

/** The citizen's final label after a decision. */
export function citizenLabel(item: AiItem): string | null {
  const top = item.response?.suggestions[0]
  if (!item.decision || !top) return null
  if (item.decision.kind === 'accept') return top.label
  if (item.decision.kind === 'change') return item.decision.label
  return null
}

/**
 * AI fields for a finding. Unanswered suggestions return nothing: they are never submitted.
 * The AI suggestion and the citizen's answer are stored separately.
 */
export function aiFields(item: AiItem | undefined): Partial<FindingIn> {
  const top = item?.response?.suggestions[0]
  if (!item?.decision || !top || !item.response) return {}
  const status: FindingStatus =
    top.plausibility?.status === 'implausible'
      ? 'expert_review'
      : item.decision.kind === 'accept'
        ? 'confirmed'
        : item.decision.kind === 'change'
          ? 'corrected'
          : 'rejected'
  return {
    ai_label: top.label,
    ai_confidence: top.confidence,
    ai_reason: top.reason,
    ai_provider: item.response.mock ? 'mock' : `${item.response.provider}:${item.response.model}`,
    citizen_answer: citizenLabel(item),
    status,
    data: { dropped: item.response.dropped, plausibility: top.plausibility ?? null },
  }
}
