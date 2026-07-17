import { useState } from 'react'
import { z } from 'zod'

/**
 * Yengil Zod form-validatsiya yordamchisi. Avval formalar validatsiyasiz edi
 * (bo'sh/noto'g'ri qiymatlar to'g'ridan-to'g'ri backendga ketardi). Endi:
 *   const f = useZodForm(schema, initial)
 *   f.set('email', v) · f.errors.email · f.validate() · f.values
 */
export function useZodForm<S extends z.ZodObject<any>>(schema: S, initial: z.infer<S>) {
  type V = z.infer<S>
  const [values, setValues] = useState<V>(initial)
  const [errors, setErrors] = useState<Partial<Record<keyof V, string>>>({})

  const set = <K extends keyof V>(key: K, value: V[K]) => {
    setValues(prev => ({ ...prev, [key]: value }))
    if (errors[key]) setErrors(prev => ({ ...prev, [key]: undefined }))
  }

  /** Tekshiradi; xato bo'lsa errors'ni to'ldiradi va null qaytaradi. */
  const validate = (): V | null => {
    const res = schema.safeParse(values)
    if (res.success) { setErrors({}); return res.data }
    const errs: Partial<Record<keyof V, string>> = {}
    for (const issue of res.error.issues) {
      const k = issue.path[0] as keyof V
      if (k != null && !errs[k]) errs[k] = issue.message
    }
    setErrors(errs)
    return null
  }

  const reset = (v: V = initial) => { setValues(v); setErrors({}) }

  return { values, errors, set, validate, reset, setValues }
}

// ─── Umumiy schemalar ─────────────────────────────────────────────────────────
export const emailSchema = z.string().trim().min(1, 'Email kiritilishi shart').email('Email formati noto\'g\'ri')
export const passwordSchema = z.string().min(6, 'Parol kamida 6 belgi bo\'lishi kerak')

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Parol kiritilishi shart'),
})

export const signupSchema = z.object({
  full_name: z.string().trim().min(2, 'Ism kamida 2 belgi'),
  email: emailSchema,
  phone: z.string().trim().optional(),
  password: passwordSchema,
})

export const productSchema = z.object({
  name: z.string().trim().min(2, 'Nomi kamida 2 belgi'),
  gtin: z.string().trim().regex(/^\d{8,14}$/u, 'GTIN 8–14 raqam bo\'lishi kerak').or(z.literal('')).optional(),
  uom: z.string().trim().min(1, 'O\'lchov birligi shart'),
  units_per_box: z.coerce.number().int().positive('Musbat son').optional(),
  boxes_per_pallet: z.coerce.number().int().positive('Musbat son').optional(),
  min_stock: z.coerce.number().int().nonnegative().optional(),
  max_stock: z.coerce.number().int().nonnegative().optional(),
})
