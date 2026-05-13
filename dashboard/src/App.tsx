import { useState, type FC } from 'react'
import { SessionProvider } from './context/SessionContext'
import { WebSocketProvider } from './context/WebSocketContext'
import TabBar from './components/TabBar'
import NavBar from './components/NavBar'
import ChatTab from './tabs/ChatTab'
import PipelineTab from './tabs/PipelineTab'
import AgentTab from './tabs/AgentTab'
import SettingsTab from './tabs/SettingsTab'
import type { TabId } from './types/session'

const TAB_COMPONENTS: Record<TabId, FC> = {
  chat: ChatTab,
  pipeline: PipelineTab,
  agents: AgentTab,
  settings: SettingsTab,
}

const TAB_LABELS: Record<TabId, string> = {
  chat: '💬 对话',
  pipeline: '📋 任务管线',
  agents: '🤖 Agent 状态',
  settings: '⚙️ 设置',
}

const AppContent: FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('chat')

  const TabComponent = TAB_COMPONENTS[activeTab]

  return (
    <>
      <div className="flex flex-col h-screen bg-cove-bg">
        <NavBar />
        <TabBar
          tabs={TAB_LABELS}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
        <main className="flex-1 overflow-hidden">
          <TabComponent />
        </main>
      </div>
    </>
  )
}

const App: FC = () => {
  return (
    <SessionProvider>
      <WebSocketProvider>
        <AppContent />
      </WebSocketProvider>
    </SessionProvider>
  )
}

export default App
