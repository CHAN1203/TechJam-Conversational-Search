import { useState } from 'react'
import type { AgentSummary } from '../api'
import type { Transcript } from '../types'

interface Props {
  sampleCount: number
  agent: AgentSummary | null
  transcript: Transcript | null
  loading: boolean
  onRun: (sample: number) => void
}

export function HeaderBar({ sampleCount, agent, transcript, loading, onRun }: Props) {
  const [value, setValue] = useState('1')
  const [invalid, setInvalid] = useState<string | null>(null)
  const max = sampleCount || 200

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = value.trim()
    if (!/^\d+$/.test(trimmed)) {
      setInvalid('whole numbers only')
      return
    }
    const parsed = Number(trimmed)
    if (parsed < 1 || parsed > max) {
      setInvalid(`1–${max}`)
      return
    }
    setInvalid(null)
    onRun(parsed)
  }

  const metrics = transcript?.metrics

  return (
    <header className="masthead">
      <div className="masthead-left">
        <h1>
          session<span className="glyph">/</span>viewer
        </h1>
        {agent && (
          <p className="masthead-config">
            {agent.clarification_policy} · pool {agent.candidate_pool_size} ·{' '}
            {agent.catalog_size.toLocaleString()} products
          </p>
        )}
      </div>

      <form className="sample-form" onSubmit={submit}>
        <label htmlFor="sample">sample</label>
        <input
          id="sample"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className={invalid ? 'is-invalid' : ''}
          inputMode="numeric"
          autoComplete="off"
          autoFocus
        />
        <button type="submit" disabled={loading}>
          {loading ? 'running' : 'run'}
        </button>
        <span className="sample-hint">{invalid ?? `1–${max}`}</span>
      </form>

      {transcript && metrics && (
        <div className="masthead-metrics">
          <span className="sample-id">{transcript.sample.sample_id}</span>
          <span className={`tag tag-${transcript.sample.scenario_type}`}>
            {transcript.sample.scenario_type}
          </span>
          <span className="tag tag-muted">{transcript.sample.difficulty_bucket}</span>
          <span className={`verdict ${metrics.hit ? 'is-hit' : 'is-miss'}`}>
            {metrics.hit ? 'HIT' : 'MISS'}
          </span>
          <dl className="metric-strip">
            <div>
              <dt>rank</dt>
              <dd>{metrics.best_rank ?? '—'}</dd>
            </div>
            <div>
              <dt>hit turn</dt>
              <dd>{metrics.first_hit_turn ?? '—'}</dd>
            </div>
            <div>
              <dt>rr</dt>
              <dd>{metrics.reciprocal_rank.toFixed(3)}</dd>
            </div>
          </dl>
        </div>
      )}
    </header>
  )
}
