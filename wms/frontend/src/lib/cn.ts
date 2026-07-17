import { clsx, type ClassValue } from 'clsx'

/** className birlashtiruvchi (Tailwind uchun). */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs)
}
