import type { Transcript } from './types'

const OFFLINE =
  'Cannot reach the session API. Start it with:  python -m frontend.server.app'

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: string }
    return body.error ?? `HTTP ${response.status}`
  } catch {
    return `HTTP ${response.status}`
  }
}

export async function runSample(sample: number): Promise<Transcript> {
  let response: Response
  try {
    response = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sample }),
    })
  } catch {
    throw new Error(OFFLINE)
  }
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as Transcript
}

export interface Health {
  ok: boolean
  sample_count: number
  agent: AgentSummary
}

export interface AgentSummary {
  clarification_policy: string
  candidate_pool_size: number
  gazetteer_slots: string[]
  catalog_size: number
}

export async function fetchHealth(): Promise<Health> {
  let response: Response
  try {
    response = await fetch('/api/health')
  } catch {
    throw new Error(OFFLINE)
  }
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as Health
}
