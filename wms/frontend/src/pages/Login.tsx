import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { login, getMe } from '../lib/api'
import { useAuthStore } from '../store/auth'
import { useZodForm, loginSchema } from '../lib/forms'
import { FormField, Input } from '../components/ui'

export default function Login() {
  const f = useZodForm(loginSchema, { email: 'admin@wms.uz', password: 'admin123' })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setUser = useAuthStore(s => s.setUser)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const valid = f.validate()
    if (!valid) return
    setLoading(true)
    try {
      const data = await login(valid.email, valid.password)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      const me = await getMe()
      setUser(me)
      navigate('/')
    } catch {
      toast.error('Login yoki parol noto\'g\'ri')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-sm">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold text-lg">W</div>
          <div>
            <h1 className="font-bold text-xl text-slate-800">WMS</h1>
            <p className="text-slate-400 text-xs">Warehouse Management</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <FormField label="Email" error={f.errors.email}>
            <Input
              type="email"
              value={f.values.email}
              onChange={e => f.set('email', e.target.value)}
              aria-invalid={!!f.errors.email}
            />
          </FormField>
          <FormField label="Parol" error={f.errors.password}>
            <Input
              type="password"
              value={f.values.password}
              onChange={e => f.set('password', e.target.value)}
              aria-invalid={!!f.errors.password}
            />
          </FormField>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 text-sm font-medium transition disabled:opacity-50"
          >
            {loading ? 'Kirish...' : 'Kirish'}
          </button>
          <p className="text-center text-sm text-slate-500">
            Hisobingiz yo'qmi?{' '}
            <a href="/signup" className="text-blue-600 font-medium">Ro'yxatdan o'tish</a>
          </p>
        </form>
      </div>
    </div>
  )
}
