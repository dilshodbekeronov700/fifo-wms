import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type Locale = 'ru' | 'uz' | 'en'
const LOCALES: Locale[] = ['ru', 'uz', 'en']

// Translation dictionary. Add keys as the UI is localised; missing keys fall
// back to the key itself, so nothing breaks if a string isn't translated yet.
const DICT: Record<string, Record<Locale, string>> = {
  // Navigatsiya
  'nav.dashboard': { ru: 'Дашборд', uz: 'Boshqaruv paneli', en: 'Dashboard' },
  'nav.sklad': { ru: 'Склад', uz: 'Sklad', en: 'Warehouse' },
  'nav.zones': { ru: 'Зоны', uz: 'Zonalar', en: 'Zones' },
  'nav.products': { ru: 'Товары', uz: 'Mahsulotlar', en: 'Products' },
  'nav.stock': { ru: 'Остатки', uz: 'Qoldiqlar', en: 'Stock' },
  'nav.receipt': { ru: 'Приёмка', uz: 'Kirim', en: 'Receipt' },
  'nav.shipment': { ru: 'Pick marshruti', uz: 'Pick marshruti', en: 'Pick route' },
  'nav.move': { ru: 'Перемещение', uz: "Ko'chirish", en: 'Move' },
  'nav.tasks': { ru: 'Задачи', uz: 'Vazifalar', en: 'Tasks' },
  'nav.analytics': { ru: 'Аналитика', uz: 'Analitika', en: 'Analytics' },
  'nav.monitoring': { ru: 'Климат', uz: 'Harorat-namlik', en: 'Climate' },
  'nav.smartup': { ru: 'Smartup (ERP)', uz: 'Smartup (ERP)', en: 'Smartup (ERP)' },
  'nav.settings': { ru: 'Настройки', uz: 'Sozlamalar', en: 'Settings' },
  // Guruh sarlavhalari
  'group.warehouse': { ru: 'Склад', uz: 'Sklad', en: 'Warehouse' },
  'group.operations': { ru: 'Операции', uz: 'Operatsiyalar', en: 'Operations' },
  'group.analysis': { ru: 'Анализ', uz: 'Tahlil', en: 'Analysis' },
  'group.system': { ru: 'Система', uz: 'Tizim', en: 'System' },
  // Umumiy
  'common.language': { ru: 'Язык', uz: 'Til', en: 'Language' },
  'common.save': { ru: 'Сохранить', uz: 'Saqlash', en: 'Save' },
  'common.cancel': { ru: 'Отмена', uz: 'Bekor', en: 'Cancel' },
  'common.loading': { ru: 'Загрузка…', uz: 'Yuklanmoqda…', en: 'Loading…' },
  'common.logout': { ru: 'Выход', uz: 'Chiqish', en: 'Logout' },
  'common.search': { ru: 'Поиск', uz: 'Qidiruv', en: 'Search' },
  'common.user': { ru: 'Пользователь', uz: 'Foydalanuvchi', en: 'User' },
  'theme.light': { ru: 'Светлая тема', uz: "Yorug' rejim", en: 'Light mode' },
  'theme.dark': { ru: 'Тёмная тема', uz: 'Tungi rejim', en: 'Dark mode' },
  // Holatlar
  'status.occupied': { ru: 'Занято', uz: 'Band', en: 'Occupied' },
  'status.partial': { ru: 'Частично', uz: 'Qisman', en: 'Partial' },
  'status.blocked': { ru: 'Заблокировано', uz: 'Bloklangan', en: 'Blocked' },
  'status.empty': { ru: 'Свободно', uz: "Bo'sh", en: 'Empty' },
}

const LABELS: Record<Locale, string> = { ru: 'Русский', uz: "O'zbekcha", en: 'English' }

type Ctx = { locale: Locale; setLocale: (l: Locale) => void; t: (k: string) => string }
const LangContext = createContext<Ctx>({ locale: 'ru', setLocale: () => {}, t: k => k })

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const saved = localStorage.getItem('locale') as Locale | null
    return saved && LOCALES.includes(saved) ? saved : 'ru'
  })
  useEffect(() => { document.documentElement.lang = locale }, [locale])
  const setLocale = (l: Locale) => { localStorage.setItem('locale', l); setLocaleState(l) }
  const t = (k: string) => DICT[k]?.[locale] ?? k
  return <LangContext.Provider value={{ locale, setLocale, t }}>{children}</LangContext.Provider>
}

export const useI18n = () => useContext(LangContext)
export const localeLabels = LABELS
export const allLocales = LOCALES
