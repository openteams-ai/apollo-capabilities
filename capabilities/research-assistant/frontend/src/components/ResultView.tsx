import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Source } from '../api/client'

interface Props {
  topic: string
  content: string
  sources: Source[]
}

export function ResultView({ topic, content, sources }: Props) {
  const copy = async () => {
    await navigator.clipboard.writeText(content)
  }

  const download = () => {
    const blob = new Blob([content], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${topic.slice(0, 40).replace(/\W+/g, '-') || 'research'}.md`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div className="panel col">
      <div className="bubble">
        <span className="label">Result</span>
        <div className="markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      </div>

      {sources.length > 0 && (
        <details>
          <summary className="muted small" style={{ cursor: 'pointer' }}>
            {sources.length} source(s) gathered
          </summary>
          <ol className="muted small" style={{ marginTop: 8 }}>
            {sources.map((s, i) => (
              <li key={i}>
                <a href={s.url} target="_blank" rel="noreferrer">{s.title || s.url}</a>
              </li>
            ))}
          </ol>
        </details>
      )}

      <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
        <button onClick={copy}>Copy markdown</button>
        <button onClick={download}>Export .md</button>
      </div>
    </div>
  )
}
