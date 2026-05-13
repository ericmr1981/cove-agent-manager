import type { FC } from 'react'
import type { ChatMessage } from '../types/session'
import UserMessage from './UserMessage'
import AssistantMessage from './AssistantMessage'
import ThinkingBlock from './ThinkingBlock'
import ToolCallBlock from './ToolCallBlock'
import ToolResultBlock from './ToolResultBlock'
import ToolErrorBlock from './ToolErrorBlock'
import SystemMessage from './SystemMessage'
import CompactionNotice from './CompactionNotice'

interface MessageItemProps {
  message: ChatMessage
}

const renderers: Record<string, FC<{ data: Record<string, unknown>; agentId?: string }>> = {
  user_message: UserMessage,
  assistant_message: AssistantMessage,
  assistant_thinking: ThinkingBlock,
  tool_use: ToolCallBlock,
  tool_result: ToolResultBlock,
  tool_error: ToolErrorBlock,
  system: SystemMessage,
  compaction: CompactionNotice,
}

const MessageItem: FC<MessageItemProps> = ({ message }) => {
  const Renderer = renderers[message.kind]
  if (!Renderer) return null

  return (
    <div className="py-2">
      <Renderer data={message.data} agentId={message.agentId} />
    </div>
  )
}

export default MessageItem
