import { useState, type FC } from 'react'
import SessionConfigForm from '../settings/SessionConfigForm'
import ModelConfigForm from '../settings/ModelConfigForm'

type SettingsSection = 'model' | 'session'

const SettingsTab: FC = () => {
  const [section, setSection] = useState<SettingsSection>('model')

  return (
    <div className="p-4 h-full overflow-y-auto">
      <h2 className="text-sm font-medium mb-3">⚙️ 设置</h2>
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setSection('model')}
          className={`px-3 py-1.5 text-xs rounded-lg ${section === 'model' ? 'bg-cove-accent text-white' : 'bg-cove-surface border border-cove-border'}`}
        >
          模型配置
        </button>
        <button
          onClick={() => setSection('session')}
          className={`px-3 py-1.5 text-xs rounded-lg ${section === 'session' ? 'bg-cove-accent text-white' : 'bg-cove-surface border border-cove-border'}`}
        >
          Session 配置
        </button>
      </div>
      {section === 'model' ? <ModelConfigForm /> : <SessionConfigForm />}
    </div>
  )
}

export default SettingsTab
