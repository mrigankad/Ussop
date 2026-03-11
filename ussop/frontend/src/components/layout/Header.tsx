import React, { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import * as Dialog from '@radix-ui/react-dialog'
import { User, SignOut, CaretDown, WifiHigh, WifiSlash, GearSix, X, Key, List, Sun, Moon } from '@phosphor-icons/react'
import { api } from '@/lib/api'

const titles: Record<string, { title: string; sub: string }> = {
  '/': { title: 'Dashboard', sub: 'Overview of system status and metrics' },
  '/inspect': { title: 'Inspect', sub: 'Analyze images and capture samples' },
  '/history': { title: 'History', sub: 'Review past inspection records' },
  '/analytics': { title: 'Analytics', sub: 'View trends and performance data' },
  '/annotate': { title: 'Annotate', sub: 'Verify samples and improve model' },
  '/batch': { title: 'Batch', sub: 'Run processing tasks on folders' },
  '/query': { title: 'AI Search', sub: 'Ask questions about your data' },
  '/stations': { title: 'Stations', sub: 'Monitor production lines' },
  '/alerts': { title: 'Alerts', sub: 'System notifications and logs' },
  '/config': { title: 'Configuration', sub: 'Manage global system settings and parameters' },
}

function Breadcrumbs() {
  const { pathname } = useLocation()
  const paths = pathname.split('/').filter(Boolean)
  
  return (
    <nav className="flex items-center gap-2 text-[10px] sm:text-[11px] font-bold tracking-wider" style={{ color: 'var(--muted)' }}>
      <span className="hover:text-olive-600 cursor-pointer transition-colors">Home</span>
      {paths.map((p, i) => (
        <React.Fragment key={p}>
          <span style={{ color: 'var(--border)' }}>/</span>
          <span className={i === paths.length - 1 ? 'text-olive-600' : 'hover:text-olive-600 cursor-pointer transition-colors'}>
            {p.charAt(0).toUpperCase() + p.slice(1).replace(/-/g, ' ')}
          </span>
        </React.Fragment>
      ))}
      {paths.length === 0 && (
        <>
          <span style={{ color: 'var(--border)' }}>/</span>
          <span className="text-olive-600">Dashboard</span>
        </>
      )}
    </nav>
  )
}

function ThemeToggle() {
  const [dark, setDark] = useState(() =>
    document.documentElement.getAttribute('data-theme') === 'dark'
  )

  function toggle() {
    const next = !dark
    setDark(next)
    document.documentElement.setAttribute('data-theme', next ? 'dark' : 'light')
    localStorage.setItem('theme', next ? 'dark' : 'light')
  }

  return (
    <button
      onClick={toggle}
      className="w-10 h-10 rounded-xl flex items-center justify-center border transition-all hover:scale-105 active:scale-95"
      style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text-2)' }}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {dark ? <Sun size={18} weight="bold" /> : <Moon size={18} weight="bold" />}
    </button>
  )
}

function HealthBadge() {
  const [healthy, setHealthy] = useState<boolean | null>(null)
  useEffect(() => {
    const check = () => api.health().then(() => setHealthy(true)).catch(() => setHealthy(false))
    check()
    const id = setInterval(check, 15000)
    return () => clearInterval(id)
  }, [])
  if (healthy === null) return null
  return (
    <div className={`hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-semibold tracking-wider border transition-all ${healthy
        ? 'bg-emerald-50 text-emerald-600 border-emerald-100 shadow-sm'
        : 'bg-red-50 text-red-600 border-red-100 shadow-sm animate-pulse'
      }`}>
      {healthy ? <WifiHigh size={14} weight="bold" /> : <WifiSlash size={14} weight="bold" />}
      <span className="hidden md:inline">{healthy ? 'Operational' : 'Disconnected'}</span>
    </div>
  )
}

function AccountSettingsModal({ open, onClose, user }: { open: boolean; onClose: () => void; user: any }) {
  const [tab, setTab] = useState<'profile' | 'password'>('profile')
  const [email, setEmail] = useState(user?.email || '')
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  async function saveProfile() {
    setSaving(true); setMsg(null)
    try {
      await api.updateMe({ email })
      const stored = JSON.parse(localStorage.getItem('user') || '{}')
      localStorage.setItem('user', JSON.stringify({ ...stored, email }))
      setMsg({ type: 'success', text: 'Profile updated successfully.' })
    } catch { setMsg({ type: 'error', text: 'Failed to update profile.' }) }
    finally { setSaving(false) }
  }

  async function handleChangePassword() {
    if (newPw !== confirmPw) { setMsg({ type: 'error', text: 'Passwords do not match.' }); return }
    if (newPw.length < 6) { setMsg({ type: 'error', text: 'Password must be at least 6 characters.' }); return }
    setSaving(true); setMsg(null)
    try {
      await api.changePassword(currentPw, newPw)
      setMsg({ type: 'success', text: 'Password changed successfully.' })
      setCurrentPw(''); setNewPw(''); setConfirmPw('')
    } catch { setMsg({ type: 'error', text: 'Failed — check current credentials.' }) }
    finally { setSaving(false) }
  }

  return (
    <Dialog.Root open={open} onOpenChange={v => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/10 backdrop-blur-[4px] z-50 animate-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 rounded-2xl border w-[95vw] max-w-md p-6 sm:p-10 animate-in shadow-2xl"
                        style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center justify-between mb-8 sm:mb-10">
            <Dialog.Title className="text-xl sm:text-2xl font-semibold tracking-tight"
                          style={{ color: 'var(--text)' }}>
              Account Settings
            </Dialog.Title>
            <button onClick={onClose} className="w-10 h-10 rounded-2xl border flex items-center justify-center transition-all hover:rotate-90"
                    style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}
                    aria-label="Close settings">
              <X size={16} weight="bold" style={{ color: 'var(--muted)' }} />
            </button>
          </div>

          <div className="flex gap-2 mb-8 sm:mb-10 p-2 rounded-2xl border"
               style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
            {(['profile', 'password'] as const).map(t => (
              <button key={t} onClick={() => { setTab(t); setMsg(null) }}
                className={`flex-1 py-3 text-[10px] font-semibold tracking-wider rounded-xl transition-all ${
                  tab === t
                    ? 'shadow-lg shadow-slate-900/5'
                    : ''
                }`}
                style={tab === t
                  ? { background: 'var(--surface)', color: 'var(--text)' }
                  : { color: 'var(--muted)' }
                }>
                {t === 'profile' ? <><User size={14} weight="bold" className="inline mr-2" />Profile</> : <><Key size={14} weight="bold" className="inline mr-2" />Security</>}
              </button>
            ))}
          </div>

          {tab === 'profile' && (
            <div className="space-y-6 sm:space-y-8">
              <div className="flex flex-col gap-3">
                <label className="text-[10px] font-semibold tracking-wider pl-2" style={{ color: 'var(--muted)' }}>Username</label>
                <input value={user?.username || ''} disabled
                       className="w-full px-6 py-4 rounded-xl border font-bold cursor-not-allowed"
                       style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' }} />
              </div>
              <div className="flex flex-col gap-3">
                <label className="text-[10px] font-semibold tracking-wider pl-2" style={{ color: 'var(--muted)' }}>Email Address</label>
                <input value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com"
                       className="w-full px-6 py-4 rounded-xl border font-bold focus:outline-none focus:ring-4 focus:ring-olive-50 transition-all"
                       style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }} />
              </div>
              <div className="flex flex-col gap-3">
                <label className="text-[10px] font-semibold tracking-wider pl-2" style={{ color: 'var(--muted)' }}>User Role</label>
                <input value={(user?.roles || []).join(', ') || 'Standard'} disabled
                       className="w-full px-6 py-4 rounded-xl border font-bold cursor-not-allowed text-[10px] tracking-tight"
                       style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' }} />
              </div>
            </div>
          )}

          {tab === 'password' && (
            <div className="space-y-6 sm:space-y-8">
              {[
                { label: 'Current Password', val: currentPw, set: setCurrentPw },
                { label: 'New Password', val: newPw, set: setNewPw },
                { label: 'Confirm Password', val: confirmPw, set: setConfirmPw },
              ].map(({ label, val, set }) => (
                <div key={label} className="flex flex-col gap-3">
                  <label className="text-[10px] font-semibold tracking-wider pl-2" style={{ color: 'var(--muted)' }}>{label}</label>
                  <input type="password" value={val} onChange={e => set(e.target.value)} placeholder="••••••••"
                         className="w-full px-6 py-4 rounded-xl border font-bold focus:outline-none focus:ring-4 focus:ring-olive-50 transition-all"
                         style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }} />
                </div>
              ))}
            </div>
          )}

          {msg && (
            <div className={`mt-8 px-6 py-4 rounded-xl text-[10px] font-semibold tracking-tight border ${msg.type === 'success' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-red-50 text-red-700 border-red-100'}`}>
              {msg.text}
            </div>
          )}

          <div className="flex gap-4 mt-10 sm:mt-12">
            <button onClick={onClose}
                    className="flex-1 py-4 rounded-xl border text-[10px] font-semibold tracking-wider transition-all active:scale-95"
                    style={{ borderColor: 'var(--border-subtle)', color: 'var(--muted)' }}>
              Cancel
            </button>
            <button onClick={tab === 'profile' ? saveProfile : handleChangePassword} disabled={saving}
                    className="flex-1 py-4 rounded-xl text-white text-[10px] font-semibold tracking-wider flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-95 shadow-xl bg-olive-600 hover:bg-olive-700">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { pathname } = useLocation()
  const page = titles[pathname] || { title: 'Ussop Engine', sub: 'Primary Control Interface' }
  const user = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null } })()
  const [settingsOpen, setSettingsOpen] = useState(false)

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    window.location.href = '/login'
  }

  return (
    <header className="h-14 lg:h-16 backdrop-blur-xl border-b flex items-center justify-between px-4 sm:px-6 lg:px-10 shrink-0 z-20 sticky top-0 transition-all"
            style={{ background: 'color-mix(in srgb, var(--surface) 60%, transparent)', borderColor: 'var(--border-subtle)' }}>
      <div className="flex items-center gap-3 min-w-0">
        {/* Hamburger menu — mobile only */}
        <button
          onClick={onMenuClick}
          className="lg:hidden w-10 h-10 rounded-xl flex items-center justify-center border transition-all hover:scale-105 active:scale-95 shrink-0"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text-2)' }}
          aria-label="Open navigation menu"
        >
          <List size={20} weight="bold" />
        </button>

        <div className="flex flex-col min-w-0 justify-center">
          <div className="flex items-center gap-3 lg:gap-4 min-w-0">
            <h1 className="text-lg lg:text-xl font-bold tracking-tighter leading-tight truncate md:min-w-fit"
                style={{ color: 'var(--text)' }}>
              {page.title}
            </h1>
            <div className="hidden sm:flex items-center gap-3 lg:gap-4 shrink-0">
              <div className="w-px h-4" style={{ background: 'var(--border-subtle)' }} />
              <Breadcrumbs />
            </div>
          </div>
          <p className="hidden sm:block text-[10px] font-semibold tracking-wider mt-1 opacity-70 truncate uppercase"
             style={{ color: 'var(--muted)' }}>
            {page.sub}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 lg:gap-6 shrink-0">
        <HealthBadge />
        <ThemeToggle />

        {user && (
          <DropdownMenu.Root>
            <DropdownMenu.Trigger className="flex items-center gap-3 p-1.5 pr-4 lg:pr-5 rounded-2xl transition-all outline-none border group hover:border-olive-200 hover:shadow-lg hover:shadow-olive-900/5 cursor-pointer"
                                  style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
              <div className="w-8 h-8 lg:w-10 lg:h-10 rounded-xl flex items-center justify-center transition-all bg-slate-50 group-hover:bg-olive-50 group-hover:scale-105">
                <User size={18} weight="bold" className="text-slate-400 group-hover:text-olive-600 transition-colors" />
              </div>
              <div className="text-left hidden md:flex flex-col justify-center">
                <p className="text-[12px] font-bold tracking-tight leading-none mb-1.5 text-slate-800" style={{ color: 'var(--text)' }}>
                  {user.username}
                </p>
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-olive-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-olive-600"></span>
                  </span>
                  <span className="text-[9px] font-bold text-olive-600 uppercase tracking-widest leading-none">
                    {user.roles?.[0] || 'Personnel'}
                  </span>
                </div>
              </div>
              <CaretDown size={14} weight="bold" className="group-hover:translate-y-0.5 transition-transform ml-2 text-slate-300 group-hover:text-olive-600" />
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content align="end" sideOffset={16}
                                    className="w-64 sm:w-[280px] rounded-[24px] border p-2 z-50 animate-in shadow-2xl flex flex-col gap-1"
                                    style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
                <div className="px-5 py-5 mb-1 rounded-[20px]"
                     style={{ background: 'var(--surface-2)' }}>
                  <p className="text-[15px] font-bold tracking-tight mb-1"
                     style={{ color: 'var(--text)' }}>
                    {user.username}
                  </p>
                  <p className="text-[12px] font-semibold truncate tracking-wider"
                     style={{ color: 'var(--muted)' }}>
                    {user.email || 'admin@ussop.local'}
                  </p>
                </div>
                
                <DropdownMenu.Item onSelect={() => setSettingsOpen(true)}
                                    className="flex items-center gap-4 px-3 py-2.5 text-[12.5px] font-bold tracking-tight rounded-[18px] cursor-pointer outline-none transition-all group hover:bg-slate-50/80"
                                    style={{ color: 'var(--text-2)' }}>
                  <div className="p-3 rounded-[14px] bg-slate-50 text-slate-500 group-hover:bg-white group-hover:shadow-sm transition-all border border-transparent group-hover:border-slate-100">
                    <GearSix size={18} weight="bold" />
                  </div>
                  Account Settings
                </DropdownMenu.Item>
                
                <div className="h-px my-1.5 mx-4" style={{ background: 'var(--border-subtle)' }} />
                
                <DropdownMenu.Item onClick={logout}
                                    className="flex items-center gap-4 px-3 py-2.5 text-[12.5px] font-bold tracking-tight text-red-600 rounded-[18px] cursor-pointer hover:bg-red-50/50 outline-none transition-all group">
                  <div className="p-3 rounded-[14px] bg-red-50 text-red-500 group-hover:bg-red-100 transition-colors border border-transparent">
                    <SignOut size={18} weight="bold" />
                  </div>
                  Sign Out
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        )}
      </div>
      {user && <AccountSettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} user={user} />}
    </header>
  )
}
