import { useCallback, useRef, useState } from 'react'
import {
  type OutputMode,
  type Source,
  type StreamEvent,
  sendFollowUp,
  startResearch,
  streamSession,
} from './api/client'
import { FollowUpBar } from './components/FollowUpBar'
import { ProviderConfig } from './components/ProviderConfig'
import { QueryBar } from './components/QueryBar'
import { ResultView } from './components/ResultView'
import { StreamPanel } from './components/StreamPanel'
import { useProviderStore } from './store/providerStore'

interface Turn {
  topic: string
  mode: OutputMode
  result?: string
  sources: Source[]
}

export default function App() {
  const config = useProviderStore((s) => s.config)
  const isConfigured = useProviderStore((s) => s.isConfigured)()

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [topic, setTopic] = useState('')
  const [mode, setMode] = useState<OutputMode>('summary')

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])

  const [streamText, setStreamText] = useState('')
  const [toolCalls, setToolCalls] = useState<{ name: string; query: string }[]>([])
  const [active, setActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cancelRef = useRef<(() => void) | null>(null)

  const handleEvent = useCallback(
    (e: StreamEvent, pendingTurn: Turn) => {
      if (e.type === 'chunk' && e.text) {
        setStreamText((s) => s + e.text)
      } else if (e.type === 'tool_call' && e.name) {
        setToolCalls((tcs) => [...tcs, { name: e.name!, query: e.query || '' }])
      } else if (e.type === 'tool_error') {
        setError(e.message || 'Tool error')
      } else if (e.type === 'done') {
        // wait for "result" event before closing
      } else if (e.type === 'result' && e.content) {
        const finished: Turn = { ...pendingTurn, result: e.content, sources: e.sources ?? pendingTurn.sources }
        setTurns((arr) => [...arr.slice(0, -1), finished])
        setStreamText('')
        setToolCalls([])
        setActive(false)
      } else if (e.type === 'error') {
        setError(e.message || 'Unknown error')
        setActive(false)
      }
    },
    [],
  )

  const beginStream = (sid: string, pendingTurn: Turn) => {
    setActive(true)
    setError(null)
    setStreamText('')
    setToolCalls([])
    cancelRef.current?.()
    cancelRef.current = streamSession(sid, (e) => handleEvent(e, pendingTurn))
  }

  const onResearch = async () => {
    if (!topic.trim() || !isConfigured) return
    try {
      const pendingTurn: Turn = { topic: topic.trim(), mode, sources: [] }
      setTurns((arr) => [...arr, pendingTurn])
      const { session_id } = await startResearch({ topic: topic.trim(), outputMode: mode, provider: config })
      setSessionId(session_id)
      beginStream(session_id, pendingTurn)
      setTopic('')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
      setActive(false)
    }
  }

  const onFollowUp = async (q: string) => {
    if (!sessionId) return
    try {
      const pendingTurn: Turn = { topic: q, mode, sources: [] }
      setTurns((arr) => [...arr, pendingTurn])
      await sendFollowUp(sessionId, q, config, mode)
      beginStream(sessionId, pendingTurn)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
      setActive(false)
    }
  }

  return (
    <div className="app">
      <div className="header">
        <h1>Research Assistant</h1>
        <div className="row">
          <span className="muted small">
            {isConfigured ? `${config.model} @ ${config.baseUrl.replace(/^https?:\/\//, '')}` : 'No provider configured'}
          </span>
          <button onClick={() => setSettingsOpen(true)}>Provider</button>
        </div>
      </div>

      <div className="col" style={{ overflowY: 'auto', minHeight: 0 }}>
        {!isConfigured && (
          <div className="banner">
            <strong>Configure your LLM provider to get started →</strong>
            <div className="muted small">
              Open the <em>Provider</em> drawer in the top right to enter a base URL, API key, and model.
            </div>
          </div>
        )}

        <QueryBar
          topic={topic}
          setTopic={setTopic}
          mode={mode}
          setMode={setMode}
          onSubmit={onResearch}
          disabled={!isConfigured || active}
          submitLabel={turns.length === 0 ? 'Research' : 'New research'}
        />

        <div className="thread">
          {turns.map((turn, i) => {
            const isLast = i === turns.length - 1
            const showLive = isLast && active && !turn.result
            return (
              <div key={i} className="col">
                <div className="panel">
                  <span className="label">You asked</span>
                  <div>{turn.topic}</div>
                  <div className="muted small">Output mode: {turn.mode}</div>
                </div>

                {showLive && <StreamPanel text={streamText} toolCalls={toolCalls} active={active} />}

                {turn.result && (
                  <ResultView
                    topic={turn.topic}
                    content={turn.result}
                    sources={turn.sources}
                  />
                )}
              </div>
            )
          })}
        </div>

        {error && <div className="panel error">⚠ {error}</div>}

        {sessionId && turns.length > 0 && turns.at(-1)?.result && (
          <FollowUpBar onSubmit={onFollowUp} disabled={active || !isConfigured} />
        )}
      </div>

      <ProviderConfig open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
