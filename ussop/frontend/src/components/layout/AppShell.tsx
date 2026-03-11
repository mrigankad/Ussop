import { Outlet, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AppShell() {
  const token = localStorage.getItem('access_token')
  if (!token) return <Navigate to="/login" replace />

  return (
    <div className="flex h-screen bg-transparent text-slate-800 overflow-hidden selection:bg-indigo-500/20">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden ml-64 relative z-10">
        <Header />
        <main className="flex-1 overflow-y-auto p-8 pt-6 relative scrollbar-thin">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
