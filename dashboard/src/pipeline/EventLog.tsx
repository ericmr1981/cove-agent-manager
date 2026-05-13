import { useEffect, useRef, type FC } from 'react'

export interface LogEntry {
  id: string
  time: string
  direction: 'in' | 'out' | 'error' | 'retry'
  message: string
}

interface EventLogProps {
  entries: LogEntry[]
}

const DIR_ICONS = {
  in: '←',
  out: '→',
  error: '!',
  retry: '↻',
}

const DIR_COLORS = {
  in: 'text-cove-accent',
  out: 'text-cove-success',
  error: 'text-cove-danger',
  retry: 'text-cove-warning',
}

const EventLog: FC<EventLogProps> = ({ entries }) => {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries.length])

  return (
    <div className="bg-cove-bg border border-cove-border rounded-lg mt-3">
      <div className="px-3 py-2 border-b border-cove-border text-xs text-cove-muted font-medium">
        事件日志
      </div>
      <div className="max-h-40 overflow-y-auto p-2 font-mono text-xs" role="log" aria-live="polite" tabIndex={0}>
        {entries.length === 0 && (
          <div className="text-cove-muted text-center py-4">暂无事件</div>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className="flex gap-2 py-0.5">
            <span className="text-cove-muted flex-shrink-0 w-14">{entry.time}</span>
            <span className={`flex-shrink-0 ${DIR_COLORS[entry.direction]}`}>{DIR_ICONS[entry.direction]}</span>
            <span className={entry.direction === 'error' ? 'text-cove-danger' : 'text-cove-text'}>
              {entry.message}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

export default EventLog
