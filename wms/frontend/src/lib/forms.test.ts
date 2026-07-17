import { describe, it, expect } from 'vitest'
import { loginSchema, signupSchema, productSchema, emailSchema } from './forms'

describe('emailSchema', () => {
  it('rejects malformed email', () => {
    expect(emailSchema.safeParse('notanemail').success).toBe(false)
  })
  it('accepts a valid email', () => {
    expect(emailSchema.safeParse('a@b.com').success).toBe(true)
  })
})

describe('loginSchema', () => {
  it('rejects invalid email', () => {
    expect(loginSchema.safeParse({ email: 'bad', password: 'x' }).success).toBe(false)
  })
  it('rejects empty password', () => {
    expect(loginSchema.safeParse({ email: 'a@b.com', password: '' }).success).toBe(false)
  })
  it('accepts valid credentials', () => {
    expect(loginSchema.safeParse({ email: 'a@b.com', password: 'secret' }).success).toBe(true)
  })
})

describe('signupSchema', () => {
  it('requires a name of at least 2 chars', () => {
    expect(signupSchema.safeParse({ full_name: 'A', email: 'a@b.com', password: '123456' }).success).toBe(false)
  })
  it('requires password >= 6 chars', () => {
    expect(signupSchema.safeParse({ full_name: 'Ali', email: 'a@b.com', password: '123' }).success).toBe(false)
  })
})

describe('productSchema', () => {
  it('accepts empty gtin', () => {
    expect(productSchema.safeParse({ name: 'Suv', uom: 'unit', gtin: '' }).success).toBe(true)
  })
  it('rejects too-short gtin', () => {
    expect(productSchema.safeParse({ name: 'Suv', uom: 'unit', gtin: '123' }).success).toBe(false)
  })
  it('accepts a 14-digit gtin', () => {
    expect(productSchema.safeParse({ name: 'Suv', uom: 'unit', gtin: '04601234567890' }).success).toBe(true)
  })
})
