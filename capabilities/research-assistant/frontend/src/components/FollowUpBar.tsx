import { useState } from 'react'

interface Props {
  onSubmit: (question: string) => void
  disabled: boolean
}

export function FollowUpBar({ onSubmit, disabled }: Props) {
  const [q, setQ] = useState('')

  const submit = () => {
    if (!q.trim() || disabled) return
    onSubmit(q.trim())
    setQ('')
  }

  return (
    <div className="panel row" style={{ gap: 8 }}>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
        placeholder="Ask a follow-up question…"
        disabled={disabled}
      />
      <button className="primary" onClick={submit} disabled={disabled || !q.trim()}>
        Ask
      </button>
    </div>
  )
}
