import type { FC } from 'react'
import SessionConfigForm from '../settings/SessionConfigForm'

const SettingsTab: FC = () => {
  return (
    <div className="p-4 h-full overflow-y-auto">
      <h2 className="text-sm font-medium mb-3">⚙️ 设置</h2>
      <SessionConfigForm />
    </div>
  )
}

export default SettingsTab
