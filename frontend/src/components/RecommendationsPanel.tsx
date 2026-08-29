import type { Turn } from '../types'

interface Props {
  turn: Turn
}

export function RecommendationsPanel({ turn }: Props) {
  return (
    <section className="panel panel-recommendations">
      <header className="panel-head">
        <h2>Top 10</h2>
        <span className="panel-note">
          turn {turn.turn} ·{' '}
          {turn.target_rank !== null ? (
            <strong className="hit-note">target at rank {turn.target_rank}</strong>
          ) : (
            'target not in top 10'
          )}
        </span>
      </header>
      <div className="panel-body">
        {turn.recommendations.length === 0 ? (
          <p className="empty">No recommendations returned this turn.</p>
        ) : (
          <ol className="rank-list">
            {turn.recommendations.map((item) => (
              <li
                key={item.parent_asin}
                className={`rank-row ${item.is_target ? 'is-target' : ''}`}
              >
                <span className="rank-number">{item.rank}</span>
                <span className="rank-asin">{item.parent_asin}</span>
                <span className="rank-title">{item.title || '—'}</span>
                {item.is_target && <span className="rank-flag">target</span>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  )
}
