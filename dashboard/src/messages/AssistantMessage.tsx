import type { FC } from 'react'
import Markdown from 'react-markdown'

interface AssistantMessageProps {
  data: Record<string, unknown>
  agentId?: string
}

const AssistantMessage: FC<AssistantMessageProps> = ({ data, agentId }) => {
  const content = data.content as string || ''
  const model = (data.model as string) || (agentId ? '' : 'Sonnet')

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cove-success/20 flex items-center justify-center text-sm">
        🤖
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-cove-accent mb-1">
          {agentId || 'Cove'} {model ? `· ${model}` : ''}
        </div>
        <div className="bg-cove-bg border border-cove-border rounded-lg p-3">
          <Markdown>{content}</Markdown>
        </div>
      </div>
    </div>
  )
}

export default AssistantMessage
