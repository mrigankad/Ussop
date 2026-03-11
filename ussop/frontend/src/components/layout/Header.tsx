import { useLocation } from 'react-router-dom'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import * as Dialog from '@radix-ui/react-dialog'
import { User, SignOut, CaretDown, WifiHigh, WifiSlash, GearSix, X, FloppyDisk, Key } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

const titles: Record<string, { title: string; sub: string }> = {
  '/': { title: 'Dashboard', sub: 'Overview & recent activity' },
  '/inspect': { title: 'Inspect', sub: 'Run AI visual inspection' },
  '/history': { title: 'History', sub: 'All inspection records' },
  '/analytics': { title: 'Analytics', sub: 'Trends & performance metrics' },
  '/annotate': { title: 'Annotate', sub: 'Active learning queue' },
  '/batch': { title: 'Batch', sub: 'Process image folders' },
  '/query': { title: 'AI Query', sub: 'Ask questions about your inspection data' },
  '/stations': { title: 'Stations', sub: 'Multi-station overview and health' },
  '/alerts': { title: 'Alerts', sub: 'System notifications and warnings' },
  '/config': { title: 'Configuration', sub: 'System settings' },
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
    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border ${healthy
        ? 'bg-emerald-50 text-emerald-600 border-emerald-100 shadow-[0_2px_10px_rgba(16,185,129,0.08)]'
        : 'bg-red-50 text-red-600 border-red-100 shadow-[0_2px_10px_rgba(239,68,68,0.08)]'
      }`}>
      {healthy ? <WifiHigh size={12} weight="bold" className="animate-pulse" /> : <WifiSlash size={12} weight="bold" />}
      {healthy ? 'System Online' : 'System Offline'}
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
      setMsg({ type: 'success', text: 'Profile updated.' })
    } catch { setMsg({ type: 'error', text: 'Failed to update profile.' }) }
    finally { setSaving(false) }
  }

  async function handleChangePassword() {
    if (newPw !== confirmPw) { setMsg({ type: 'error', text: 'Passwords do not match.' }); return }
    if (newPw.length < 6) { setMsg({ type: 'error', text: 'Password must be at least 6 characters.' }); return }
    setSaving(true); setMsg(null)
    try {
      await api.changePassword(currentPw, newPw)
      setMsg({ type: 'success', text: 'Password changed.' })
      setCurrentPw(''); setNewPw(''); setConfirmPw('')
    } catch { setMsg({ type: 'error', text: 'Failed — check your current password.' }) }
    finally { setSaving(false) }
  }

  return (
    <Dialog.Root open={open} onOpenChange={v => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 animate-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.15)] border border-slate-200 w-full max-w-md p-6 animate-in">
          <div className="flex items-center justify-between mb-5">
            <Dialog.Title className="text-lg font-extrabold text-slate-800">Account Settings</Dialog.Title>
            <button onClick={onClose} className="w-8 h-8 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center hover:bg-slate-100 transition-colors">
              <X size={14} weight="bold" className="text-slate-500" />
            </button>
          </div>

          <div className="flex gap-1 mb-5 p-1 bg-slate-100 rounded-xl">
            {(['profile', 'password'] as const).map(t => (
              <button key={t} onClick={() => { setTab(t); setMsg(null) }}
                className={`flex-1 py-2 text-xs font-bold rounded-lg capitalize transition-all ${tab === t ? 'bg-white shadow-sm text-slate-800 border border-slate-200' : 'text-slate-500 hover:text-slate-700'}`}>
                {t === 'profile' ? <><User size={12} className="inline mr-1.5" />Profile</> : <><Key size={12} className="inline mr-1.5" />Password</>}
              </button>
            ))}
          </div>

          {tab === 'profile' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1.5">Username</label>
                <input value={user?.username || ''} disabled className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 font-medium cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1.5">Email</label>
                <input value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com"
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 transition-all" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1.5">Role</label>
                <input value={(user?.roles || []).join(', ') || 'user'} disabled className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 font-medium cursor-not-allowed capitalize" />
              </div>
            </div>
          )}

          {tab === 'password' && (
            <div className="space-y-4">
              {[
                { label: 'Current Password', val: currentPw, set: setCurrentPw },
                { label: 'New Password', val: newPw, set: setNewPw },
                { label: 'Confirm New Password', val: confirmPw, set: setConfirmPw },
              ].map(({ label, val, set }) => (
                <div key={label}>
                  <label className="block text-xs font-bold text-slate-600 mb-1.5">{label}</label>
                  <input type="password" value={val} onChange={e => set(e.target.value)} placeholder="••••••••"
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 transition-all" />
                </div>
              ))}
            </div>
          )}

          {msg && (
            <div className={`mt-4 px-3 py-2.5 rounded-xl text-xs font-bold border ${msg.type === 'success' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-red-50 text-red-700 border-red-100'}`}>
              {msg.text}
            </div>
          )}

          <div className="flex gap-3 mt-5">
            <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-slate-200 text-sm font-bold text-slate-600 hover:bg-slate-50 transition-colors">
              Cancel
            </button>
            <button onClick={tab === 'profile' ? saveProfile : handleChangePassword} disabled={saving}
              className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-sm font-bold text-white flex items-center justify-center gap-2 transition-colors disabled:opacity-60">
              <FloppyDisk size={14} weight="bold" /> {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

export default function Header() {
  const { pathname } = useLocation()
  const page = titles[pathname] || { title: 'Ussop', sub: '' }
  const user = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null } })()
  const [settingsOpen, setSettingsOpen] = useState(false)

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    window.location.href = '/login'
  }

  return (
    <header className="h-20 glass border-b border-slate-200/60 flex items-center justify-between px-8 shrink-0 z-20 sticky top-0 bg-white/70 backdrop-blur-xl">
      <div>
        <h1 className="text-xl font-bold text-slate-800 tracking-tight">{page.title}</h1>
        <p className="text-sm text-slate-500 mt-0.5 font-medium">{page.sub}</p>
      </div>
      <div className="flex items-center gap-5">
        <HealthBadge />
        {user && (
          <DropdownMenu.Root>
            <DropdownMenu.Trigger className="flex items-center gap-3 px-3 py-1.5 rounded-2xl hover:bg-slate-50 transition-all outline-none border border-transparent hover:border-slate-200 hover:shadow-sm group">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors border border-indigo-100/50">
                <User size={16} weight="duotone" className="text-indigo-600 group-hover:text-indigo-700 transition-colors" />
              </div>
              <div className="text-left py-0.5">
                <p className="text-sm font-bold text-slate-800 leading-none group-hover:text-indigo-700 transition-colors">{user.username}</p>
                <p className="text-[11px] font-medium text-slate-400 mt-1 capitalize">{user.roles?.[0] || 'user'}</p>
              </div>
              <CaretDown size={14} weight="bold" className="text-slate-400 group-hover:text-slate-600 transition-colors ml-1" />
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content align="end" sideOffset={8} className="w-56 bg-white rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.08)] border border-slate-100 p-2 z-50 animate-in">
                <div className="px-3 py-3 mb-1 bg-slate-50 rounded-xl">
                  <p className="text-sm font-bold text-slate-800">{user.username}</p>
                  <p className="text-xs font-medium text-slate-500 mt-0.5">{user.email || user.roles?.join(', ')}</p>
                </div>
                <DropdownMenu.Separator className="h-px bg-slate-100 my-1.5 mx-1" />
                <DropdownMenu.Item onSelect={() => setSettingsOpen(true)} className="flex items-center gap-2.5 px-3 py-2.5 text-sm font-medium text-slate-600 rounded-xl cursor-pointer hover:bg-slate-50 hover:text-indigo-600 outline-none transition-colors">
                  <GearSix size={16} weight="duotone" /> Account Settings
                </DropdownMenu.Item>
                <DropdownMenu.Separator className="h-px bg-slate-100 my-1.5 mx-1" />
                <DropdownMenu.Item onClick={logout} className="flex items-center gap-2.5 px-3 py-2.5 text-sm font-medium text-red-600 rounded-xl cursor-pointer hover:bg-red-50 hover:text-red-700 outline-none transition-colors">
                  <SignOut size={16} weight="duotone" /> Sign Out
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
