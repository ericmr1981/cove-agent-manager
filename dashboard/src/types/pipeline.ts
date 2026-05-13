import type { Node, Edge } from '@xyflow/react';

export interface PipelineNodeData {
  label: string;
  type: 'planner' | 'worker' | 'reviewer';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'retrying' | 'skipped';
  progress: number;
  model?: string;
  capability?: string;
  error?: string;
  [key: string]: unknown;
}

export type PipelineNode = Node<PipelineNodeData>;
export type PipelineEdge = Edge;
