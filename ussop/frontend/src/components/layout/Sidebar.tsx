import { NavLink } from 'react-router-dom'
import { SquaresFour, MagnifyingGlass, Clock, ChartBar, NotePencil, Stack, GearSix, Crosshair, Lightning, Bell, Factory } from '@phosphor-icons/react'
import { cn } from '@/lib/cn'

const nav = [
  { to: '/', label: 'Dashboard', icon: SquaresFour, end: true },
  { to: '/inspect', label: 'Inspect', icon: MagnifyingGlass },
  { to: '/history', label: 'History', icon: Clock },
  { to: '/analytics', label: 'Analytics', icon: ChartBar },
  { to: '/annotate', label: 'Annotate', icon: NotePencil },
  { to: '/batch', label: 'Batch', icon: Stack },
  { to: '/query', label: 'AI Query', icon: Lightning },
  { to: '/stations', label: 'Stations', icon: Factory },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/config', label: 'Settings', icon: GearSix },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-white/95 backdrop-blur-3xl border-r border-slate-200/80 flex flex-col z-30 select-none shadow-[10px_0_30px_rgba(0,0,0,0.02)]">
      {/* Brand */}
      <div className="px-6 py-7 border-b border-slate-100 relative overflow-hidden group">
        <div className="absolute inset-0 bg-gradient-to-r from-indigo-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
        <div className="flex items-center gap-3.5 relative z-10">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-[0_4px_15px_rgba(79,70,229,0.3)] border border-indigo-400/20 group-hover:scale-105 transition-transform duration-300">
            <Crosshair size={22} weight="fill" className="text-white drop-shadow-sm" />
          </div>
          <div>
            <span className="text-slate-900 font-extrabold text-xl tracking-tight">Ussop</span>
            <p className="text-[10px] font-bold text-indigo-500 leading-none mt-1 capitalize">Visual Inspector</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-4 py-6 overflow-y-auto scrollbar-thin">
        <p className="text-[10px] font-bold text-slate-400 capitalize px-3 mb-3">Navigation</p>
        <ul className="space-y-1.5">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) => cn(
                  'flex items-center gap-3.5 px-3 py-3 rounded-xl text-sm font-semibold transition-all duration-300 border group',
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 border-indigo-100/50 shadow-[0_2px_10px_rgba(79,70,229,0.06)]'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800 border-transparent hover:shadow-[0_2px_5px_rgba(0,0,0,0.01)]'
                )}
              >
                {({ isActive }) => (
                  <>
                    <span className={cn(
                      'flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-300',
                      isActive ? 'text-indigo-600 bg-white shadow-sm' : 'text-slate-400 group-hover:text-slate-600'
                    )}>
                      <Icon size={18} weight={isActive ? 'duotone' : 'regular'} />
                    </span>
                    {label}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="px-6 py-5 border-t border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]"></span>
          </div>
          <span className="text-xs font-semibold text-slate-500 capitalize">v1.0.0 · Production</span>
        </div>
      </div>
    </aside>
  )
}
