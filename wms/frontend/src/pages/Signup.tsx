/** Self-registration → creates a pending account awaiting admin approval (P4). */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { signup } from '../lib/api'
import { useZodForm, emailSchema, passwordSchema } from '../lib/forms'
import { UserPlus, CheckCircle2 } from 'lucide-react'

const schema = z.object({
  full_name: z.string().trim().min(2, 'Ism kamida 2 belgi'),
  email: emailSchema,
  password: passwordSchema,
  tenant_slug: z.string().trim().min(1, 'Tashkilot kodi shart'),
})

export default function Signup() {
  const nav = useNavigate()
  const f = useZodForm(schema, { full_name: '', email: '', password: '', tenant_slug: 'demo' })
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const valid = f.validate()
    if (!valid) return
    setBusy(true); setErr('')
    try { await signup(valid); setDone(true) }
    catch (e: any) {
      const d = e?.response?.data?.detail
      setErr(d === 'email_taken' ? 'Bu email band' : d === 'organisation_not_found' ? 'Tashkilot topilmadi' : 'Xatolik')
    } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        {done ? (
          <div className="text-center space-y-3 py-4">
            <CheckCircle2 size={48} className="mx-auto text-green-500" />
            <h2 className="font-bold text-slate-800">So'rovingiz qabul qilindi</h2>
            <p className="text-sm text-slate-500">Hisobingiz administrator tasdig'ini kutmoqda. Tasdiqlangach kirishingiz mumkin bo'ladi.</p>
            <button onClick={() => nav('/login')} className="text-blue-600 text-sm font-medium">Kirishga qaytish</button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center text-white"><UserPlus size={18} /></div>
              <div><div className="font-bold text-slate-800">Ro'yxatdan o'tish</div><div className="text-xs text-slate-400">Tasdiqdan keyin faollashadi</div></div>
            </div>
            {err && <div className="text-sm text-red-600 bg-red-50 rounded-lg p-2">{err}</div>}
            <Field label="To'liq ism" error={f.errors.full_name}><input className="inp" value={f.values.full_name} onChange={e => f.set('full_name', e.target.value)} /></Field>
            <Field label="Email" error={f.errors.email}><input className="inp" type="email" value={f.values.email} onChange={e => f.set('email', e.target.value)} /></Field>
            <Field label="Parol" error={f.errors.password}><input className="inp" type="password" value={f.values.password} onChange={e => f.set('password', e.target.value)} /></Field>
            <Field label="Tashkilot kodi" error={f.errors.tenant_slug}><input className="inp" value={f.values.tenant_slug} onChange={e => f.set('tenant_slug', e.target.value)} /></Field>
            <button disabled={busy} className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50">
              {busy ? 'Yuborilmoqda…' : "Ro'yxatdan o'tish"}
            </button>
            <p className="text-center text-sm text-slate-500">Hisobingiz bormi? <Link to="/login" className="text-blue-600 font-medium">Kirish</Link></p>
            <style>{`.inp{width:100%;border:1px solid #e2e8f0;border-radius:8px;padding:8px 10px;font-size:14px}.inp:focus{outline:none;border-color:#3b82f6}`}</style>
          </form>
        )}
      </div>
    </div>
  )
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs text-slate-500 mb-1 block">{label}</span>
      {children}
      {error && <span className="text-xs text-rose-500 mt-1 block">{error}</span>}
    </label>
  )
}
