import { useState, useMemo, type FC } from 'react'
import { useSession } from '../context/SessionContext'
import PipelineDAG from '../pipeline/PipelineDAG'
import EventLog from '../pipeline/EventLog'
import type { PipelineNode, PipelineEdge } from '../types/pipeline'
import type { LogEntry } from '../pipeline/EventLog'

function buildPipeline(
  agents: ReturnType<typeof useSession>['state']['agentList']
): { nodes: PipelineNode[]; edges: PipelineEdge[]; logs: LogEntry[] } {
  const nodes: PipelineNode[] = []
  const edges: PipelineEdge[] = []
  const logs: LogEntry[] = []

  const planner = agents.find(a => a.type === 'planner')
  const workers = agents.filter(a => a.type === 'worker')
  const reviewers = agents.filter(a => a.type === 'reviewer')

  if (!planner && workers.length === 0) return { nodes, edges, logs }

  if (planner) {
    nodes.push({
      id: planner.id,
      type: 'pipelineNode',
      position: { x: 250, y: 0 },
      data: {
        label: planner.id,
        type: 'planner',
        status: planner.status,
        progress: planner.progress,
        model: planner.model,
      },
    })
    logs.push({ id: `${planner.id}-decompose`, time: '--:--:--', direction: 'in', message: `${planner.id}: 任务分解中` })

    workers.forEach((w) => {
      edges.push({ id: `${planner.id}->${w.id}`, source: planner.id, target: w.id })
      logs.push({ id: `${w.id}-created`, time: '--:--:--', direction: 'out', message: `${w.id} 已创建 (${w.capability || 'N/A'})` })
    })
  }

  workers.forEach((w, i) => {
    const col = i - (workers.length - 1) / 2
    nodes.push({
      id: w.id,
      type: 'pipelineNode',
      position: { x: 250 + col * 200, y: 150 },
      data: {
        label: w.id,
        type: 'worker',
        status: w.status,
        progress: w.progress,
        model: w.model,
        capability: w.capability,
        error: w.error,
      },
    })

    if (w.status === 'failed') {
      logs.push({ id: `${w.id}-error`, time: '--:--:--', direction: 'error', message: `${w.id} 失败: ${w.error || ''}` })
    } else if (w.status === 'retrying') {
      logs.push({ id: `${w.id}-retry`, time: '--:--:--', direction: 'retry', message: `${w.id} 正在重试` })
    }
  })

  if (reviewers.length > 0) {
    const reviewer = reviewers[0]
    nodes.push({
      id: reviewer.id,
      type: 'pipelineNode',
      position: { x: 250, y: 300 },
      data: {
        label: reviewer.id,
        type: 'reviewer',
        status: reviewer.status,
        progress: reviewer.progress,
        model: reviewer.model,
      },
    })
    workers.forEach(w => edges.push({ id: `${w.id}->${reviewer.id}`, source: w.id, target: reviewer.id }))
  }

  return { nodes, edges, logs }
}

const PipelineTab: FC = () => {
  const { state } = useSession()
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const { nodes, edges, logs } = useMemo(
    () => buildPipeline(state.agentList),
    [state.agentList]
  )

  return (
    <div className="p-4 h-full overflow-y-auto">
      <h2 className="text-sm font-medium mb-3">任务管线</h2>
      <PipelineDAG nodes={nodes} edges={edges} onNodeClick={setSelectedNode} />
      {selectedNode && (
        <div className="mt-2 text-xs text-cove-muted">
          选中: {selectedNode}
        </div>
      )}
      <EventLog entries={logs} />
    </div>
  )
}

export default PipelineTab
