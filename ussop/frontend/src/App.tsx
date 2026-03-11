// Forced reload for UI sync
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppShell from '@/components/layout/AppShell'
import { ToastProvider } from '@/components/ui/Toast'
import { Toaster } from 'sonner'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Inspect from '@/pages/Inspect'
import History from '@/pages/History'
import Analytics from '@/pages/Analytics'
import Annotate from '@/pages/Annotate'
import Batch from '@/pages/Batch'
import Config from '@/pages/Config'
import Query from '@/pages/Query'
import Alerts from '@/pages/Alerts'
import Stations from '@/pages/Stations'

export default function App() {
  return (
    <ToastProvider>
      <Toaster position="top-right" richColors theme="system" />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<AppShell />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inspect" element={<Inspect />} />
            <Route path="/history" element={<History />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/annotate" element={<Annotate />} />
            <Route path="/batch" element={<Batch />} />
            <Route path="/query" element={<Query />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/stations" element={<Stations />} />
            <Route path="/config" element={<Config />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
