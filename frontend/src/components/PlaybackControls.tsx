import type { Playback } from '../usePlayback'

interface Props {
  playback: Playback
  count: number
}

export function PlaybackControls({ playback, count }: Props) {
  const { index, playing, speed, previous, next, toggle, cycleSpeed } = playback

  return (
    <footer className="transport">
      <div className="transport-buttons">
        <button onClick={previous} disabled={index === 0} title="Previous turn (←)">
          ‹
        </button>
        <button className="transport-play" onClick={toggle} title="Play / pause (space)">
          {playing ? '❚❚' : '▶'}
        </button>
        <button onClick={next} disabled={index >= count - 1} title="Next turn (→)">
          ›
        </button>
      </div>

      <div className="transport-scrub">
        <div className="scrub-track">
          <div
            className="scrub-fill"
            style={
              {
                '--progress': count > 1 ? index / (count - 1) : 1,
              } as React.CSSProperties
            }
          />
        </div>
      </div>

      <div className="transport-readout">
        <span className="readout-turn">
          turn {index + 1} <span className="dim">/ {count}</span>
        </span>
        <button className="speed" onClick={cycleSpeed} title="Playback speed">
          {speed}×
        </button>
      </div>
    </footer>
  )
}
