import type { Transcript } from '../types'

interface Props {
  transcript: Transcript
  index: number
  onSelect: (index: number) => void
}

/**
 * One cell per turn, encoding what happened. Doubles as the scrubber, so the
 * shape of a whole session is readable before you step into it.
 */
export function TurnRibbon({ transcript, index, onSelect }: Props) {
  const overrideTurn = transcript.hidden.behavior.override?.turn ?? null

  return (
    <div className="ribbon" role="tablist" aria-label="Turns">
      {transcript.turns.map((turn, position) => {
        const hit = turn.target_rank !== null
        const classes = [
          'ribbon-cell',
          position === index ? 'is-active' : '',
          hit ? 'is-hit' : '',
          turn.error ? 'is-error' : '',
          overrideTurn === turn.turn ? 'is-override' : '',
        ]
          .filter(Boolean)
          .join(' ')

        return (
          <button
            key={turn.turn}
            className={classes}
            role="tab"
            aria-selected={position === index}
            onClick={() => onSelect(position)}
            title={
              `turn ${turn.turn}` +
              (hit ? ` · target at rank ${turn.target_rank}` : ' · target not in top 10') +
              (overrideTurn === turn.turn ? ' · override' : '')
            }
          >
            <span className="ribbon-number">{turn.turn}</span>
            <span className="ribbon-bar" />
          </button>
        )
      })}
    </div>
  )
}
