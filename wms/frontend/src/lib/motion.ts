import type { Variants } from 'framer-motion'

// Kamaytirish: foydalanuvchi prefers-reduced-motion ni tanlaganmi
export const reduceMotion =
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

const dur = (ms: number) => (reduceMotion ? 0 : ms / 1000)

// Sahifa/karta pastdan yuqoriga kirish
export const fadeInUp: Variants = {
  hidden:  { opacity: 0, y: reduceMotion ? 0 : 16 },
  visible: { opacity: 1, y: 0, transition: { duration: dur(220), ease: 'easeOut' } },
  exit:    { opacity: 0, y: reduceMotion ? 0 : -8, transition: { duration: dur(150) } },
}

// Konteyner — bolalar ketma-ket kirsin
export const staggerContainer: Variants = {
  hidden:  { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: dur(60), delayChildren: dur(40) },
  },
}

// Karta — pastdan
export const cardItem: Variants = {
  hidden:  { opacity: 0, y: reduceMotion ? 0 : 20 },
  visible: { opacity: 1, y: 0, transition: { duration: dur(200), ease: 'easeOut' } },
}

// Modal / popover — o'lchov bilan kirish
export const scaleIn: Variants = {
  hidden:  { opacity: 0, scale: reduceMotion ? 1 : 0.95 },
  visible: { opacity: 1, scale: 1, transition: { duration: dur(180), ease: [0.16, 1, 0.3, 1] } },
  exit:    { opacity: 0, scale: reduceMotion ? 1 : 0.97, transition: { duration: dur(130) } },
}

// Tab kontenti almashinuvi
export const tabFade: Variants = {
  hidden:  { opacity: 0, x: reduceMotion ? 0 : 10 },
  visible: { opacity: 1, x: 0, transition: { duration: dur(180), ease: 'easeOut' } },
  exit:    { opacity: 0, x: reduceMotion ? 0 : -6, transition: { duration: dur(120) } },
}

// Akkordeon yig'ilish/ochilish — height clip
export const accordionContent: Variants = {
  hidden:  { height: 0, opacity: 0 },
  visible: {
    height: 'auto',
    opacity: 1,
    transition: {
      height: { duration: dur(260), ease: 'easeOut' as const },
      opacity: { duration: dur(180) },
    },
  },
  exit: {
    height: 0,
    opacity: 0,
    transition: {
      height: { duration: dur(200) },
      opacity: { duration: dur(120) },
    },
  },
}
