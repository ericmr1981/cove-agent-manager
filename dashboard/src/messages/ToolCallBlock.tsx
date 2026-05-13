import type { FC } from 'react'

interface ToolCallBlockProps {
  data: Record<string, unknown>
}

const ToolCallBlock: FC<ToolCallBlockProps> = ({ data }) => {
  const name = data.name as string || ''
  const input = data.input as Record<string, unknown> || {}

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8" />
      <div className="flex-1">
        <div className="bg-cove-bg border border-cove-border rounded-lg overflow-hidden">
          <div className="px-3 py-1.5 bg-cove-surface border-b border-cove-border text-xs text-cove-muted font-mono">
            {name}
          </div>
          <pre className="p-3 text-sm overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(input, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}

export default ToolCallBlock
