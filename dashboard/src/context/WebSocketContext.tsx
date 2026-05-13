import { createContext, useContext, useCallback, useState, type Dispatch, type FC, type ReactNode } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { useSession, type SessionAction } from './SessionContext'
import type { WsServerEvent, WsClientMessage } from '../types/events'
import type { ChatMessage, AgentInfo, SessionState } from '../types/session'

const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/sessions`

interface WebSocketContextValue {
  connected: boolean
  connectSession: (sessionId: string) => void
  sendMessage: (content: string) => void
  sendPermissionResponse: (requestId: string, decision: 'allow' | 'deny' | 'always_allow') => void
  sendInterrupt: () => void
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null)

function eventToMessage(event: WsServerEvent, dispatch: Dispatch<SessionAction>) {
  if (event.type === 'event' && 'kind' in event.event) {
    const msg: ChatMessage = {
      uuid: event.event.uuid,
      kind: event.event.kind,
      agentId: event.event.agent_id,
      timestamp: event.event.timestamp,
      data: event.event.data,
    }
    dispatch({ type: 'ADD_MESSAGE', message: msg })
  } else if (event.type === 'agent_status') {
    const agent: AgentInfo = {
      id: event.agent_id,
      label: event.agent_id,
      type: event.agent_id.startsWith('planner') ? 'planner' : 'worker',
      status: event.status,
      progress: event.progress,
      model: event.model || 'unknown',
      uptime_seconds: event.uptime_seconds,
    }
    dispatch({ type: 'UPDATE_AGENT', agent })
  } else if (event.type === 'metrics_snapshot') {
    dispatch({
      type: 'SET_METRICS',
      cost: event.cost_usd,
      uptime: event.uptime,
      tokens: event.tokens_used,
      tokenLimit: event.token_limit,
    })
  } else if (event.type === 'session_status') {
    dispatch({ type: 'SET_STATUS', status: event.status as SessionState['status'] })
  }
}

export const WebSocketProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const { dispatch } = useSession()
  const [wsUrl, setWsUrl] = useState<string | null>(null)

  const onEvent = useCallback((event: WsServerEvent) => {
    eventToMessage(event, dispatch)
  }, [dispatch])

  const { connected, send } = useWebSocket({ url: wsUrl, onEvent })

  const connectSession = useCallback((sessionId: string) => {
    dispatch({ type: 'SET_SESSION_ID', id: sessionId })
    setWsUrl(`${WS_BASE}/${sessionId}/stream`)
  }, [dispatch])

  const sendMessage = useCallback((content: string) => {
    const msg: WsClientMessage = { type: 'user_message', content, id: crypto.randomUUID() }
    send(msg)
  }, [send])

  const sendPermissionResponse = useCallback((requestId: string, decision: 'allow' | 'deny' | 'always_allow') => {
    send({ type: 'permission_response', request_id: requestId, decision })
  }, [send])

  const sendInterrupt = useCallback(() => {
    send({ type: 'interrupt' })
  }, [send])

  return (
    <WebSocketContext.Provider value={{ connected, connectSession, sendMessage, sendPermissionResponse, sendInterrupt }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocketContext() {
  const ctx = useContext(WebSocketContext)
  if (!ctx) throw new Error('useWebSocketContext must be used within WebSocketProvider')
  return ctx
}
