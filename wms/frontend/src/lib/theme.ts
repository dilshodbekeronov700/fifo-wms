import { create } from 'zustand'

type Theme = 'light' | 'dark'

function apply(t: Theme) {
  document.documentElement.classList.toggle('dark', t === 'dark')
}

const stored = (localStorage.getItem('theme') as Theme | null)
const initial: Theme = stored
  ?? (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')

// Apply before first paint (module is imported in App entry).
apply(initial)

export const useTheme = create<{ theme: Theme; toggle: () => void }>((set, get) => ({
  theme: initial,
  toggle: () => {
    const t: Theme = get().theme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', t)
    apply(t)
    set({ theme: t })
  },
}))
