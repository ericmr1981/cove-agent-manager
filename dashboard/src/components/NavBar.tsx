import { useState, type FC } from 'react'
import { useSession } from '../context/SessionContext'
import { useWebSocketContext } from '../context/WebSocketContext'

const NavBar: FC = () => {
  const { state, dispatch } = useSession()
  const { connected, error, sendInterrupt, connectSession } = useWebSocketContext()
  const [creating, setCreating] = useState(false)

  const handleNewSession = async () => {
    setCreating(true)
    try {
      const res = await fetch('/api/v1/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_key: 'dashboard', config: { model: 'sonnet' } }),
      })
      const data = await res.json()
      dispatch({ type: 'RESET' })
      connectSession(data.session_id)
    } catch (e) {
      console.error('Failed to create session', e)
    } finally {
      setCreating(false)
    }
  }

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
        {!connected ? (
          <span className="text-cove-warning flex items-center gap-2">
            ⬤ 断开
            <button
              onClick={handleNewSession}
              disabled={creating}
              className="px-2 py-0.5 text-xs border border-cove-border rounded hover:border-cove-accent"
            >
              {creating ? '连接中...' : '新建会话'}
            </button>
            {error && <span className="text-cove-danger text-xs max-w-[200px] truncate" title={error}>⚠ {error}</span>}
          </span>
        ) : (
          <span className="text-cove-success">⬤ 已连接</span>
        )}
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
        {connected && (
          <button
            onClick={handleNewSession}
            disabled={creating}
            className="px-2 py-0.5 text-xs border border-cove-border rounded hover:border-cove-accent"
          >
            新建会话
          </button>
        )}
      </div>
    </header>
  )
}

export default NavBar
