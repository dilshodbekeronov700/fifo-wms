import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LiveIndicator from './LiveIndicator'

describe('LiveIndicator', () => {
  it('shows "Jonli" when live', () => {
    render(<LiveIndicator status="live" lastEventAt={null} />)
    expect(screen.getByText('Jonli')).toBeInTheDocument()
  })
  it('shows "Ulanmoqda" when connecting', () => {
    render(<LiveIndicator status="connecting" lastEventAt={null} />)
    expect(screen.getByText('Ulanmoqda')).toBeInTheDocument()
  })
  it('shows "Oflayn" when offline', () => {
    render(<LiveIndicator status="offline" lastEventAt={null} />)
    expect(screen.getByText('Oflayn')).toBeInTheDocument()
  })
})
