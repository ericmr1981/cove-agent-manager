import { memo, type FC } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { PipelineNodeData } from '../types/pipeline'

const STATUS_COLORS: Record<string, string> = {
  pending: '#30363d',
  running: '#58a6ff',
  completed: '#3fb950',
  failed: '#f85149',
  retrying: '#d29922',
  skipped: '#8b949e',
}

const STATUS_LABELS: Record<string, string> = {
  pending: '排队中',
  running: '运行中',
  completed: '完成',
  failed: '失败',
  retrying: '重试中',
  skipped: '跳过',
}

const NODE_EMOJIS: Record<string, string> = {
  planner: '🧠',
  worker: '🔧',
  reviewer: '👁️',
}

const PipelineNode: FC<NodeProps<PipelineNodeData>> = ({ data }) => {
  const color = STATUS_COLORS[data.status] || STATUS_COLORS.pending
  const borderStyle = data.status === 'pending' ? 'dashed' : 'solid'

  return (
    <div
      className="bg-cove-bg border-2 rounded-lg p-3 min-w-[140px]"
      style={{ borderColor: color, borderStyle }}
    >
      <Handle type="target" position={Position.Top} className="!bg-cove-border" />
      <div className="text-center">
        <div className="text-lg mb-1" aria-hidden="true">{NODE_EMOJIS[data.type] || '?'}</div>
        <div className="text-sm font-medium">{data.label}</div>
        <div className="text-xs text-cove-muted mt-1">{data.capability || ''}</div>
        {data.model && <div className="text-xs text-cove-muted">{data.model}</div>}
        {data.status !== 'pending' && (
          <div className="mt-2 h-1 bg-cove-border rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all" style={{ width: `${data.progress * 100}%`, backgroundColor: color }} />
          </div>
        )}
        <div className="text-xs mt-1" style={{ color }}>{STATUS_LABELS[data.status]}</div>
        {data.error && <div className="text-xs text-cove-danger mt-1">⚠️ {data.error}</div>}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-cove-border" />
    </div>
  )
}

export default memo(PipelineNode)
