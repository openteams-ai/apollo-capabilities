import { useEffect, useState } from 'react'
import { fetchModels } from '../api/client'
import { useProviderStore } from '../store/providerStore'

const PRESETS: { label: string; baseUrl: string }[] = [
  { label: 'llama.cpp (local)', baseUrl: 'http://localhost:8080/v1' },
  { label: 'Ollama (local)', baseUrl: 'http://localhost:11434/v1' },
  { label: 'Docker (local)', baseUrl: 'http://localhost:12434/engines/v1' },
  { label: 'Custom (OpenAI spec)', baseUrl: '' },
  { label: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1' },
]

interface Props {
  open: boolean
  onClose: () => void
}

export function ProviderConfig({ open, onClose }: Props) {
  const config = useProviderStore((s) => s.config)
  const setConfig = useProviderStore((s) => s.setConfig)

  const [baseUrl, setBaseUrl] = useState(config.baseUrl)
  const [apiKey, setApiKey] = useState(config.apiKey)
  const [model, setModel] = useState(config.model)
  const [models, setModels] = useState<string[]>([])
  const [status, setStatus] = useState<{ kind: 'idle' | 'ok' | 'error' | 'loading'; msg?: string }>({ kind: 'idle' })

  useEffect(() => {
    if (open) {
      setBaseUrl(config.baseUrl)
      setApiKey(config.apiKey)
      setModel(config.model)
    }
  }, [open, config])

  const test = async () => {
    if (!baseUrl.trim()) {
      setStatus({ kind: 'error', msg: 'Enter a base URL first.' })
      return
    }
    setStatus({ kind: 'loading' })
    try {
      const res = await fetchModels(baseUrl.trim(), apiKey.trim())
      setModels(res.models)
      if (res.models.length > 0) {
        setStatus({ kind: 'ok', msg: `Found ${res.models.length} model(s).` })
        if (!model && res.models[0]) setModel(res.models[0])
      } else {
        setStatus({ kind: 'error', msg: res.error || 'No models returned. Type a model name manually.' })
      }
    } catch (err: unknown) {
      setStatus({ kind: 'error', msg: err instanceof Error ? err.message : String(err) })
    }
  }

  const save = () => {
    setConfig({ baseUrl: baseUrl.trim(), apiKey: apiKey.trim(), model: model.trim() })
    onClose()
  }

  if (!open) return null

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Provider</h2>
          <button onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="col">
          <div className="muted small">Pre-fill a base URL:</div>
          <div className="preset-row">
            {PRESETS.map((p) => (
              <button key={p.label} onClick={() => setBaseUrl(p.baseUrl)}>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Base URL</label>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.openai.com/v1"
          />
        </div>

        <div className="field">
          <label>API key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-..."
          />
          <span className="muted small">Use any string for local endpoints.</span>
        </div>

        <div className="field">
          <label>Model</label>
          {models.length > 0 ? (
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              {!models.includes(model) && model && <option value={model}>{model}</option>}
              {models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          ) : (
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="gpt-4o, llama3.2, ..."
            />
          )}
          <span className="muted small">
            Click "Test connection" to populate the model list, or type a model name directly.
          </span>
        </div>

        <div className="row">
          <button onClick={test} disabled={status.kind === 'loading'}>
            {status.kind === 'loading' ? 'Testing…' : 'Test connection'}
          </button>
          <button className="primary" onClick={save} disabled={!baseUrl.trim() || !model.trim()}>
            Save
          </button>
        </div>

        {status.kind === 'ok' && <div className="success small">✓ {status.msg}</div>}
        {status.kind === 'error' && <div className="error small">✗ {status.msg}</div>}

        <div className="divider" />
        <div className="muted small">
          The API key is held in memory only. Base URL and model are persisted across reloads,
          but the key is cleared every time you reopen the app.
        </div>
      </div>
    </div>
  )
}
