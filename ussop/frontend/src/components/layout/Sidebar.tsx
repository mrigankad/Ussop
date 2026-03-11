import { NavLink, useLocation } from 'react-router-dom'
import { SquaresFour, MagnifyingGlass, Clock, ChartBar, NotePencil, Stack, GearSix, Lightning, Bell, Factory, X, CaretDoubleLeft, CaretDoubleRight } from '@phosphor-icons/react'
import { cn } from '@/lib/cn'
import logo from '@/assets/logo.png'

const nav = [
  { to: '/', label: 'Dashboard', icon: SquaresFour, end: true },
  { to: '/inspect', label: 'Inspect', icon: MagnifyingGlass },
  { to: '/history', label: 'History', icon: Clock },
  { to: '/analytics', label: 'Analytics', icon: ChartBar },
  { to: '/annotate', label: 'Annotate', icon: NotePencil },
  { to: '/batch', label: 'Batch', icon: Stack },
  { to: '/query', label: 'AI Search', icon: Lightning },
  { to: '/stations', label: 'Stations', icon: Factory },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/config', label: 'Configuration', icon: GearSix },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
  collapsed?: boolean
  onToggleCollapse?: () => void
}

export default function Sidebar({ open, onClose, collapsed = false, onToggleCollapse }: SidebarProps) {
  const location = useLocation()

  return (
    <aside
      className={cn(
        'flex flex-col h-full w-full select-none font-sans',
        'border-r transition-all duration-300 ease-in-out'
      )}
      style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}
      aria-label="Main navigation"
    >
      {/* Brand */}
      <div className={cn("py-4 relative overflow-hidden group flex flex-col items-center", collapsed ? "px-2" : "px-6")}>
        {/* Mobile close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 rounded flex items-center justify-center lg:hidden hover:bg-slate-100 transition-colors z-20"
          aria-label="Close navigation"
          style={{ color: 'var(--muted)' }}
        >
          <X size={18} weight="bold" />
        </button>
        <div className="flex flex-col items-center text-center gap-2 relative z-10 w-full mt-2">
          <div className={cn("flex items-center justify-center transition-all duration-700 group-hover:scale-105", collapsed ? "w-10 h-10 mt-2" : "w-32 h-32")}>
            <img src={logo} alt="Logo" className="w-full h-full object-contain" />
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className={cn("flex-1 py-1 overflow-y-auto scrollbar-none", collapsed ? "px-3" : "px-6")} aria-label="Primary">
        {!collapsed && (
          <p className="text-[10px] font-semibold tracking-wider px-4 mb-3"
             style={{ color: 'var(--border)' }}>
            Navigation
          </p>
        )}
        <ul className="space-y-0.5">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                onClick={() => {
                  // Close sidebar on mobile after navigation
                  if (window.innerWidth < 1024) onClose()
                }}
                aria-current={location.pathname === to ? 'page' : undefined}
                className={({ isActive }) => cn(
                  'flex items-center gap-3.5 rounded text-[14px] font-semibold tracking-tight transition-all duration-300 border border-transparent group',
                  collapsed ? 'justify-center p-3 w-12 mx-auto' : 'px-5 py-2.5',
                  isActive
                    ? 'bg-olive-600 text-white shadow-md shadow-olive-900/10'
                    : 'hover:text-olive-700 hover:bg-olive-50'
                )}
                style={({ isActive }) => isActive ? {} : { color: 'var(--muted)' }}
                title={collapsed ? label : undefined}
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      size={20}
                      weight={isActive ? 'fill' : 'bold'}
                      className={cn(
                        'transition-all shrink-0',
                        isActive ? 'text-white' : 'text-slate-400 group-hover:text-olive-600'
                      )}
                    />
                    {!collapsed && <span className="truncate">{label}</span>}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse Toggle */}
      {onToggleCollapse && (
        <div className="p-3 border-t mt-auto hidden lg:flex" style={{ borderColor: 'var(--border-subtle)' }}>
          <button
            onClick={onToggleCollapse}
            className={cn(
              "w-full flex items-center p-3 rounded-xl transition-all text-slate-400 hover:text-olive-600 hover:bg-olive-50 active:scale-95 border border-transparent",
              collapsed ? "justify-center" : "justify-between"
            )}
            title={collapsed ? "Expand" : "Collapse"}
          >
            {!collapsed && <span className="text-[11px] font-bold tracking-wider ml-2">Collapse</span>}
            {collapsed ? <CaretDoubleRight size={20} weight="bold" /> : <CaretDoubleLeft size={20} weight="bold" />}
          </button>
        </div>
      )}


    </aside>
  )
}
