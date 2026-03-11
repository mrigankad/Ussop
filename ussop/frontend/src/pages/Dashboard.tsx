import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import type { Statistics, Inspection } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { DecisionBadge } from '@/components/shared/DecisionBadge'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/Button'
import { Plus, Pulse, CheckCircle, WarningCircle, Timer, ArrowRight, ArrowClockwise } from '@phosphor-icons/react'
import React from 'react'

interface StatCardProps {
  label: string; value: string; sub: string
  icon: React.ReactNode; color: string; bgColor: string; borderColor: string
}

function StatCard({ label, value, sub, icon, color, bgColor, borderColor }: StatCardProps) {
  return (
    <Card className={`group transition-all duration-300 border-t-2 ${borderColor}`}>
      <CardContent className="py-6 sm:py-8 relative overflow-hidden">
        <div className="flex items-start justify-between relative z-10">
          <div>
            <p className="text-[11px] font-bold mb-2" style={{ color: 'var(--muted)' }}>{label}</p>
            <p className="text-3xl sm:text-4xl font-bold mt-1 mb-2 tracking-tighter"
               style={{ color: 'var(--text)' }}>{value}</p>
            <p className="text-[11px] font-bold" style={{ color: 'var(--muted)' }}>{sub}</p>
          </div>
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${bgColor} border`}
               style={{ borderColor: 'var(--border-subtle)' }}>
            <span className={color}>{icon}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<Statistics | null>(null)
  const [recent, setRecent] = useState<Inspection[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)

  async function load(showRefresh = false) {
    if (showRefresh) setRefreshing(true)
    try {
      const [s, r] = await Promise.all([api.getStatistics(24), api.getInspections({ limit: 10 })])
      setStats(s); setRecent(r.items)
    } catch (e) { console.error(e) }
    finally { setLoading(false); setRefreshing(false) }
  }

  useEffect(() => {
    load()

    const token = localStorage.getItem('access_token') ?? ''
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.host}/ws/dashboard?token=${token}`
    let ws: WebSocket | null = null
    let pollId: ReturnType<typeof setInterval> | null = null

    function connectWs() {
      ws = new WebSocket(wsUrl)
      ws.onopen = () => setWsConnected(true)
      ws.onclose = () => {
        setWsConnected(false)
        if (!pollId) pollId = setInterval(() => load(), 30_000)
      }
      ws.onerror = () => ws?.close()
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'stats') setStats(msg.data)
          if (msg.type === 'inspection') {
            setRecent(prev => [msg.data as Inspection, ...prev].slice(0, 10))
            setTimeout(load, 500)
          }
        } catch { }
      }
    }

    connectWs()

    return () => {
      ws?.close()
      if (pollId) clearInterval(pollId)
    }
  }, [])

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-6 sm:space-y-8 lg:space-y-10 animate-in font-sans pb-12">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 py-4 sm:py-5 rounded-xl sm:rounded-2xl border backdrop-blur-md"
           style={{ background: 'color-mix(in srgb, var(--surface) 40%, transparent)', borderColor: 'var(--border-subtle)' }}>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 border px-4 sm:px-5 py-2.5 rounded-xl shadow-sm"
               style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
            <span className="relative flex h-2 w-2">
              {wsConnected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-olive-400 opacity-75"></span>}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${wsConnected ? 'bg-olive-600' : 'bg-slate-300'}`}></span>
            </span>
            <span className="text-[11px] font-semibold tracking-tight"
                  style={{ color: 'var(--text)' }}>Dashboard</span>
          </div>
          <span className="text-[10px] font-bold tracking-wider hidden md:block"
                style={{ color: 'var(--muted)' }}>Real-time updates</span>
        </div>
        <div className="flex gap-3 sm:gap-4 w-full sm:w-auto">
          <Button variant="secondary" size="sm" onClick={() => load(true)}
                  className="gap-2 text-[11px] font-semibold py-3 px-4 sm:px-6 rounded-xl transition-all active:scale-95 shadow-sm flex-1 sm:flex-initial">
            <ArrowClockwise size={14} weight="bold" className={refreshing ? 'animate-spin' : ''} /> Refresh
          </Button>
          <Link to="/inspect" className="flex-1 sm:flex-initial">
            <Button variant="primary" size="sm"
                    className="gap-2 text-[11px] font-semibold py-3 px-4 sm:px-8 rounded-xl border-transparent transition-all active:scale-95 shadow-lg shadow-olive-900/10 w-full">
              <Plus size={14} weight="bold" /> New Inspection
            </Button>
          </Link>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <StatCard
          label="Total Inspections" value={String(stats?.total_inspections ?? 0)}
          sub="Last 24 Hours" icon={<Pulse size={24} weight="bold" />}
          color="text-olive-600" bgColor="bg-olive-50" borderColor="border-olive-200"
        />
        <StatCard
          label="Pass Rate" value={`${((stats?.pass_rate ?? 0) * 100).toFixed(1)}%`}
          sub={`${stats?.passed ?? 0} Passed`} icon={<CheckCircle size={24} weight="bold" />}
          color="text-emerald-600" bgColor="bg-emerald-50" borderColor="border-emerald-200"
        />
        <StatCard
          label="Issues Found" value={String((stats?.failed ?? 0) + (stats?.uncertain ?? 0))}
          sub={`${stats?.failed ?? 0} Failed`} icon={<WarningCircle size={24} weight="bold" />}
          color="text-red-600" bgColor="bg-red-50" borderColor="border-red-200"
        />
        <StatCard
          label="Avg. Cycle Time" value={`${(stats?.avg_inspection_time_ms ?? 0).toFixed(0)}ms`}
          sub="Processing Speed" icon={<Timer size={24} weight="bold" />}
          color="text-amber-600" bgColor="bg-amber-50" borderColor="border-amber-200"
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8 lg:gap-10">
        {/* Recent Inspections Table */}
        <Card className="lg:col-span-2 overflow-hidden">
          <CardHeader className="p-6 sm:p-8 lg:p-10 border-none flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4 sm:gap-6">
              <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center border shadow-sm transition-transform hover:rotate-6 duration-500"
                   style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
                <Pulse size={24} weight="bold" style={{ color: 'var(--text)' }} />
              </div>
              <div className="flex flex-col">
                <h2 className="text-lg sm:text-xl font-semibold tracking-tight leading-none mb-2"
                    style={{ color: 'var(--text)' }}>Recent Inspections</h2>
                <p className="text-[11px] font-bold tracking-wider"
                   style={{ color: 'var(--muted)' }}>Recent activity and results</p>
              </div>
            </div>
            <Link to="/history" className="text-[11px] font-semibold text-olive-600 hover:text-white flex items-center gap-2.5 px-5 sm:px-6 py-3 rounded-xl bg-olive-50 hover:bg-olive-600 transition-all border border-olive-100/50 shadow-sm active:scale-95 group">
              View All <ArrowRight size={14} weight="bold" className="group-hover:translate-x-1 transition-transform" />
            </Link>
          </CardHeader>
          <div className="px-4 sm:px-6 pb-4 sm:pb-6">
            <div className="rounded-xl sm:rounded-2xl border p-2"
                 style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
              {recent.length === 0 ? (
                <div className="py-20">
                  <EmptyState title="No Inspections Yet" description="Run your first inspection to see results here" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left min-w-[600px]">
                    <thead>
                      <tr>
                        {['Part ID', 'Decision', 'Items', 'Cycle Time', 'Timestamp'].map(h => (
                          <th key={h} className="px-4 sm:px-6 lg:px-8 py-4 sm:py-5 text-[10px] font-semibold tracking-wider"
                              style={{ color: 'var(--muted)' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {recent.map(item => (
                        <tr key={item.id} className="hover:bg-[var(--surface)] transition-all group cursor-default border-b last:border-none" style={{ borderColor: 'var(--border-subtle)' }}>
                          <td className="px-4 sm:px-6 lg:px-8 py-5 sm:py-7 font-mono text-[11px] font-semibold tracking-tighter"
                              style={{ color: 'var(--text)' }}>{item.part_id || 'N/A'}</td>
                          <td className="px-4 sm:px-6 lg:px-8 py-5 sm:py-7"><DecisionBadge decision={item.decision} /></td>
                          <td className="px-4 sm:px-6 lg:px-8 py-5 sm:py-7">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold" style={{ color: 'var(--text)' }}>{item.objects_found}</span>
                              <span className="text-[10px] font-bold tracking-tighter" style={{ color: 'var(--muted)' }}>Objects</span>
                            </div>
                          </td>
                          <td className="px-4 sm:px-6 lg:px-8 py-5 sm:py-7 font-mono text-xs font-bold" style={{ color: 'var(--muted)' }}>
                            {item.total_time_ms ? `${Math.round(item.total_time_ms)}ms` : '—'}
                          </td>
                          <td className="px-4 sm:px-6 lg:px-8 py-5 sm:py-7 text-[11px] font-semibold" style={{ color: 'var(--muted)' }}>
                            {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Right sidebar */}
        <div className="space-y-6 sm:space-y-8 lg:space-y-10">
          {/* Defect Breakdown */}
          {stats && Object.keys(stats.defect_breakdown).length > 0 ? (
            <Card>
              <CardHeader className="p-6 sm:p-8 lg:p-10 border-none">
                <div className="flex flex-col">
                  <h2 className="text-lg sm:text-xl font-semibold tracking-tight leading-none mb-2"
                      style={{ color: 'var(--text)' }}>Defect Breakdown</h2>
                  <p className="text-[11px] font-bold tracking-wider"
                     style={{ color: 'var(--muted)' }}>Distribution of issues</p>
                </div>
              </CardHeader>
              <CardContent className="px-6 sm:px-8 lg:px-10 pb-6 sm:pb-8 lg:pb-10 pt-0">
                <div className="space-y-6 sm:space-y-8">
                  {Object.entries(stats.defect_breakdown).sort((a, b) => b[1] - a[1]).map(([name, count]) => {
                    const max = Math.max(...Object.values(stats.defect_breakdown))
                    const percent = `${(count / max) * 100}%`
                    return (
                      <div key={name} className="group flex items-center gap-4">
                        <span className="w-24 truncate text-xs font-semibold tracking-tighter"
                              style={{ color: 'var(--text)' }}>{name}</span>
                        <div className="flex-1 h-2 rounded-full overflow-hidden border"
                             style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
                          <div
                            className="h-full bg-gradient-to-r from-red-500 to-red-600 rounded-full transition-all duration-1000 ease-out"
                            style={{ width: percent }}
                          />
                        </div>
                        <span className="w-8 text-right text-[10px] font-semibold text-white bg-red-600 px-2.5 py-1 rounded-full shadow-sm">{count}</span>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-6 sm:p-8 lg:p-10">
                <div className="py-12 sm:py-16 text-center rounded-xl sm:rounded-2xl border transition-all"
                     style={{ background: 'color-mix(in srgb, #059669 5%, var(--surface))', borderColor: 'var(--border-subtle)' }}>
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl shadow-lg flex items-center justify-center mx-auto mb-6 sm:mb-8 border transition-transform hover:scale-110 duration-500"
                       style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
                    <CheckCircle size={36} weight="bold" className="text-emerald-600" />
                  </div>
                  <h3 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text)' }}>All Systems Clear</h3>
                  <p className="text-[11px] mt-2 text-emerald-600 font-bold tracking-wider">Pass Rate Confidence 100%</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Quick Actions */}
          <Card>
            <CardHeader className="px-6 sm:px-8 lg:px-10 pt-6 sm:pt-8 lg:pt-10 pb-4 border-none">
              <h2 className="text-[10px] font-semibold tracking-wider" style={{ color: 'var(--muted)' }}>Quick Actions</h2>
            </CardHeader>
            <CardContent className="px-6 sm:px-8 pb-6 sm:pb-8 pt-4 space-y-3 sm:space-y-4">
              {[
                { to: '/inspect', label: 'New Inspection', icon: <ArrowRight size={14} weight="bold" />, color: 'bg-olive-600 text-white hover:bg-olive-700 shadow-olive-900/10' },
                { to: '/batch', label: 'Batch Processing', icon: <ArrowRight size={14} weight="bold" />, color: 'bg-slate-900 text-white hover:bg-black shadow-slate-900/20' },
                { to: '/annotate', label: 'Label Samples', icon: <ArrowRight size={14} weight="bold" />, classes: 'border' },
              ].map(({ to, label, icon, color, classes }) => (
                <Link key={to} to={to}
                      className={`flex items-center justify-between px-5 sm:px-6 py-4 sm:py-5 rounded-xl transition-all border border-transparent font-semibold tracking-tight text-xs shadow-md active:scale-95 group ${color || ''} ${classes || ''}`}
                      style={classes ? { background: 'var(--surface-2)', color: 'var(--text-2)', borderColor: 'var(--border-subtle)' } : undefined}>
                  {label}
                  <div className="group-hover:translate-x-1 transition-transform">{icon}</div>
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
