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
  icon: React.ReactNode; color: string; bgColor: string; shadowColor: string
}

function StatCard({ label, value, sub, icon, color, bgColor, shadowColor }: StatCardProps) {
  return (
    <Card className={`group hover:shadow-[0_8px_30px_${shadowColor}] transition-all duration-300 border-t-4 hover:-translate-y-1`}
      style={{ borderTopColor: shadowColor.replace('0.15)', '0.6)') }}>
      <CardContent className="py-6 relative overflow-hidden">
        <div className={`absolute -right-4 -top-4 w-24 h-24 rounded-full blur-2xl opacity-40 ${bgColor} group-hover:opacity-70 transition-opacity duration-300`} />
        <div className="flex items-start justify-between relative z-10">
          <div>
            <p className="text-xs font-bold text-slate-500 capitalize mb-1">{label}</p>
            <p className="text-4xl font-black text-slate-900 mt-1 mb-1 tracking-tight">{value}</p>
            <p className="text-xs font-semibold text-slate-400">{sub}</p>
          </div>
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${bgColor} border border-white/50 shadow-sm`}>
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

    // WebSocket for live push updates — falls back to polling on error
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
        // Fall back to 30 s polling when WS drops
        if (!pollId) pollId = setInterval(() => load(), 30_000)
      }
      ws.onerror = () => ws?.close()
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'stats') setStats(msg.data)
          if (msg.type === 'inspection') {
            // Prepend new inspection to recent list (keep max 10)
            setRecent(prev => [msg.data as Inspection, ...prev].slice(0, 10))
            // Refresh full stats after a short delay so counts update
            setTimeout(load, 500)
          }
        } catch { /* ignore malformed frames */ }
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
    <div className="space-y-6 animate-in">
      <div className="flex items-center justify-between bg-white/40 p-3 rounded-2xl border border-slate-200/60 shadow-sm backdrop-blur-md">
        <p className="text-sm font-semibold text-slate-600 flex items-center gap-2.5 pl-2">
          <span className="relative flex h-2.5 w-2.5" title={wsConnected ? 'Live (WebSocket)' : 'Polling'}>
            {wsConnected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>}
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${wsConnected ? 'bg-indigo-500' : 'bg-slate-400'}`}></span>
          </span>
          Overview (Last 24 Hours)
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" onClick={() => load(true)} className="gap-2 bg-white hover:bg-slate-50 text-slate-700 border-slate-200 shadow-sm">
            <ArrowClockwise size={14} weight="bold" className={refreshing ? 'animate-spin' : ''} /> Refresh
          </Button>
          <Link to="/inspect">
            <Button variant="primary" size="sm" className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white shadow-[0_2px_10px_rgba(79,70,229,0.3)] border-transparent hover:shadow-[0_4px_15px_rgba(79,70,229,0.4)] transition-all">
              <Plus size={14} weight="bold" /> New Inspection
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        <StatCard
          label="Total Inspections" value={String(stats?.total_inspections ?? 0)}
          sub="Last 24 hours" icon={<Pulse size={24} weight="duotone" />}
          color="text-indigo-600" bgColor="bg-indigo-50" shadowColor="rgba(99,102,241,0.15)"
        />
        <StatCard
          label="Pass Rate" value={`${((stats?.pass_rate ?? 0) * 100).toFixed(1)}%`}
          sub={`${stats?.passed ?? 0} passed`} icon={<CheckCircle size={24} weight="duotone" />}
          color="text-emerald-600" bgColor="bg-emerald-50" shadowColor="rgba(16,185,129,0.15)"
        />
        <StatCard
          label="Defects Found" value={String((stats?.failed ?? 0) + (stats?.uncertain ?? 0))}
          sub={`${stats?.failed ?? 0} failed, ${stats?.uncertain ?? 0} uncertain`} icon={<WarningCircle size={24} weight="duotone" />}
          color="text-red-600" bgColor="bg-red-50" shadowColor="rgba(239,68,68,0.15)"
        />
        <StatCard
          label="Avg Cycle Time" value={`${(stats?.avg_inspection_time_ms ?? 0).toFixed(0)}ms`}
          sub="Per inspection" icon={<Timer size={24} weight="duotone" />}
          color="text-amber-600" bgColor="bg-amber-50" shadowColor="rgba(245,158,11,0.15)"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <Card className="col-span-2 flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center border border-indigo-100">
                <Pulse size={16} className="text-indigo-600" weight="bold" />
              </div>
              <div>
                <h2 className="text-lg font-extrabold text-slate-800 tracking-tight">Recent Inspections</h2>
                <p className="text-[11px] font-bold text-slate-500 capitalize mt-0.5">Latest 10 results</p>
              </div>
            </div>
            <Link to="/history" className="text-xs text-indigo-600 hover:text-indigo-700 font-bold flex items-center gap-1.5 px-3 py-2 rounded-lg hover:bg-indigo-50 transition-colors capitalize border border-transparent hover:border-indigo-100">
              View all <ArrowRight size={12} weight="bold" />
            </Link>
          </CardHeader>
          <div className="overflow-x-auto flex-1 p-2">
            {recent.length === 0 ? (
              <EmptyState title="No inspections yet" description="Upload an image to get started" />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    {['Time', 'Part ID', 'Decision', 'Objects', 'Cycle Time'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-[11px] font-extrabold text-slate-400 capitalize">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recent.map(item => (
                    <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50/80 transition-colors group">
                      <td className="px-4 py-4 text-slate-600 text-[13px] font-semibold">{new Date(item.timestamp).toLocaleTimeString()}</td>
                      <td className="px-4 py-4">
                        <span className="text-xs font-mono font-bold text-slate-700 bg-white border border-slate-200 px-2.5 py-1 rounded-md shadow-sm">{item.part_id || '—'}</span>
                      </td>
                      <td className="px-4 py-4"><DecisionBadge decision={item.decision} /></td>
                      <td className="px-4 py-4 text-slate-700 font-bold">{item.objects_found}</td>
                      <td className="px-4 py-4 text-slate-500 font-mono text-xs font-semibold">{item.total_time_ms ? <span className="px-2 py-1 rounded-md bg-white border border-slate-200 shadow-sm">{`${Math.round(item.total_time_ms)}ms`}</span> : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <div className="space-y-6">
          {stats && Object.keys(stats.defect_breakdown).length > 0 ? (
            <Card>
              <CardHeader>
                <div>
                  <h2 className="text-lg font-extrabold text-slate-800 tracking-tight">Defect Breakdown</h2>
                  <p className="text-[11px] font-bold text-slate-500 capitalize mt-0.5">{Object.keys(stats.defect_breakdown).length} distinct types</p>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-5">
                  {Object.entries(stats.defect_breakdown).sort((a, b) => b[1] - a[1]).map(([name, count]) => {
                    const max = Math.max(...Object.values(stats.defect_breakdown))
                    const percent = `${(count / max) * 100}%`
                    return (
                      <div key={name} className="group/item">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-xs font-bold text-slate-700 capitalize">{name}</span>
                          <span className="text-xs font-black text-white bg-red-500 px-2.5 py-0.5 rounded-md shadow-[0_2px_5px_rgba(239,68,68,0.3)]">{count}</span>
                        </div>
                        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200 shadow-inner">
                          <div
                            className="h-full bg-gradient-to-r from-red-500 to-rose-400 rounded-full transition-all duration-1000 ease-out relative"
                            style={{ width: percent }}
                          >
                            <div className="absolute top-0 right-0 bottom-0 w-10 bg-gradient-to-r from-transparent to-white/30" />
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent>
                <div className="py-8 text-center bg-gradient-to-b from-emerald-50/50 to-white rounded-xl border border-emerald-100/50">
                  <div className="w-16 h-16 rounded-2xl bg-emerald-100 flex items-center justify-center mx-auto mb-4 border border-emerald-200 shadow-sm relative">
                    <div className="absolute inset-0 bg-emerald-400 opacity-20 blur-xl rounded-full" />
                    <CheckCircle size={32} weight="duotone" className="text-emerald-600 relative z-10" />
                  </div>
                  <p className="text-sm font-extrabold text-slate-800 tracking-wide">No defects found</p>
                  <p className="text-[11px] mt-1 text-emerald-600 font-bold capitalize">100% yield in last 24h</p>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader><h2 className="text-lg font-extrabold text-slate-800 tracking-tight">Quick Actions</h2></CardHeader>
            <CardContent className="space-y-3 py-5">
              {[
                { to: '/inspect', label: 'Run Inspection', color: 'text-indigo-700 bg-indigo-50 border-indigo-100 hover:border-indigo-300 hover:bg-indigo-100 hover:shadow-[0_2px_10px_rgba(79,70,229,0.1)]' },
                { to: '/batch', label: 'Start Batch Job', color: 'text-amber-700 bg-amber-50 border-amber-100 hover:border-amber-300 hover:bg-amber-100 hover:shadow-[0_2px_10px_rgba(245,158,11,0.1)]' },
                { to: '/annotate', label: 'Review Queue', color: 'text-emerald-700 bg-emerald-50 border-emerald-100 hover:border-emerald-300 hover:bg-emerald-100 hover:shadow-[0_2px_10px_rgba(16,185,129,0.1)]' },
                { to: '/analytics', label: 'View Analytics', color: 'text-blue-700 bg-blue-50 border-blue-100 hover:border-blue-300 hover:bg-blue-100 hover:shadow-[0_2px_10px_rgba(59,130,246,0.1)]' },
              ].map(({ to, label, color }) => (
                <Link key={to} to={to} className="flex items-center justify-between p-3.5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 shadow-sm hover:shadow-md transition-all group">
                  <span className={`text-[11px] capitalize font-extrabold px-3 py-1.5 rounded-lg border transition-all ${color}`}>{label}</span>
                  <div className="w-8 h-8 rounded-full bg-slate-50 border border-slate-100 flex items-center justify-center group-hover:bg-white group-hover:scale-110 transition-all shadow-sm">
                    <ArrowRight size={14} weight="bold" className="text-slate-400 group-hover:text-slate-800 transition-colors" />
                  </div>
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
