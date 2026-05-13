import type { FC } from 'react'

interface SystemMessageProps {
  data: Record<string, unknown>
}

const SystemMessage: FC<SystemMessageProps> = ({ data }) => {
  const content = data.content as string || data.message as string || ''

  return (
    <div className="flex justify-center py-1">
      <span className="px-3 py-1 text-xs text-cove-muted bg-cove-surface rounded-full">{content}</span>
    </div>
  )
}

export default SystemMessage
