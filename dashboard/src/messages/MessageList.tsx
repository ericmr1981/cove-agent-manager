import { useEffect, useRef, type FC } from 'react'
import type { ChatMessage } from '../types/session'
import MessageItem from './MessageItem'

interface MessageListProps {
  messages: ChatMessage[]
}

const MessageList: FC<MessageListProps> = ({ messages }) => {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-2">
      {messages.map(msg => (
        <MessageItem key={msg.uuid} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

export default MessageList
