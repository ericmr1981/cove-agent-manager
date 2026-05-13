import type { FC } from 'react'
import type { TabId } from '../types/session'

interface TabBarProps {
  tabs: Record<TabId, string>
  activeTab: TabId
  onTabChange: (tab: TabId) => void
}

const TabBar: FC<TabBarProps> = ({ tabs, activeTab, onTabChange }) => {
  return (
    <nav className="flex border-b border-cove-border bg-cove-surface px-2">
      {(Object.entries(tabs) as [TabId, string][]).map(([id, label]) => (
        <button
          key={id}
          onClick={() => onTabChange(id)}
          className={`px-4 py-2 text-sm border-b-2 transition-colors ${
            activeTab === id
              ? 'border-cove-accent text-white'
              : 'border-transparent text-cove-muted hover:text-cove-text'
          }`}
        >
          {label}
        </button>
      ))}
    </nav>
  )
}

export default TabBar
