import type { Hidden, SampleMeta, Turn } from '../types'

interface Props {
  hidden: Hidden
  sample: SampleMeta
  turn: Turn
}

function ConstraintList({
  label,
  values,
  disclosed,
}: {
  label: string
  values: string[]
  disclosed: string[]
}) {
  if (values.length === 0) return null
  return (
    <div className="constraint-block">
      <span className="constraint-label">{label}</span>
      <ul className="constraint-list">
        {values.map((value) => {
          const revealed = disclosed.includes(value)
          return (
            <li key={value} className={revealed ? 'is-revealed' : 'is-held'}>
              <span className="constraint-mark">{revealed ? '✓' : '○'}</span>
              <span>{value}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function HiddenStatePanel({ hidden, sample, turn }: Props) {
  const { target, intent_card, behavior } = hidden
  const held = [...intent_card.hard_constraints, ...intent_card.soft_preferences].filter(
    (value) => !turn.disclosed.includes(value),
  )

  return (
    <section className="panel panel-hidden">
      <header className="panel-head">
        <h2>Target &amp; hidden state</h2>
        <span className="panel-note">not visible to the agent</span>
      </header>
      <div className="panel-body">
        <div className="target-card">
          <span className="target-asin">{target.parent_asin}</span>
          <p className="target-title">{target.title}</p>
          <p className="target-meta">
            {hidden.coarse_category}
            {target.store && ` · ${target.store}`}
            {target.price !== null && target.price !== undefined && ` · $${target.price}`}
          </p>
        </div>

        <ConstraintList
          label="hard constraints"
          values={intent_card.hard_constraints}
          disclosed={turn.disclosed}
        />
        <ConstraintList
          label="soft preferences"
          values={intent_card.soft_preferences}
          disclosed={turn.disclosed}
        />
        <p className="derived-note">
          Disclosure is reconstructed by matching constraint text against the customer's
          messages — the evaluator keeps this set private.
          {held.length > 0 && (
            <>
              {' '}
              <strong>{held.length}</strong> still unrevealed at this turn.
            </>
          )}
        </p>

        {behavior.override && (
          <div className="override-card">
            <span className="constraint-label">override · turn {behavior.override.turn}</span>
            <p className="override-line">
              <span className="dim">drops</span> {behavior.override.old_value}
            </p>
            <p className="override-line">
              <span className="dim">wants</span> {behavior.override.new_value}
            </p>
          </div>
        )}

        <div className="profile-card">
          <span className="constraint-label">customer profile</span>
          <p>{sample.user_profile.summary ?? '—'}</p>
          <p className="term-cloud">
            {(sample.user_profile.preference_tags ?? []).map((tag) => (
              <span key={tag} className="term term-muted">
                {tag}
              </span>
            ))}
          </p>
        </div>
      </div>
    </section>
  )
}
