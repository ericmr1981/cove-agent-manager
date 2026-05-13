import type { FC } from 'react'
import type { AgentInfo } from '../types/session'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-cove-muted',
  running: 'bg-cove-success',
  completed: 'bg-cove-accent',
  failed: 'bg-cove-danger',
  retrying: 'bg-cove-warning',
}

const TYPE_EMOJIS: Record<string, string> = {
  planner: '🧠',
  worker: '🔧',
  reviewer: '👁️',
}

const STATUS_BG: Record<string, string> = {
  pending: 'bg-cove-muted/10 border-cove-muted/30 text-cove-muted',
  running: 'bg-cove-success/10 border-cove-success/30 text-cove-success',
  completed: 'bg-cove-accent/10 border-cove-accent/30 text-cove-accent',
  failed: 'bg-cove-danger/10 border-cove-danger/30 text-cove-danger',
  retrying: 'bg-cove-warning/10 border-cove-warning/30 text-cove-warning',
}

interface AgentCardProps {
  agent: AgentInfo
}

const AgentCard: FC<AgentCardProps> = ({ agent }) => {
  return (
    <div className="bg-cove-surface border border-cove-border rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden="true">{TYPE_EMOJIS[agent.type] || '?'}</span>
          <span className="font-medium text-sm">{agent.id}</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_BG[agent.status] || ''}`}>
          {agent.status}
        </span>
      </div>
      <div className="text-xs text-cove-muted mb-2">{agent.capability || '—'}</div>
      <div className="h-1.5 bg-cove-bg rounded-full overflow-hidden mb-1">
        <div
          className={`h-full rounded-full transition-all ${STATUS_COLORS[agent.status] || 'bg-cove-muted'}`}
          style={{ width: `${agent.progress * 100}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-cove-muted">
        <span>{agent.model}</span>
        {agent.uptime_seconds !== undefined && <span>{Math.floor(agent.uptime_seconds / 60)}m</span>}
      </div>
      {agent.error && <div className="mt-2 text-xs text-cove-danger">⚠️ {agent.error}</div>}
    </div>
  )
}

export default AgentCard
