import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from './ErrorBoundary'

function Boom(): React.ReactElement {
  throw new Error('kaboom')
}

describe('ErrorBoundary', () => {
  beforeEach(() => vi.spyOn(console, 'error').mockImplementation(() => {}))
  afterEach(() => vi.restoreAllMocks())

  it('renders children when there is no error', () => {
    render(<ErrorBoundary><div>ok-child</div></ErrorBoundary>)
    expect(screen.getByText('ok-child')).toBeInTheDocument()
  })

  it('shows the fallback when a child throws', () => {
    render(<ErrorBoundary><Boom /></ErrorBoundary>)
    expect(screen.getByText(/Nimadir noto'g'ri ketdi/)).toBeInTheDocument()
    expect(screen.getByText(/kaboom/)).toBeInTheDocument()
  })
})
