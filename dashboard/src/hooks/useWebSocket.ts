import { useCallback, useEffect, useRef, useState } from 'react'
import type { WsServerEvent } from '../types/events'

type EventHandler = (event: WsServerEvent) => void

interface UseWebSocketOptions {
  url: string | null
  onEvent: EventHandler
  reconnectDelay?: number
}

export function useWebSocket({ url, onEvent, reconnectDelay = 3000 }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    if (!url) return
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      reconnectTimerRef.current = setTimeout(connect, reconnectDelay)
    }
    ws.onerror = () => ws.close()
    ws.onmessage = (msg) => {
      try {
        const event: WsServerEvent = JSON.parse(msg.data)
        onEvent(event)
      } catch { /* ignore malformed messages */ }
    }
  }, [url, onEvent, reconnectDelay])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, send }
}
