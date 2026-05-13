import { useState, useEffect, type FC } from 'react'

interface ModelConfig {
  anthropicApiKey: string
  openaiApiKey: string
  model: string
  temperature: number
  maxTokens: number
  apiEndpoint: string
}

const MODELS = [
  { id: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4.6', provider: 'anthropic' },
  { id: 'claude-opus-4-20250514', label: 'Claude Opus 4.7', provider: 'anthropic' },
  { id: 'claude-haiku-4-20250514', label: 'Claude Haiku 4.5', provider: 'anthropic' },
  { id: 'gpt-4o', label: 'GPT-4o', provider: 'openai' },
  { id: 'gpt-4o-mini', label: 'GPT-4o-mini', provider: 'openai' },
]

const ModelConfigForm: FC = () => {
  const [config, setConfig] = useState<ModelConfig>({
    anthropicApiKey: '',
    openaiApiKey: '',
    model: 'claude-sonnet-4-20250514',
    temperature: 0.7,
    maxTokens: 4096,
    apiEndpoint: '',
  })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    fetch('/api/v1/config')
      .then(r => r.json())
      .then(data => {
        if (data.model) setConfig(prev => ({ ...prev, model: data.model }))
        if (data.temperature) setConfig(prev => ({ ...prev, temperature: data.temperature }))
        if (data.max_tokens) setConfig(prev => ({ ...prev, maxTokens: data.max_tokens }))
        if (data.api_endpoint) setConfig(prev => ({ ...prev, apiEndpoint: data.api_endpoint }))
      })
      .catch(() => {})
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      // Save API keys via vault API
      if (config.anthropicApiKey) {
        await fetch('/api/v1/vault/anthropic_api_key', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value: config.anthropicApiKey }),
        })
      }
      if (config.openaiApiKey) {
        await fetch('/api/v1/vault/openai_api_key', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value: config.openaiApiKey }),
        })
      }
      // Save model config
      const res = await fetch('/api/v1/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: config.model,
          temperature: config.temperature,
          max_tokens: config.maxTokens,
          api_endpoint: config.apiEndpoint,
        }),
      })
      if (!res.ok) throw new Error('Save failed')
      setMessage({ type: 'success', text: '配置已保存' })
    } catch (e) {
      setMessage({ type: 'error', text: '保存失败: ' + (e instanceof Error ? e.message : 'unknown') })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <section>
        <h3 className="text-sm font-medium mb-3">API 密钥</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-4 space-y-3">
          <div>
            <label className="block text-xs text-cove-muted mb-1">Anthropic API Key</label>
            <input
              type="password"
              value={config.anthropicApiKey}
              onChange={e => setConfig({ ...config, anthropicApiKey: e.target.value })}
              placeholder="sk-ant-..."
              className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs text-cove-muted mb-1">OpenAI API Key</label>
            <input
              type="password"
              value={config.openaiApiKey}
              onChange={e => setConfig({ ...config, openaiApiKey: e.target.value })}
              placeholder="sk-..."
              className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm font-mono"
            />
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-medium mb-3">模型选择</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-4 space-y-3">
          <div>
            <label className="block text-xs text-cove-muted mb-1">模型</label>
            <select
              value={config.model}
              onChange={e => setConfig({ ...config, model: e.target.value })}
              className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm"
            >
              {MODELS.map(m => (
                <option key={m.id} value={m.id}>{m.label} ({m.provider})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-cove-muted mb-1">
              Temperature: {config.temperature}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.temperature}
              onChange={e => setConfig({ ...config, temperature: +e.target.value })}
              className="w-full accent-cove-accent"
            />
            <div className="flex justify-between text-xs text-cove-muted">
              <span>精确 (0)</span>
              <span>创意 (1)</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-cove-muted mb-1">Max Tokens</label>
            <input
              type="number"
              value={config.maxTokens}
              onChange={e => setConfig({ ...config, maxTokens: +e.target.value })}
              min={256}
              max={128000}
              step={256}
              className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-cove-muted mb-1">API 端点（可选，用于代理）</label>
            <input
              type="text"
              value={config.apiEndpoint}
              onChange={e => setConfig({ ...config, apiEndpoint: e.target.value })}
              placeholder="https://api.anthropic.com"
              className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm font-mono"
            />
          </div>
        </div>
      </section>

      {message && (
        <div className={`text-sm px-3 py-2 rounded ${
          message.type === 'success' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        className="px-4 py-2 bg-cove-accent text-white rounded-lg text-sm hover:opacity-90 disabled:opacity-50"
      >
        {saving ? '保存中...' : '保存配置'}
      </button>
    </div>
  )
}

export default ModelConfigForm
