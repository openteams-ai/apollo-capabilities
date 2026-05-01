import type { OutputMode } from '../api/client'

interface Props {
  topic: string
  setTopic: (s: string) => void
  mode: OutputMode
  setMode: (m: OutputMode) => void
  onSubmit: () => void
  disabled: boolean
  submitLabel?: string
}

const MODES: { value: OutputMode; label: string }[] = [
  { value: 'summary', label: 'Summary' },
  { value: 'report', label: 'Report' },
  { value: 'pros_cons', label: 'Pros & Cons' },
  { value: 'timeline', label: 'Timeline' },
  { value: 'open_questions', label: 'Open Questions' },
]

export function QueryBar({ topic, setTopic, mode, setMode, onSubmit, disabled, submitLabel }: Props) {
  return (
    <div className="panel col">
      <div className="field">
        <label>Topic or question</label>
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. AI regulation in the EU in 2026 — what changed and who is affected?"
          rows={3}
        />
      </div>
      <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <div className="row">
          <label className="muted small" htmlFor="mode-select">Output</label>
          <select
            id="mode-select"
            value={mode}
            onChange={(e) => setMode(e.target.value as OutputMode)}
            style={{ width: 'auto' }}
          >
            {MODES.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
        <button className="primary" onClick={onSubmit} disabled={disabled || !topic.trim()}>
          {submitLabel ?? 'Research'}
        </button>
      </div>
    </div>
  )
}
