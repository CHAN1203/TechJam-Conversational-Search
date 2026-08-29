import { diffSlots } from '../slotDiff'
import type { Turn } from '../types'

interface Props {
  turn: Turn
  previous: Turn | null
}

export function AgentStatePanel({ turn, previous }: Props) {
  const groups = diffSlots(turn.slots, previous?.slots ?? null)

  return (
    <section className="panel panel-agent">
      <header className="panel-head">
        <h2>Agent state</h2>
        <span className="panel-note">
          {turn.fts_match_count !== null
            ? `${turn.fts_match_count.toLocaleString()} catalog matches`
            : 'match count unavailable'}
        </span>
      </header>
      <div className="panel-body">
        <h3 className="subhead">
          Slots
          <span className="legend">
            <i className="dot dot-new" /> new
            <i className="dot dot-dropped" /> dropped
          </span>
        </h3>
        {groups.length === 0 ? (
          <p className="empty">No slots extracted yet.</p>
        ) : (
          <div className="slot-groups">
            {groups.map((group) => (
              <div key={group.slot} className="slot-group">
                <span className="slot-name">{group.slot}</span>
                <div className="slot-terms">
                  {group.rows.map((row) => (
                    <span key={row.term} className={`slot-term is-${row.change}`}>
                      {row.term}
                      {row.arrived !== null && <sup>t{row.arrived}</sup>}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <h3 className="subhead">Query terms ({turn.query_terms.length})</h3>
        {turn.query_terms.length === 0 ? (
          <p className="empty">Empty query — the agent returned nothing this turn.</p>
        ) : (
          <p className="term-cloud">
            {turn.query_terms.map((term) => (
              <span key={term} className="term">
                {term}
              </span>
            ))}
          </p>
        )}

        <h3 className="subhead">Already asked</h3>
        <p className="term-cloud">
          {turn.asked_attributes.length === 0 ? (
            <span className="empty">nothing yet</span>
          ) : (
            turn.asked_attributes.map((attribute) => (
              <span key={attribute} className="term term-muted">
                {attribute}
              </span>
            ))
          )}
        </p>
      </div>
    </section>
  )
}
