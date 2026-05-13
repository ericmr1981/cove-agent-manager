export type EventKind =
  | 'user_message'
  | 'assistant_message'
  | 'assistant_thinking'
  | 'tool_use'
  | 'tool_result'
  | 'tool_error'
  | 'system'
  | 'permission_request'
  | 'permission_decision'
  | 'compaction'
  | 'checkpoint'
  | 'agent_status'
  | 'pipeline_update'
  | 'worker_progress'
  | 'metrics_snapshot';

export interface SessionEvent {
  type: 'event';
  event: {
    kind: EventKind;
    data: Record<string, unknown>;
    uuid: string;
    timestamp: string;
    agent_id?: string;
  };
}

export interface PermissionRequest {
  type: 'permission_request';
  tool: string;
  command: string;
  request_id: string;
}

export interface PermissionResponse {
  type: 'permission_response';
  request_id: string;
  decision: 'allow' | 'deny' | 'always_allow';
}

export interface AgentStatusEvent {
  type: 'agent_status';
  agent_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'retrying';
  progress: number;
  current_tool?: string;
  model?: string;
  uptime_seconds?: number;
}

export interface PipelineUpdateEvent {
  type: 'pipeline_update';
  dag: {
    nodes: Array<{ id: string; label: string; type: string; status: string; progress: number; model?: string }>;
    edges: Array<{ source: string; target: string }>;
  };
}

export interface WorkerProgressEvent {
  type: 'worker_progress';
  worker_id: string;
  progress: number;
  message: string;
}

export interface MetricsSnapshotEvent {
  type: 'metrics_snapshot';
  active_agents: number;
  total_completed: number;
  cost_usd: number;
  uptime: number;
  tokens_used: number;
  token_limit: number;
}

export type WsServerEvent =
  | SessionEvent
  | PermissionRequest
  | AgentStatusEvent
  | PipelineUpdateEvent
  | WorkerProgressEvent
  | MetricsSnapshotEvent
  | { type: 'session_status'; status: string; stats?: Record<string, unknown> }
  | { type: 'error'; code: string; message: string };

export type WsClientMessage =
  | { type: 'user_message'; content: string; id: string }
  | { type: 'interrupt' }
  | { type: 'permission_response'; request_id: string; decision: 'allow' | 'deny' | 'always_allow' }
  | { type: 'set_permission_mode'; mode: string };
