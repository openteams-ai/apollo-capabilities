import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface ProviderConfig {
  baseUrl: string
  apiKey: string
  model: string
}

interface ProviderStore {
  config: ProviderConfig
  setConfig: (c: Partial<ProviderConfig>) => void
  isConfigured: () => boolean
}

export const useProviderStore = create<ProviderStore>()(
  persist(
    (set, get) => ({
      config: { baseUrl: '', apiKey: '', model: '' },
      setConfig: (c) => set((s) => ({ config: { ...s.config, ...c } })),
      isConfigured: () => {
        const { baseUrl, model } = get().config
        return baseUrl.trim().length > 0 && model.trim().length > 0
      },
    }),
    { name: 'provider-config' },
  ),
)

export function toBackendProvider(c: ProviderConfig) {
  return { base_url: c.baseUrl, api_key: c.apiKey, model: c.model }
}
