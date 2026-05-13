import type { FC } from 'react'

interface MetricsBarProps {
  activeAgents: number
  totalCompleted: number
  costUsd: number
  uptime: number
}

const MetricsBar: FC<MetricsBarProps> = ({ activeAgents, totalCompleted, costUsd, uptime }) => {
  const metrics = [
    { label: '活跃 Agent', value: activeAgents.toString() },
    { label: '已完成 Worker', value: totalCompleted.toString() },
    { label: '费用', value: `$${costUsd.toFixed(2)}` },
    { label: '运行时长', value: `${Math.floor(uptime / 60)}m` },
  ]

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      {metrics.map(m => (
        <div key={m.label} className="bg-cove-surface border border-cove-border rounded-lg p-3 text-center">
          <div className="text-xl font-semibold">{m.value}</div>
          <div className="text-xs text-cove-muted mt-1">{m.label}</div>
        </div>
      ))}
    </div>
  )
}

export default MetricsBar
