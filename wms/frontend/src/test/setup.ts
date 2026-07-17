import '@testing-library/jest-dom'

// jsdom (bu Node/vitest kombinatsiyasida) localStorage bermaydi — oddiy
// in-memory polyfill qo'yamiz, shunda localStorage'ga tayangan kod test'da ishlaydi.
if (typeof globalThis.localStorage === 'undefined') {
  const store = new Map<string, string>()
  const ls = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => { store.set(k, String(v)) },
    removeItem: (k: string) => { store.delete(k) },
    clear: () => { store.clear() },
    key: (i: number) => [...store.keys()][i] ?? null,
    get length() { return store.size },
  }
  Object.defineProperty(globalThis, 'localStorage', { value: ls, configurable: true })
}
