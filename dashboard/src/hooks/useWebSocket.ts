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
  const [error, setError] = useState<string | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const retryCountRef = useRef(0)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!url || !mountedRef.current) return

    // Close existing socket
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.close()
    }

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) { ws.close(); return }
      setConnected(true)
      setError(null)
      retryCountRef.current = 0
    }

    ws.onclose = (e) => {
      if (!mountedRef.current) return
      setConnected(false)
      wsRef.current = null
      if (e.code !== 1000) {
        const msg = `WS 断开 (code=${e.code}${e.reason ? ` reason=${e.reason}` : ''})`
        setError(msg)
        console.warn('[WS]', msg)
      }
      // Exponential backoff: 1s, 2s, 4s, 8s... max 30s
      const delay = Math.min(reconnectDelay * Math.pow(2, retryCountRef.current), 30000)
      retryCountRef.current++
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      const msg = `WS 连接失败: ${url.slice(0, 60)}...`
      setError(msg)
      console.error('[WS]', msg)
      ws.close()
    }

    ws.onmessage = (msg) => {
      try {
        const event: WsServerEvent = JSON.parse(msg.data)
        onEvent(event)
      } catch (e) {
        console.warn('[WS] malformed message', e)
      }
    }
  }, [url, onEvent, reconnectDelay])

  useEffect(() => {
    mountedRef.current = true
    retryCountRef.current = 0
    setError(null)
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.warn('[WS] cannot send, not connected', data)
    }
  }, [])

  return { connected, error, send }
}
