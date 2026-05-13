import type { EventKind } from './events';

export interface PendingPermission {
  requestId: string;
  tool: string;
  command: string;
}

export interface SessionState {
  sessionId: string | null;
  status: 'idle' | 'ready' | 'running' | 'completed' | 'failed';
  model: string;
  tokenUsage: number;
  tokenLimit: number;
  costUsd: number;
  uptime: number;
  permissionMode: string;
  sandboxImage: string;
  sandboxStatus: string;
  tools: string[];
  agentList: AgentInfo[];
  messages: ChatMessage[];
  pendingPermission: PendingPermission | null;
}

export interface ChatMessage {
  uuid: string;
  kind: EventKind;
  agentId?: string;
  agentLabel?: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface AgentInfo {
  id: string;
  label: string;
  type: 'planner' | 'worker' | 'reviewer';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'retrying';
  progress: number;
  model: string;
  capability?: string;
  error?: string;
  uptime_seconds?: number;
}

export type TabId = 'chat' | 'pipeline' | 'agents' | 'settings';
