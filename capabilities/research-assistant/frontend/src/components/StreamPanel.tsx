import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  text: string
  toolCalls: { name: string; query: string }[]
  active: boolean
}

export function StreamPanel({ text, toolCalls, active }: Props) {
  if (!active && !text && toolCalls.length === 0) return null
  return (
    <div className="panel col">
      <div className="bubble">
        <span className="label">{active ? 'Thinking…' : 'Draft'}</span>
        {toolCalls.length > 0 && (
          <div className="col" style={{ gap: 4 }}>
            {toolCalls.map((tc, i) => (
              <span key={i} className="tool-badge">
                🔎 {tc.name}: <em>{tc.query}</em>
              </span>
            ))}
          </div>
        )}
        {text && (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
