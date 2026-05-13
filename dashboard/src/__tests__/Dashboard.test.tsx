import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

describe('Cove Console', () => {
  it('renders the Cove brand in the navbar', () => {
    render(<App />)
    expect(screen.getByText('Cove')).toBeDefined()
  })

  it('renders all four tabs', () => {
    render(<App />)
    expect(screen.getAllByText('💬 对话').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('📋 任务管线').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('🤖 Agent 状态').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('⚙️ 设置').length).toBeGreaterThanOrEqual(1)
  })

  it('shows chat tab by default', () => {
    render(<App />)
    expect(screen.getAllByPlaceholderText(/WebSocket 未连接/).length).toBeGreaterThanOrEqual(1)
  })
})
