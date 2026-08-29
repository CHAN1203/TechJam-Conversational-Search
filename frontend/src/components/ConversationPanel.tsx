import { useEffect, useRef } from 'react'
import type { Turn } from '../types'

interface Props {
  turns: Turn[]
  index: number
  overrideTurn: number | null
  onSelect: (index: number) => void
}

export function ConversationPanel({ turns, index, overrideTurn, onSelect }: Props) {
  const activeRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [index])

  return (
    <section className="panel panel-conversation">
      <header className="panel-head">
        <h2>Conversation</h2>
        <span className="panel-note">simulated customer · agent</span>
      </header>
      <div className="panel-body">
        {turns.slice(0, index + 1).map((turn, position) => (
          <div
            key={turn.turn}
            ref={position === index ? activeRef : undefined}
            className={`exchange ${position === index ? 'is-active' : ''}`}
            onClick={() => onSelect(position)}
          >
            <div className="exchange-rail">
              <span className="exchange-turn">{turn.turn}</span>
            </div>
            <div className="exchange-body">
              {overrideTurn === turn.turn && (
                <p className="override-flag">intent override fires here</p>
              )}
              <p className="message message-user">
                <span className="speaker">Customer</span>
                {turn.user_message}
              </p>
              <p className="message message-agent">
                <span className="speaker">Agent</span>
                {turn.agent_message || <em className="dim">(no message)</em>}
                {turn.ask_attribute && (
                  <span className="ask-chip">asks: {turn.ask_attribute}</span>
                )}
              </p>
              {turn.error && <p className="message message-error">{turn.error}</p>}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
