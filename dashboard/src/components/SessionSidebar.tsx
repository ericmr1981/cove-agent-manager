import type { FC } from 'react'
import { useSession } from '../context/SessionContext'

const SessionSidebar: FC = () => {
  const { state } = useSession()

  return (
    <aside className="w-56 border-l border-cove-border p-3 text-sm flex flex-col gap-4 overflow-y-auto">
      <div>
        <h3 className="text-xs text-cove-muted uppercase tracking-wide mb-2">Session</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-3 space-y-2">
          <div>
            <div className="text-xs text-cove-muted">模型</div>
            <div className="text-sm">{state.model}</div>
          </div>
          <div>
            <div className="text-xs text-cove-muted">Tokens</div>
            <div className="text-sm">{state.tokenUsage.toLocaleString()} / {state.tokenLimit.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-xs text-cove-muted">工具</div>
            <div className="text-sm">{state.tools.join(' · ') || '-'}</div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-xs text-cove-muted uppercase tracking-wide mb-2">Sandbox</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-3">
          <div className="text-sm">{state.sandboxImage}</div>
          <div className={`text-xs mt-1 flex items-center gap-1 ${state.sandboxStatus === 'running' ? 'text-cove-success' : 'text-cove-muted'}`}>
            <span className={`w-2 h-2 rounded-full ${state.sandboxStatus === 'running' ? 'bg-cove-success' : 'bg-cove-muted'}`} />
            {state.sandboxStatus}
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-xs text-cove-muted uppercase tracking-wide mb-2">权限模式</h3>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-3">
          <div className="text-sm">{state.permissionMode}</div>
        </div>
      </div>

      {state.agentList.length > 0 && (
        <div>
          <h3 className="text-xs text-cove-muted uppercase tracking-wide mb-2">Agents</h3>
          <div className="space-y-1">
            {state.agentList.map(agent => (
              <div key={agent.id} className="bg-cove-surface border border-cove-border rounded-lg p-2 text-xs">
                <div className="flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${agent.status === 'running' ? 'bg-cove-success' : agent.status === 'failed' ? 'bg-cove-danger' : 'bg-cove-muted'}`} />
                  {agent.id}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}

export default SessionSidebar
