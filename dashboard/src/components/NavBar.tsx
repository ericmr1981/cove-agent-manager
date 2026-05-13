import type { FC } from 'react'
import { useSession } from '../context/SessionContext'
import { useWebSocketContext } from '../context/WebSocketContext'

const NavBar: FC = () => {
  const { state } = useSession()
  const { connected, sendInterrupt } = useWebSocketContext()

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-cove-border bg-cove-surface">
      <div className="flex items-center gap-3">
        <span className="font-bold text-lg">Cove</span>
        {state.sessionId && (
          <>
            <span className="text-cove-muted text-sm font-mono">{state.sessionId.slice(0, 8)}</span>
            <span className={`w-2 h-2 rounded-full ${state.status === 'running' ? 'bg-cove-success' : state.status === 'failed' ? 'bg-cove-danger' : 'bg-cove-muted'}`} />
            <span className="text-xs text-cove-muted">{state.status}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-4 text-sm">
        {!connected && <span className="text-cove-warning">⬤ 断开</span>}
        {state.tokenLimit > 0 && (
          <span className="text-cove-muted">
            Tokens: {state.tokenUsage.toLocaleString()} / {state.tokenLimit.toLocaleString()}
          </span>
        )}
        {state.costUsd > 0 && (
          <span className="text-cove-muted">${state.costUsd.toFixed(2)}</span>
        )}
        {state.status === 'running' && (
          <button onClick={sendInterrupt} className="px-3 py-1 text-sm border border-cove-border rounded hover:bg-cove-danger/10 hover:border-cove-danger text-cove-muted hover:text-cove-danger">
            中断
          </button>
        )}
      </div>
    </header>
  )
}

export default NavBar
