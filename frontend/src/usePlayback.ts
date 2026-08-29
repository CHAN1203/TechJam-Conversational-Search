import { useCallback, useEffect, useState } from 'react'

const BASE_INTERVAL_MS = 1200

export interface Playback {
  index: number
  playing: boolean
  speed: number
  atEnd: boolean
  setIndex: (index: number) => void
  next: () => void
  previous: () => void
  toggle: () => void
  cycleSpeed: () => void
}

const SPEEDS = [0.5, 1, 2, 4]

export function usePlayback(count: number): Playback {
  const [index, setRawIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)

  useEffect(() => {
    setRawIndex(0)
    setPlaying(false)
  }, [count])

  const setIndex = useCallback(
    (value: number) => setRawIndex(Math.max(0, Math.min(count - 1, value))),
    [count],
  )
  const next = useCallback(() => setIndex(index + 1), [index, setIndex])
  const previous = useCallback(() => setIndex(index - 1), [index, setIndex])

  const atEnd = count === 0 || index >= count - 1

  const toggle = useCallback(() => {
    if (count === 0) return
    // Replaying from the end should start over rather than sit still.
    if (!playing && index >= count - 1) setRawIndex(0)
    setPlaying((value) => !value)
  }, [count, index, playing])

  useEffect(() => {
    if (!playing || count === 0) return
    const id = window.setInterval(
      () => setRawIndex((value) => Math.min(count - 1, value + 1)),
      BASE_INTERVAL_MS / speed,
    )
    return () => window.clearInterval(id)
  }, [playing, speed, count])

  useEffect(() => {
    if (playing && atEnd) setPlaying(false)
  }, [playing, atEnd])

  const cycleSpeed = useCallback(
    () => setSpeed((value) => SPEEDS[(SPEEDS.indexOf(value) + 1) % SPEEDS.length]),
    [],
  )

  return { index, playing, speed, atEnd, setIndex, next, previous, toggle, cycleSpeed }
}
