import { useCallback, useEffect, useState } from 'react'
import { fetchHealth, runSample, type AgentSummary } from './api'
import { AgentStatePanel } from './components/AgentStatePanel'
import { ConversationPanel } from './components/ConversationPanel'
import { HeaderBar } from './components/HeaderBar'
import { HiddenStatePanel } from './components/HiddenStatePanel'
import { PlaybackControls } from './components/PlaybackControls'
import { RecommendationsPanel } from './components/RecommendationsPanel'
import { TurnRibbon } from './components/TurnRibbon'
import type { Transcript } from './types'
import { usePlayback } from './usePlayback'

export default function App() {
  const [transcript, setTranscript] = useState<Transcript | null>(null)
  const [agent, setAgent] = useState<AgentSummary | null>(null)
  const [sampleCount, setSampleCount] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const playback = usePlayback(transcript?.turns.length ?? 0)
  const { index, setIndex, next, previous, toggle } = playback

  useEffect(() => {
    fetchHealth()
      .then((health) => {
        setAgent(health.agent)
        setSampleCount(health.sample_count)
        setError(null)
      })
      .catch((cause: Error) => setError(cause.message))
  }, [])

  const run = useCallback(async (sample: number) => {
    setLoading(true)
    try {
      setTranscript(await runSample(sample))
      setError(null)
    } catch (cause) {
      setTranscript(null)
      setError((cause as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement
      if (target.tagName === 'INPUT') return
      if (event.key === 'ArrowRight') next()
      else if (event.key === 'ArrowLeft') previous()
      else if (event.key === ' ') {
        event.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [next, previous, toggle])

  const turn = transcript?.turns[index] ?? null
  const previousTurn = index > 0 ? (transcript?.turns[index - 1] ?? null) : null

  return (
    <div className="shell">
      <HeaderBar
        sampleCount={sampleCount}
        agent={agent}
        transcript={transcript}
        loading={loading}
        onRun={run}
      />

      {transcript && (
        <TurnRibbon transcript={transcript} index={index} onSelect={setIndex} />
      )}

      {error && (
        <div className="notice notice-error">
          <p>{error}</p>
        </div>
      )}

      {!transcript && !error && (
        <div className="notice">
          <p className="notice-lead">Type a sample number and press run.</p>
          <p>
            The session is replayed through the unmodified evaluator, so what you see is
            what a scoring run produces. Use <kbd>←</kbd> <kbd>→</kbd> to step,{' '}
            <kbd>space</kbd> to play.
          </p>
        </div>
      )}

      {transcript && turn && (
        <>
          <main className="grid" key={`${transcript.sample.index}-${index}`}>
            <ConversationPanel
              turns={transcript.turns}
              index={index}
              overrideTurn={transcript.hidden.behavior.override?.turn ?? null}
              onSelect={setIndex}
            />
            <HiddenStatePanel
              hidden={transcript.hidden}
              sample={transcript.sample}
              turn={turn}
            />
            <RecommendationsPanel turn={turn} />
            <AgentStatePanel turn={turn} previous={previousTurn} />
          </main>
          <PlaybackControls playback={playback} count={transcript.turns.length} />
        </>
      )}
    </div>
  )
}
