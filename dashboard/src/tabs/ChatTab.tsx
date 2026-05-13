import { useState, type FC } from 'react'
import { useSession } from '../context/SessionContext'
import { useWebSocketContext } from '../context/WebSocketContext'
import MessageList from '../messages/MessageList'
import SessionSidebar from '../components/SessionSidebar'

const ChatTab: FC = () => {
  const { state } = useSession()
  const { sendMessage, connected } = useWebSocketContext()
  const [input, setInput] = useState('')

  const handleSend = () => {
    const text = input.trim()
    if (!text) return
    sendMessage(text)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
        <MessageList messages={state.messages} />
        <div className="border-t border-cove-border p-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={connected ? '输入消息...' : 'WebSocket 未连接...'}
              disabled={!connected}
              className="flex-1 bg-cove-bg border border-cove-border rounded-lg px-3 py-2 text-sm text-cove-text placeholder-cove-muted focus:outline-none focus:border-cove-accent disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!connected || !input.trim()}
              className="px-4 py-2 bg-cove-accent text-white rounded-lg text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              发送
            </button>
          </div>
        </div>
      </div>
      <SessionSidebar />
    </div>
  )
}

export default ChatTab
