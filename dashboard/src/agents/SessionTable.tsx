import type { FC } from 'react'

interface SessionRow {
  id: string
  project: string
  agents: string
  status: 'running' | 'completed' | 'failed'
  tokens: number
  uptime: string
}

interface SessionTableProps {
  sessions: SessionRow[]
}

const STATUS_DOTS: Record<string, string> = {
  running: 'bg-cove-success',
  completed: 'bg-cove-muted',
  failed: 'bg-cove-danger',
}

const SessionTable: FC<SessionTableProps> = ({ sessions }) => {
  return (
    <div className="bg-cove-bg border border-cove-border rounded-lg overflow-x-auto mt-4">
      <div className="px-3 py-2 border-b border-cove-border text-xs text-cove-muted font-medium">
        所有 Session
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-cove-border text-xs text-cove-muted">
            <th className="text-left px-3 py-2 font-medium">Session ID</th>
            <th className="text-left px-3 py-2 font-medium">项目</th>
            <th className="text-left px-3 py-2 font-medium">Agent</th>
            <th className="text-left px-3 py-2 font-medium">状态</th>
            <th className="text-right px-3 py-2 font-medium">Tokens</th>
            <th className="text-right px-3 py-2 font-medium">耗时</th>
          </tr>
        </thead>
        <tbody>
          {sessions.length === 0 && (
            <tr>
              <td colSpan={6} className="text-center py-8 text-cove-muted text-xs">
                暂无 Session 记录
              </td>
            </tr>
          )}
          {sessions.map(s => (
            <tr key={s.id} className="border-b border-cove-border hover:bg-cove-surface/50">
              <td className="px-3 py-2 font-mono text-xs">{s.id}</td>
              <td className="px-3 py-2">{s.project}</td>
              <td className="px-3 py-2 text-xs text-cove-muted">{s.agents}</td>
              <td className="px-3 py-2">
                <span className={`inline-flex items-center gap-1 text-xs`}>
                  <span className={`w-2 h-2 rounded-full ${STATUS_DOTS[s.status] || 'bg-cove-muted'}`} />
                  {s.status}
                </span>
              </td>
              <td className="px-3 py-2 text-right">{s.tokens.toLocaleString()}</td>
              <td className="px-3 py-2 text-right">{s.uptime}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default SessionTable
