import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { CircleNotch, Eye, EyeSlash } from '@phosphor-icons/react'
import { toast } from 'sonner'
import loginBg from '@/assets/login_bg.png'
import logo from '@/assets/logo.png'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (localStorage.getItem('access_token')) navigate('/', { replace: true })
  }, [navigate])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await api.login(username, password)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      navigate('/', { replace: true })
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen flex p-2 sm:p-4 font-sans" style={{ background: 'var(--bg)' }}>
      <div className="flex flex-1 w-full rounded sm:rounded-md overflow-hidden border"
           style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
        {/* Left — image panel (hidden on mobile) */}
        <div
          className="hidden lg:flex w-1/2 bg-slate-900 bg-cover bg-center"
          style={{ backgroundImage: `url(${loginBg})` }}
        >
          <div className="w-full h-full bg-olive-900/10 backdrop-brightness-90" />
        </div>

        {/* Right — login form */}
        <div className="flex-1 flex items-center justify-center p-6 sm:p-8"
             style={{ background: 'var(--surface)' }}>
          <div className="w-full max-w-sm">
            <div className="flex flex-col items-center mb-10 sm:mb-12 text-center">
              <div className="mb-4 flex items-center justify-center scale-150 transition-transform hover:scale-175 duration-500">
                <img src={logo} alt="Logo" className="h-20 sm:h-24 w-auto object-contain" />
              </div>
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tighter mb-2"
                  style={{ color: 'var(--text)' }}>Welcome Back</h1>
              <p className="text-sm font-bold" style={{ color: 'var(--muted)' }}>Sign in to manage your inspections</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
              <div className="flex flex-col gap-2">
                <label htmlFor="login-username" className="text-xs font-bold"
                       style={{ color: 'var(--muted)' }}>Username</label>
                <input
                  id="login-username"
                  type="text" value={username} onChange={e => setUsername(e.target.value)}
                  placeholder="Admin" required autoFocus autoComplete="username"
                  className="w-full px-4 py-3.5 rounded border focus:outline-none focus:ring-2 focus:ring-olive-50 focus:border-olive-600 transition-all font-medium"
                  style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }}
                />
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <label htmlFor="login-password" className="text-xs font-bold"
                         style={{ color: 'var(--muted)' }}>Password</label>
                  <a href="#" className="text-[11px] font-bold text-olive-600 hover:text-olive-700 transition-colors">Forgot Password?</a>
                </div>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showPass ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••" required autoComplete="current-password"
                    className="w-full px-4 py-3.5 rounded border focus:outline-none focus:ring-2 focus:ring-olive-50 focus:border-olive-600 transition-all font-medium pr-12"
                    style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }}
                  />
                  <button type="button" onClick={() => setShowPass(v => !v)}
                          className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                          style={{ color: 'var(--muted)' }}
                          aria-label={showPass ? 'Hide password' : 'Show password'}>
                    {showPass ? <EyeSlash size={20} weight="bold" /> : <Eye size={20} weight="bold" />}
                  </button>
                </div>
              </div>

              <div className="pt-4">
                <button
                  type="submit" disabled={loading}
                  className="w-full py-4 rounded bg-olive-600 hover:bg-olive-700 text-white font-bold text-[15px] transition-all disabled:opacity-50 active:scale-[0.98]"
                >
                  {loading && <CircleNotch size={18} className="animate-spin inline mr-2" />}
                  {loading ? 'Entering...' : 'Sign In'}
                </button>
              </div>
            </form>


          </div>
        </div>
      </div>
    </div>
  )
}
