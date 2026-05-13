import { useState, type FC } from 'react'
import { useWebSocketContext } from '../context/WebSocketContext'

interface PermissionCardProps {
  requestId: string
  tool: string
  command: string
  onResolved?: () => void
}

const PermissionCard: FC<PermissionCardProps> = ({ requestId, tool, command, onResolved }) => {
  const { sendPermissionResponse } = useWebSocketContext()
  const [resolved, setResolved] = useState(false)

  const handleDecision = (decision: 'allow' | 'deny' | 'always_allow') => {
    sendPermissionResponse(requestId, decision)
    setResolved(true)
    onResolved?.()
  }

  if (resolved) {
    return (
      <div className="flex gap-3">
        <div className="flex-shrink-0 w-8" />
        <div className="flex-1 bg-cove-surface border border-cove-border rounded-lg p-3">
          <span className="text-xs text-cove-muted">✅ 已处理</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8" />
      <div className="flex-1 bg-cove-surface border border-cove-border rounded-lg p-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-cove-warning">🔒</span>
          <span className="text-sm">需要权限：<code className="text-cove-accent bg-cove-bg px-1 rounded">{tool}</code></span>
        </div>
        <pre className="text-xs text-cove-muted mb-3 bg-cove-bg p-2 rounded">{command}</pre>
        <div className="flex gap-2">
          <button onClick={() => handleDecision('allow')} className="px-3 py-1 text-sm bg-cove-success text-white rounded hover:opacity-90">
            允许
          </button>
          <button onClick={() => handleDecision('deny')} className="px-3 py-1 text-sm border border-cove-border rounded hover:bg-cove-danger/10 hover:border-cove-danger">
            拒绝
          </button>
          <button onClick={() => handleDecision('always_allow')} className="px-3 py-1 text-sm border border-cove-border rounded hover:bg-cove-accent/10 hover:border-cove-accent">
            始终允许
          </button>
        </div>
      </div>
    </div>
  )
}

export default PermissionCard
