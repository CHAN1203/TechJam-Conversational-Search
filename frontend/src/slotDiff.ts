import type { SlotState } from './types'

export type SlotChange = 'new' | 'kept' | 'dropped'

export interface SlotRow {
  term: string
  /** Turn the term arrived on. Null when the term was dropped this turn. */
  arrived: number | null
  change: SlotChange
}

export interface SlotGroup {
  slot: string
  rows: SlotRow[]
}

/**
 * Diff the selected turn's slot state against the previous turn's.
 *
 * This is the point of the panel: an intent override drops slots at
 * starter/agent.py:162-178, and seeing exactly which terms vanished is what
 * explains an override session.
 */
export function diffSlots(current: SlotState, previous: SlotState | null): SlotGroup[] {
  const slots = new Set([...Object.keys(current), ...Object.keys(previous ?? {})])
  const groups: SlotGroup[] = []

  for (const slot of [...slots].sort()) {
    const now = current[slot] ?? {}
    const before = previous?.[slot] ?? {}
    const rows: SlotRow[] = Object.entries(now).map(([term, arrived]) => ({
      term,
      arrived,
      change: previous !== null && term in before ? 'kept' : 'new',
    }))
    for (const term of Object.keys(before)) {
      if (!(term in now)) rows.push({ term, arrived: null, change: 'dropped' })
    }
    if (rows.length === 0) continue
    rows.sort((a, b) => (a.arrived ?? 99) - (b.arrived ?? 99) || a.term.localeCompare(b.term))
    groups.push({ slot, rows })
  }
  return groups
}
