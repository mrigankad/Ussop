import { useState } from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AppShell() {
  const token = localStorage.getItem('access_token')
  if (!token) return <Navigate to="/login" replace />

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true')

  function toggleCollapse() {
    setCollapsed(v => {
      const next = !v;
      localStorage.setItem('sidebar_collapsed', String(next));
      return next;
    });
  }

  return (
    <div className="h-screen w-full flex p-2 sm:p-4 font-sans selection:bg-olive-500/20"
         style={{ background: 'var(--bg)' }}>
      <div className="flex flex-1 w-full h-full rounded-2xl sm:rounded-[20px] overflow-hidden border relative shadow-2xl shadow-slate-900/5 transition-all"
           style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }}>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-white focus:text-black">Skip to content</a>

        {/* Mobile overlay backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 lg:hidden overflow-hidden transition-opacity"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Sidebar Wrapper */}
        <div className={`fixed lg:static inset-y-0 left-0 z-50 ${collapsed ? 'w-20' : 'w-72'} shrink-0 h-full transform transition-all duration-300 ease-in-out lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} collapsed={collapsed} onToggleCollapse={toggleCollapse} />
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative z-10 bg-transparent">
          <Header onMenuClick={() => setSidebarOpen(v => !v)} />
          <main
            id="main-content"
            role="main"
            className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 w-full scrollbar-thin"
            style={{ background: 'var(--surface-2)' }}
          >
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
