import { useState, type FC } from 'react'

interface ToolResultBlockProps {
  data: Record<string, unknown>
}

const MAX_PREVIEW_LENGTH = 500

const ToolResultBlock: FC<ToolResultBlockProps> = ({ data }) => {
  const [expanded, setExpanded] = useState(false)
  const content = data.content as string || ''
  const isLong = content.length > MAX_PREVIEW_LENGTH
  const display = isLong && !expanded ? content.slice(0, MAX_PREVIEW_LENGTH) + '...' : content

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8" />
      <div className="flex-1">
        <div className="bg-cove-bg border border-cove-border rounded-lg p-3">
          <pre className="text-sm text-cove-text overflow-x-auto whitespace-pre-wrap">{display}</pre>
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 text-xs text-cove-accent hover:underline"
            >
              {expanded ? '收起' : '展开全部'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default ToolResultBlock
