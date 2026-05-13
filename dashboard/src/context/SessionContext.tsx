import { createContext, useContext, useReducer, type Dispatch, type FC, type ReactNode } from 'react'
import type { SessionState, ChatMessage, AgentInfo } from '../types/session'

export type SessionAction =
  | { type: 'SET_SESSION_ID'; id: string }
  | { type: 'SET_STATUS'; status: SessionState['status'] }
  | { type: 'ADD_MESSAGE'; message: ChatMessage }
  | { type: 'UPDATE_AGENT'; agent: AgentInfo }
  | { type: 'REMOVE_AGENT'; agentId: string }
  | { type: 'SET_TOKEN_USAGE'; used: number; limit: number }
  | { type: 'SET_COST'; cost: number }
  | { type: 'SET_UPTIME'; uptime: number }
  | { type: 'SET_METRICS'; cost: number; uptime: number; tokens: number; tokenLimit: number }
  | { type: 'RESET' }

const initialState: SessionState = {
  sessionId: null,
  status: 'idle',
  model: 'claude-sonnet-4-5',
  tokenUsage: 0,
  tokenLimit: 10000,
  costUsd: 0,
  uptime: 0,
  permissionMode: 'acceptEdits',
  sandboxImage: 'cove/sandbox:python-3.12',
  sandboxStatus: 'unknown',
  tools: [],
  agentList: [],
  messages: [],
}

function sessionReducer(state: SessionState, action: SessionAction): SessionState {
  switch (action.type) {
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.id }
    case 'SET_STATUS':
      return { ...state, status: action.status }
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.message] }
    case 'UPDATE_AGENT': {
      const exists = state.agentList.findIndex(a => a.id === action.agent.id)
      if (exists >= 0) {
        const updated = [...state.agentList]
        updated[exists] = action.agent
        return { ...state, agentList: updated }
      }
      return { ...state, agentList: [...state.agentList, action.agent] }
    }
    case 'REMOVE_AGENT':
      return { ...state, agentList: state.agentList.filter(a => a.id !== action.agentId) }
    case 'SET_TOKEN_USAGE':
      return { ...state, tokenUsage: action.used, tokenLimit: action.limit }
    case 'SET_COST':
      return { ...state, costUsd: action.cost }
    case 'SET_UPTIME':
      return { ...state, uptime: action.uptime }
    case 'SET_METRICS':
      return { ...state, tokenUsage: action.tokens, tokenLimit: action.tokenLimit, costUsd: action.cost, uptime: action.uptime }
    case 'RESET':
      return initialState
    default:
      return state
  }
}

const SessionContext = createContext<{ state: SessionState; dispatch: Dispatch<SessionAction> } | null>(null)

export const SessionProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(sessionReducer, initialState)
  return (
    <SessionContext.Provider value={{ state, dispatch }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within SessionProvider')
  return ctx
}
