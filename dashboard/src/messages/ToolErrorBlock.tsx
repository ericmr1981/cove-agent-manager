import type { FC } from 'react'

interface ToolErrorBlockProps {
  data: Record<string, unknown>
}

const ToolErrorBlock: FC<ToolErrorBlockProps> = ({ data }) => {
  const error = data.error as string || data.content as string || 'Unknown error'

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8" />
      <div className="flex-1">
        <div className="bg-cove-danger/10 border border-cove-danger/30 rounded-lg p-3">
          <div className="text-xs text-cove-danger mb-1">Error</div>
          <pre className="text-sm text-cove-text whitespace-pre-wrap">{error}</pre>
        </div>
      </div>
    </div>
  )
}

export default ToolErrorBlock
