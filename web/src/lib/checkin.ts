import questionsFile from '../../../data/questions.json'
import { roundCoord } from './observer'
import type { AnswerValue, CheckInDraft, FindingIn, QueuedPhoto } from './types'

export type Posture = 'angled' | 'flat' | 'unsure'
export type Amphibians = 'none' | 'heard' | 'seen'

/** Everything the volunteer entered. AI suggestions are added in Phase 3 as separate fields. */
export interface WizardState {
  siteId?: string
  answers: Record<string, AnswerValue>
  skipped: string[]
  dips: number[]
  posture?: Posture
  cupPhoto?: Blob
  amphibians?: Amphibians
  birds: number
  bats?: 'none' | 'seen'
  predatorPhoto?: Blob
  deadBirdsSeen?: 'yes' | 'no'
  deadBirds: number
  deadBirdPhoto?: Blob
  consent: boolean
  extraFindings: FindingIn[]
}

export const emptyState = (): WizardState => ({
  answers: {},
  skipped: [],
  dips: [0, 0, 0, 0, 0],
  birds: 0,
  deadBirds: 0,
  consent: false,
  extraFindings: [],
})

// ------------------------------------------------------------- questions

export interface Question {
  id: string
  label: string
  scale: 'ape' | 'cover5' | 'count'
  protocol_code?: string
  fhir_code?: string
}

export interface Section {
  id: string
  protocol_section: string
  fhir_indicator: string
  per_margin?: string[]
  aquasentinel_addition?: boolean
  questions: Question[]
}

export const questions = questionsFile as unknown as { source: string; sections: Section[] }

/** Answer keys for a section; bank questions are asked once per margin. */
export function answerKeys(section: Section): string[] {
  if (!section.per_margin) return section.questions.map((q) => q.id)
  return section.per_margin.flatMap((m) => section.questions.map((q) => marginKey(q.id, m)))
}

export function marginKey(questionId: string, margin: string): string {
  return questionId.replace(/^bank_/, `bank_${margin}_`)
}

export function answeredCount(section: Section, answers: Record<string, AnswerValue>): number {
  return answerKeys(section).filter((k) => answers[k] !== undefined).length
}

// ------------------------------------------------------------- guided key

/** Larval resting posture key. Culex and Aedes larvae hang at an angle from a siphon; Anopheles lie flat. */
export function larvaKey(posture: Posture | undefined): string | null {
  if (posture === 'angled') return 'culex_or_aedes_type'
  if (posture === 'flat') return 'anopheles_type'
  return null
}

// ------------------------------------------------------------- draft

export interface BuildContext {
  observerId: string
  now: Date
  uuid: string
  position?: { lat: number; lon: number } | null
}

export function buildFindings(s: WizardState): FindingIn[] {
  const findings: FindingIn[] = []
  const total = s.dips.reduce((a, b) => a + b, 0)
  findings.push({ type: 'larvae', subject: 'larval_dips', count: total, status: 'manual', data: { dips: [...s.dips] } })
  if (total > 0 && s.posture) {
    findings.push({
      type: 'larvae',
      subject: 'larval_posture',
      citizen_answer: s.posture,
      key_label: larvaKey(s.posture),
      status: 'manual',
    })
  }
  if (s.amphibians) findings.push({ type: 'predator', subject: 'amphibians', citizen_answer: s.amphibians, status: 'manual' })
  findings.push({ type: 'predator', subject: 'insectivorous_birds', count: s.birds, status: 'manual' })
  if (s.bats) findings.push({ type: 'predator', subject: 'bats', citizen_answer: s.bats, status: 'manual' })
  if (s.deadBirdsSeen === 'yes' && s.deadBirds > 0) {
    findings.push({ type: 'dead_bird', subject: 'dead_bird', count: s.deadBirds, status: 'manual', data: { handled: false } })
  }
  return [...findings, ...s.extraFindings]
}

export function buildDraft(s: WizardState, ctx: BuildContext): { draft: CheckInDraft; photos: QueuedPhoto[] } {
  if (!s.siteId) throw new Error('A site is required')
  const skipped = new Set(s.skipped)
  const answers = Object.fromEntries(
    questions.sections
      .filter((sec) => !skipped.has(sec.id))
      .flatMap((sec) => answerKeys(sec))
      .filter((k) => s.answers[k] !== undefined)
      .map((k) => [k, s.answers[k]]),
  )
  const photos: QueuedPhoto[] = []
  if (s.cupPhoto) photos.push({ subject: 'larval_dips', blob: s.cupPhoto })
  if (s.predatorPhoto) photos.push({ subject: 'predator_photo', blob: s.predatorPhoto })
  if (s.deadBirdPhoto && s.deadBirdsSeen === 'yes') photos.push({ subject: 'dead_bird', blob: s.deadBirdPhoto })
  const draft: CheckInDraft = {
    client_uuid: ctx.uuid,
    site_id: s.siteId,
    observer_id: ctx.observerId,
    observed_at: ctx.now.toISOString(),
    lat: ctx.position ? roundCoord(ctx.position.lat) : null,
    lon: ctx.position ? roundCoord(ctx.position.lon) : null,
    consent: s.consent,
    answers,
    findings: buildFindings(s),
  }
  return { draft, photos }
}
