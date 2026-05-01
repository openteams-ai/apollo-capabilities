import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { exportResult, type ExportTarget, type Source } from '../api/client'

interface Props {
  sessionId: string
  topic: string
  content: string
  sources: Source[]
}

export function ResultView({ sessionId, topic, content, sources }: Props) {
  const [exportStatus, setExportStatus] = useState<{ kind: 'idle' | 'ok' | 'error' | 'loading'; msg?: string }>({ kind: 'idle' })

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

  const doExport = async (target: ExportTarget) => {
    setExportStatus({ kind: 'loading', msg: `Exporting to ${target}…` })
    try {
      const res = await exportResult(sessionId, target, topic)
      setExportStatus({
        kind: res.ok ? 'ok' : 'error',
        msg: res.detail || (res.ok ? `Saved to ${target}.` : `Export to ${target} failed.`),
      })
    } catch (err: unknown) {
      setExportStatus({ kind: 'error', msg: err instanceof Error ? err.message : String(err) })
    }
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
        <div style={{ flex: 1 }} />
        <button onClick={() => doExport('notion')} disabled={exportStatus.kind === 'loading'}>Save to Notion</button>
        <button onClick={() => doExport('linear')} disabled={exportStatus.kind === 'loading'}>Save to Linear</button>
        <button onClick={() => doExport('hubspot')} disabled={exportStatus.kind === 'loading'}>Save to HubSpot</button>
      </div>

      {exportStatus.kind === 'ok' && <div className="success small">✓ {exportStatus.msg}</div>}
      {exportStatus.kind === 'error' && <div className="error small">✗ {exportStatus.msg}</div>}
      {exportStatus.kind === 'loading' && <div className="muted small">{exportStatus.msg}</div>}
    </div>
  )
}
