// Shared types. Field names mirror api/models.py.

export type FindingType = 'habitat' | 'larvae' | 'adult_mosquito' | 'predator' | 'dead_bird'
export type FindingStatus = 'pending' | 'confirmed' | 'corrected' | 'rejected' | 'manual' | 'expert_review'
export type ObserverTier = 'new' | 'calibrated' | 'trusted'
export type ActionStatus = 'drafted' | 'approved' | 'dismissed'

export interface Site {
  id: string
  name: string
  city_id: string
  city_name: string
  lat: number
  lon: number
  altitude: number | null
  synthetic: boolean
}

export interface Observer {
  id: string
  tier: ObserverTier
  team: string | null
  calibration: Record<string, unknown>
  synthetic: boolean
}

export interface FindingIn {
  type: FindingType
  subject: string
  ai_label?: string | null
  ai_confidence?: number | null
  ai_reason?: string | null
  ai_provider?: string | null
  key_label?: string | null
  citizen_answer?: string | null
  count?: number | null
  status: FindingStatus
  data?: Record<string, unknown>
  synthetic?: boolean
}

export interface Finding extends FindingIn {
  id: number
  checkin_id: number
}

export type AnswerValue = string | number

export interface CheckInDraft {
  client_uuid: string
  site_id: string
  observer_id: string
  observed_at: string
  lat: number | null
  lon: number | null
  consent: boolean
  answers: Record<string, AnswerValue>
  findings: FindingIn[]
  synthetic?: boolean
}

export interface CheckIn extends Omit<CheckInDraft, 'findings'> {
  id: number
  created_at: string
}

export interface CheckInResult {
  checkin: CheckIn
  findings: Finding[]
  duplicate: boolean
}

export interface RiskFactor {
  name: string
  label: string
  value: number | null
  weight: number
  contribution: number
  inputs: Record<string, unknown>
  explanation: string
  data_age_days: number | null
}

export type Band = 'low' | 'moderate' | 'high' | 'very_high'

export interface RiskScore {
  id?: number
  site_id: string
  week: string
  as_of?: string | null
  total: number
  band: Band
  factors: RiskFactor[]
  explanation: string
  config_version: string
  dominant: string | null
  coverage: number
  range_low: number
  range_high: number
  needs_data: boolean
  alert: boolean
  checkin_ids: number[]
  synthetic: boolean
}

export interface MeasureDef {
  title: string
  catalogue: boolean
  service: string
  section: string | null
  page: number | null
  detail?: string
  quote?: string
  note?: string
  mosquito_warning?: string
}

export interface MeasureCatalogue {
  source: string
  source_url: string
  drivers: Record<string, { label: string; measures: string[] }>
  measures: Record<string, MeasureDef>
}

export interface DecisionResult {
  action: Action
  messages: Message[]
}

export interface Action {
  id: number
  site_id: string
  risk_score_id: number | null
  driver: string
  measure_id: string
  title: string
  rationale: string
  status: ActionStatus
  approved_by: string | null
  decision_note: string | null
  decided_at: string | null
  contributors: string[]
  warnings: string[]
  created_at: string
  synthetic: boolean
}

export interface Message {
  id: number
  observer_id: string
  action_id: number | null
  kind: string
  text: string
  read: boolean
  created_at: string
  synthetic: boolean
}

/** A photo waiting in the offline queue, linked to a finding by subject. */
export interface QueuedPhoto {
  subject: string
  blob: Blob
}
