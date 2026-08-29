/** Mirrors the payload built by frontend/server/transcript.py. */

export interface Recommendation {
  rank: number
  parent_asin: string
  title: string
  is_target: boolean
}

/** Slot name -> term -> the turn on which that term arrived. */
export type SlotState = Record<string, Record<string, number>>

export interface Turn {
  turn: number
  user_message: string
  agent_message: string
  ask_attribute: string | null
  recommendations: Recommendation[]
  target_rank: number | null
  slots: SlotState
  query_terms: string[]
  asked_attributes: string[]
  fts_match_count: number | null
  error: string | null
  /** Reconstructed, not read from the evaluator. See transcript.derive_disclosed. */
  disclosed: string[]
}

export interface Metrics {
  sample_id: string
  scenario_type: string
  hit: boolean
  first_hit_turn: number | null
  best_rank: number | null
  reciprocal_rank: number
}

export interface UserProfile {
  summary?: string
  preference_tags?: string[]
  purchase_frequency?: string
  rating_style?: string
  average_prior_rating?: number
}

export interface SampleMeta {
  index: number
  sample_id: string
  scenario_type: string
  difficulty_bucket: string
  category_bucket: string
  user_profile: UserProfile
}

export interface Target {
  parent_asin: string
  title: string
  store: string
  price: number | null
  categories: string[]
  features: string[]
  details: Record<string, string>
}

export interface IntentCard {
  target_category: string
  hard_constraints: string[]
  soft_preferences: string[]
}

export interface Override {
  turn: number
  old_value: string
  new_value: string
  message: string
}

export interface Behavior {
  scenario_type: string
  override?: Override
}

export interface Hidden {
  target: Target
  intent_card: IntentCard
  behavior: Behavior
  coarse_category: string
}

export interface AgentConfig {
  clarification_policy: string
  candidate_pool_size: number
  gazetteer_slots: string[]
  catalog_size: number
}

export interface Transcript {
  sample: SampleMeta
  metrics: Metrics
  turns: Turn[]
  hidden: Hidden
  agent: AgentConfig
}
