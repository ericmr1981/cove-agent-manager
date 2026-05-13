import type { FC } from 'react'

interface CompactionNoticeProps {
  data: Record<string, unknown>
}

const CompactionNotice: FC<CompactionNoticeProps> = ({ data }) => {
  const count = data.compacted_count as number || data.compacted_uuids_len as number || 0

  return (
    <div className="flex justify-center py-1">
      <span className="px-3 py-1 text-xs text-cove-warning bg-cove-warning/10 border border-cove-warning/20 rounded-full">
        上下文已压缩 · {count} 条事件
      </span>
    </div>
  )
}

export default CompactionNotice
