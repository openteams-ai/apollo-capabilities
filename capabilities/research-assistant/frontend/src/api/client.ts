import type { ProviderConfig } from '../store/providerStore'
import { toBackendProvider } from '../store/providerStore'

export type OutputMode = 'summary' | 'report' | 'pros_cons' | 'timeline' | 'open_questions'
export type ExportTarget = 'notion' | 'linear' | 'hubspot'

export interface Source {
  title: string
  url: string
  snippet: string
}

export interface StreamEvent {
  type: 'chunk' | 'tool_call' | 'tool_error' | 'done' | 'result' | 'error'
  text?: string
  name?: string
  query?: string
  message?: string
  sources?: Source[]
  content?: string
  mode?: OutputMode
}

async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const body = await r.text().catch(() => '')
    throw new Error(`${r.status} ${r.statusText}${body ? ` — ${body}` : ''}`)
  }
  return r.json() as Promise<T>
}

export async function fetchModels(baseUrl: string, apiKey: string): Promise<{ models: string[]; error?: string }> {
  const params = new URLSearchParams({ base_url: baseUrl, api_key: apiKey })
  const r = await fetch(`/api/provider/models?${params}`)
  return jsonOrThrow(r)
}

export async function startResearch(input: {
  topic: string
  outputMode: OutputMode
  provider: ProviderConfig
}): Promise<{ session_id: string }> {
  const r = await fetch('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: input.topic,
      output_mode: input.outputMode,
      provider: toBackendProvider(input.provider),
    }),
  })
  return jsonOrThrow(r)
}

export async function sendFollowUp(
  sessionId: string,
  question: string,
  provider: ProviderConfig,
  outputMode?: OutputMode,
): Promise<{ session_id: string }> {
  const r = await fetch(`/api/research/${sessionId}/followup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      provider: toBackendProvider(provider),
      output_mode: outputMode,
    }),
  })
  return jsonOrThrow(r)
}

export function streamSession(
  sessionId: string,
  onEvent: (e: StreamEvent) => void,
): () => void {
  const es = new EventSource(`/api/research/${sessionId}/stream`)
  es.onmessage = (msg) => {
    try {
      const data: StreamEvent = JSON.parse(msg.data)
      onEvent(data)
      if (data.type === 'result' || data.type === 'error') {
        es.close()
      }
    } catch (err) {
      console.error('bad sse payload', err)
    }
  }
  es.onerror = () => {
    es.close()
  }
  return () => es.close()
}

export async function exportResult(
  sessionId: string,
  target: ExportTarget,
  title?: string,
): Promise<{ ok: boolean; detail: string; target: ExportTarget; url?: string }> {
  const r = await fetch(`/api/research/${sessionId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target, title }),
  })
  return jsonOrThrow(r)
}
