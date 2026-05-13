import { useCallback, type FC } from 'react'
import { ReactFlow, Background, Controls, MiniMap, type NodeTypes } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { PipelineNode, PipelineEdge } from '../types/pipeline'
import PipelineNodeComponent from './PipelineNode'

const nodeTypes: NodeTypes = {
  pipelineNode: PipelineNodeComponent,
}

interface PipelineDAGProps {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  onNodeClick?: (nodeId: string) => void
}

const PipelineDAG: FC<PipelineDAGProps> = ({ nodes, edges, onNodeClick }) => {
  const onNodeClickHandler = useCallback((_event: React.MouseEvent, node: PipelineNode) => {
    onNodeClick?.(node.id)
  }, [onNodeClick])

  return (
    <div className="h-80 border border-cove-border rounded-lg overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClickHandler}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        defaultEdgeOptions={{
          style: { stroke: '#30363d', strokeWidth: 2 },
          type: 'smoothstep',
        }}
      >
        <Background color="#30363d" gap={16} />
        <Controls />
        <MiniMap
          nodeStrokeColor="#30363d"
          nodeColor="#161b22"
          maskColor="rgba(13,17,23,0.7)"
        />
      </ReactFlow>
    </div>
  )
}

export default PipelineDAG
