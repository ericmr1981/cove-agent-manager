import { useState, type FC } from 'react'

interface ThinkingBlockProps {
  data: Record<string, unknown>
}

const ThinkingBlock: FC<ThinkingBlockProps> = ({ data }) => {
  const [expanded, setExpanded] = useState(false)
  const content = data.content as string || ''
  const signature = data.signature as string

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8" />
      <div className="flex-1">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm text-cove-muted hover:text-cove-text transition-colors"
        >
          <span>{expanded ? '▼' : '▶'} 正在思考...</span>
          {signature && <span className="text-xs text-cove-muted">· 签名: {signature.slice(0, 16)}...</span>}
        </button>
        {expanded && (
          <div className="mt-2 p-3 bg-cove-bg border border-cove-border rounded-lg text-sm text-cove-muted whitespace-pre-wrap">
            {content}
          </div>
        )}
      </div>
    </div>
  )
}

export default ThinkingBlock
