import type { FC } from 'react'
import type { AgentInfo } from '../types/session'
import AgentCard from './AgentCard'

interface AgentCardGridProps {
  agents: AgentInfo[]
}

const AgentCardGrid: FC<AgentCardGridProps> = ({ agents }) => {
  if (agents.length === 0) {
    return (
      <div className="text-center py-8 text-cove-muted text-sm">
        暂无 Agent 数据。创建 Session 后自动出现。
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {agents.map(agent => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}

export default AgentCardGrid
