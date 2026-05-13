import { useMemo, type FC } from 'react'
import { useSession } from '../context/SessionContext'
import AgentCardGrid from '../agents/AgentCardGrid'
import MetricsBar from '../agents/MetricsBar'
import SessionTable from '../agents/SessionTable'

const AgentTab: FC = () => {
  const { state } = useSession()

  const activeAgents = useMemo(
    () => state.agentList.filter(a => a.status === 'running').length,
    [state.agentList]
  )
  const completedAgents = useMemo(
    () => state.agentList.filter(a => a.status === 'completed').length,
    [state.agentList]
  )

  return (
    <div className="p-4 h-full overflow-y-auto">
      <h2 className="text-sm font-medium mb-3">Agent 状态</h2>
      <MetricsBar
        activeAgents={activeAgents}
        totalCompleted={completedAgents}
        costUsd={state.costUsd}
        uptime={state.uptime}
      />
      <AgentCardGrid agents={state.agentList} />
      <SessionTable sessions={[]} />
    </div>
  )
}

export default AgentTab
