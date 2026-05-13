import type { FC } from 'react'
import Markdown from 'react-markdown'

interface UserMessageProps {
  data: Record<string, unknown>
}

const UserMessage: FC<UserMessageProps> = ({ data }) => {
  const content = data.content as string || ''

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cove-accent/20 flex items-center justify-center text-sm font-bold text-cove-accent">
        U
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-cove-muted mb-1">You</div>
        <div className="bg-cove-surface border border-cove-border rounded-lg p-3">
          <Markdown>{content}</Markdown>
        </div>
      </div>
    </div>
  )
}

export default UserMessage
