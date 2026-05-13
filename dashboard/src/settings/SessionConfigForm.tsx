import { useState, type FC } from 'react'

interface SessionConfig {
  systemPrompt: string
  model: string
  maxTurns: number
  maxBudgetUsd: number
  permissionMode: string
  tools: string[]
  sandboxImage: string
  network: string
}

const AVAILABLE_TOOLS = ['Bash', 'Read', 'Edit', 'Grep', 'Glob', 'WebSearch', 'WebFetch']

const presetTools: Record<string, string[]> = {
  'READ_ONLY': ['Read', 'Grep', 'Glob'],
  'READ_WRITE': ['Read', 'Edit', 'Bash'],
  'EXECUTE': ['Bash', 'Read'],
  'SEARCH': ['WebSearch', 'WebFetch'],
  'THINK': [],
}

const SessionConfigForm: FC = () => {
  const [config, setConfig] = useState<SessionConfig>({
    systemPrompt: 'You are a helpful coding assistant...',
    model: 'claude-sonnet-4-5',
    maxTurns: 50,
    maxBudgetUsd: 10,
    permissionMode: 'acceptEdits',
    tools: ['Bash', 'Read', 'Edit'],
    sandboxImage: 'cove/sandbox:python-3.12',
    network: 'restricted',
  })

  return (
    <div className="max-w-2xl space-y-6">
      <section>
        <h3 className="text-sm font-medium mb-3">模型配置</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-4 space-y-3">
          <div>
            <label className="block text-xs text-cove-muted mb-1">模型</label>
            <select
              value={config.model}
              onChange={e => setConfig({ ...config, model: e.target.value })}
              className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm"
            >
              <option value="claude-sonnet-4-5">Claude Sonnet 4.5</option>
              <option value="claude-opus-4-1">Claude Opus 4.1</option>
              <option value="claude-haiku-4-5">Claude Haiku 4.5</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-cove-muted mb-1">最大轮次</label>
              <input type="number" value={config.maxTurns} onChange={e => setConfig({ ...config, maxTurns: +e.target.value })} className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-cove-muted mb-1">预算 ($)</label>
              <input type="number" step="0.5" value={config.maxBudgetUsd} onChange={e => setConfig({ ...config, maxBudgetUsd: +e.target.value })} className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm" />
            </div>
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-medium mb-3">工具配置</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-4">
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.entries(presetTools).map(([name, tools]) => (
              <button
                key={name}
                onClick={() => setConfig({ ...config, tools })}
                className="px-2 py-1 text-xs border border-cove-border rounded hover:border-cove-accent"
              >
                {name}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_TOOLS.map(tool => (
              <label key={tool} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={config.tools.includes(tool)}
                  onChange={e => {
                    const updated = e.target.checked
                      ? [...config.tools, tool]
                      : config.tools.filter(t => t !== tool)
                    setConfig({ ...config, tools: updated })
                  }}
                  className="accent-cove-accent"
                />
                {tool}
              </label>
            ))}
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-medium mb-3">权限模式</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-4">
          <select
            value={config.permissionMode}
            onChange={e => setConfig({ ...config, permissionMode: e.target.value })}
            className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm"
          >
            <option value="auto">Auto — AI 自动决策</option>
            <option value="acceptEdits">AcceptEdits — 编辑类自动允许，危险操作需审批</option>
            <option value="bypassPermissions">Bypass — 绕过所有权限</option>
          </select>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-medium mb-3">Sandbox 配置</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-4 space-y-3">
          <div>
            <label className="block text-xs text-cove-muted mb-1">镜像</label>
            <input type="text" value={config.sandboxImage} onChange={e => setConfig({ ...config, sandboxImage: e.target.value })} className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm font-mono" />
          </div>
          <div>
            <label className="block text-xs text-cove-muted mb-1">网络</label>
            <select
              value={config.network}
              onChange={e => setConfig({ ...config, network: e.target.value })}
              className="w-full bg-cove-bg border border-cove-border rounded px-2 py-1.5 text-sm"
            >
              <option value="isolated">隔离</option>
              <option value="restricted">受限</option>
              <option value="full">完整</option>
            </select>
          </div>
        </div>
      </section>
    </div>
  )
}

export default SessionConfigForm
