import { describe, it, expect, beforeEach } from 'vitest'
import { act } from 'react'
import { renderHook } from '@testing-library/react'
import { LanguageProvider, useI18n } from './i18n'

function wrapper({ children }: { children: React.ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>
}

describe('i18n', () => {
  beforeEach(() => localStorage.clear())

  it('defaults to Russian and translates a nav key', () => {
    const { result } = renderHook(() => useI18n(), { wrapper })
    expect(result.current.locale).toBe('ru')
    expect(result.current.t('nav.dashboard')).toBe('Дашборд')
  })

  it('switches locale and re-translates', () => {
    const { result } = renderHook(() => useI18n(), { wrapper })
    act(() => result.current.setLocale('en'))
    expect(result.current.t('nav.dashboard')).toBe('Dashboard')
    act(() => result.current.setLocale('uz'))
    expect(result.current.t('nav.products')).toBe('Mahsulotlar')
  })

  it('falls back to the key when missing', () => {
    const { result } = renderHook(() => useI18n(), { wrapper })
    expect(result.current.t('nonexistent.key')).toBe('nonexistent.key')
  })

  it('persists locale to localStorage', () => {
    const { result } = renderHook(() => useI18n(), { wrapper })
    act(() => result.current.setLocale('en'))
    expect(localStorage.getItem('locale')).toBe('en')
  })
})
