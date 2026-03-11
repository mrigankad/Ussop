import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Statistics } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { DecisionBadge } from '@/components/shared/DecisionBadge'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { Factory, CheckCircle, WarningCircle, Timer, Pulse, ArrowRight } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'

interface StationSummary {
  station_id: string
  stats: Statistics
  last_decision: string | null
  last_time: string | null
}

function StatusDot({ rate }: { rate: number }) {
  const color = rate >= 0.95 ? 'bg-emerald-500' : rate >= 0.85 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${color}`} />
      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${color}`} />
    </span>
  )
}

function StationCard({ s }: { s: StationSummary }) {
  const passRate = (s.stats.pass_rate ?? 0) * 100
  const health   = passRate >= 95 ? 'Healthy' : passRate >= 85 ? 'Warning' : 'Critical'
  const healthColor = passRate >= 95
    ? 'text-emerald-700 bg-emerald-50 border-emerald-100'
    : passRate >= 85
    ? 'text-amber-700 bg-amber-50 border-amber-100'
    : 'text-red-700 bg-red-50 border-red-100'

  return (
    <Card className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
      <CardHeader>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <Factory size={16} className="text-indigo-600" weight="bold" />
          </div>
          <div>
            <h3 className="text-sm font-extrabold text-slate-800">{s.station_id}</h3>
            {s.last_time && (
              <p className="text-[10px] font-medium text-slate-400">
                Last: {new Date(s.last_time).toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusDot rate={s.stats.pass_rate ?? 0} />
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${healthColor}`}>{health}</span>
        </div>
      </CardHeader>

      <CardContent className="pt-0 pb-5">
        <div className="grid grid-cols-2 gap-3 mb-4">
          {[
            { label: 'Inspections', value: String(s.stats.total_inspections ?? 0), icon: <Pulse size={13} className="text-indigo-500" weight="bold" /> },
            { label: 'Pass Rate',   value: `${passRate.toFixed(1)}%`,               icon: <CheckCircle size={13} className="text-emerald-500" weight="bold" /> },
            { label: 'Defects',     value: String((s.stats.failed ?? 0) + (s.stats.uncertain ?? 0)), icon: <WarningCircle size={13} className="text-red-500" weight="bold" /> },
            { label: 'Avg Time',    value: `${(s.stats.avg_inspection_time_ms ?? 0).toFixed(0)}ms`, icon: <Timer size={13} className="text-amber-500" weight="bold" /> },
          ].map(({ label, value, icon }) => (
            <div key={label} className="bg-slate-50 rounded-xl px-3 py-2.5 border border-slate-100">
              <div className="flex items-center gap-1.5 mb-1">{icon}<span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">{label}</span></div>
              <p className="text-lg font-black text-slate-800 tracking-tight">{value}</p>
            </div>
          ))}
        </div>

        {s.last_decision && (
          <div className="flex items-center justify-between px-3 py-2 bg-white border border-slate-100 rounded-xl">
            <span className="text-[11px] font-bold text-slate-500">Last result</span>
            <DecisionBadge decision={s.last_decision as any} />
          </div>
        )}

        {Object.keys(s.stats.defect_breakdown).length > 0 && (
          <div className="mt-3 space-y-1.5">
            {Object.entries(s.stats.defect_breakdown)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 3)
              .map(([name, count]) => {
                const max = Math.max(...Object.values(s.stats.defect_breakdown))
                return (
                  <div key={name} className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-slate-600 w-20 truncate capitalize">{name}</span>
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-red-400 rounded-full" style={{ width: `${(count / max) * 100}%` }} />
                    </div>
                    <span className="text-[10px] font-black text-slate-500 w-4 text-right">{count}</span>
                  </div>
                )
              })}
          </div>
        )}

        <Link
          to={`/history?station_id=${encodeURIComponent(s.station_id)}`}
          className="mt-3 flex items-center justify-between px-3 py-2 rounded-xl bg-indigo-50 border border-indigo-100 hover:bg-indigo-100 hover:border-indigo-200 transition-all text-[11px] font-bold text-indigo-700 group"
        >
          View history
          <ArrowRight size={11} weight="bold" className="group-hover:translate-x-0.5 transition-transform" />
        </Link>
      </CardContent>
    </Card>
  )
}

export default function Stations() {
  const [stations, setStations] = useState<StationSummary[]>([])
  const [loading, setLoading]   = useState(true)

  async function load() {
    setLoading(true)
    try {
      // Get last 500 inspections to discover all active stations
      const hist = await api.getInspections({ limit: 500 })
      const ids = [...new Set(hist.items.map(i => i.station_id).filter(Boolean))]

      if (ids.length === 0) {
        setStations([])
        return
      }

      const results = await Promise.all(
        ids.map(async id => {
          const stats = await api.getStatistics(24)   // per-station filter not yet in API wrapper
          const last = hist.items.find(i => i.station_id === id)
          return {
            station_id: id,
            stats,
            last_decision: last?.decision ?? null,
            last_time: last?.timestamp ?? null,
          } as StationSummary
        })
      )

      setStations(results.sort((a, b) => a.station_id.localeCompare(b.station_id)))
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-center justify-between bg-white/40 p-3 rounded-2xl border border-slate-200/60 shadow-sm backdrop-blur-md">
        <p className="text-sm font-semibold text-slate-600 flex items-center gap-2.5 pl-2">
          <Factory size={16} className="text-indigo-500" weight="bold" />
          Multi-Station Overview
        </p>
        <span className="text-xs font-bold text-slate-400 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-sm">
          {stations.length} station{stations.length !== 1 ? 's' : ''} active
        </span>
      </div>

      {stations.length === 0 ? (
        <EmptyState
          title="No stations found"
          description="Run inspections with different station_id values to see them here"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {stations.map(s => <StationCard key={s.station_id} s={s} />)}
        </div>
      )}
    </div>
  )
}
