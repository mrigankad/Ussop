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
    <Card className="hover:-translate-y-0.5 hover: transition-all duration-200">
      <CardHeader>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-olive-50 border border-olive-100 flex items-center justify-center">
            <Factory size={16} className="text-olive-600" weight="bold" />
          </div>
          <div>
            <h3 className="text-sm font-bold" style={{ color: 'var(--text)' }}>{s.station_id}</h3>
            {s.last_time && (
              <p className="text-[10px] font-medium" style={{ color: 'var(--muted)' }}>
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
            { label: 'Total Inspections', value: String(s.stats.total_inspections ?? 0), icon: <Pulse size={13} className="text-olive-500" weight="bold" /> },
            { label: 'Pass Rate %',       value: `${passRate.toFixed(1)}%`,               icon: <CheckCircle size={13} className="text-emerald-500" weight="bold" /> },
            { label: 'Defects',           value: String((s.stats.failed ?? 0) + (s.stats.uncertain ?? 0)), icon: <WarningCircle size={13} className="text-red-500" weight="bold" /> },
            { label: 'Avg Cycle time',    value: `${(s.stats.avg_inspection_time_ms ?? 0).toFixed(0)}ms`, icon: <Timer size={13} className="text-amber-500" weight="bold" /> },
          ].map(({ label, value, icon }) => (
            <div key={label} className="rounded-xl px-4 py-3 border transition-colors" style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
              <div className="flex items-center gap-1.5 mb-1.5">{icon}<span className="text-[10px] font-bold text-slate-400 tracking-tight">{label}</span></div>
              <p className="text-lg font-semibold tracking-tighter" style={{ color: 'var(--text)' }}>{value}</p>
            </div>
          ))}
        </div>

        {s.last_decision && (
          <div className="flex items-center justify-between px-4 py-3 border rounded-xl" style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
            <span className="text-[11px] font-bold" style={{ color: 'var(--muted)' }}>Last Result</span>
            <DecisionBadge decision={s.last_decision as any} />
          </div>
        )}

        {Object.keys(s.stats.defect_breakdown).length > 0 && (
          <div className="mt-4 space-y-2">
            <div className="flex justify-between items-center px-1 mb-1">
              <span className="text-[10px] font-bold" style={{ color: 'var(--muted)' }}>Defect Types</span>
            </div>
            {Object.entries(s.stats.defect_breakdown)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 3)
              .map(([name, count]) => {
                const max = Math.max(...Object.values(s.stats.defect_breakdown))
                return (
                  <div key={name} className="flex items-center gap-3">
                    <span className="text-[10px] font-bold w-24 truncate" style={{ color: 'var(--text-2)' }}>{name}</span>
                    <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--surface-2)' }}>
                      <div className="h-full bg-red-400/80 rounded-full" style={{ width: `${(count / max) * 100}%` }} />
                    </div>
                    <span className="text-[10px] font-bold w-4 text-right" style={{ color: 'var(--muted)' }}>{count}</span>
                  </div>
                )
              })}
          </div>
        )}

        <Link
          to={`/history?station_id=${encodeURIComponent(s.station_id)}`}
          className="mt-6 flex items-center justify-between px-4 py-3 rounded-xl bg-olive-50/50 text-olive-700 hover:bg-olive-50 transition-all text-[11px] font-bold group border border-olive-100/50"
        >
          View History
          <ArrowRight size={12} weight="bold" className="group-hover:translate-x-1 transition-transform" />
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
      <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-2xl border backdrop-blur-md gap-4" style={{ background: 'color-mix(in srgb, var(--surface) 40%, transparent)', borderColor: 'var(--border-subtle)' }}>
        <p className="text-sm font-bold flex items-center gap-3 pl-2" style={{ color: 'var(--text)' }}>
          <Factory size={18} className="text-olive-600" weight="bold" />
          Stations
        </p>
        <span className="text-[11px] font-bold border px-4 py-2 rounded-lg shadow-sm" style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' }}>
          {stations.length} Station{stations.length !== 1 ? 's' : ''} Online
        </span>
      </div>

      {stations.length === 0 ? (
        <EmptyState
          title="No Active Stations Found"
          description="Initialize inspections with station identifiers to populate this dashboard"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
          {stations.map(s => <StationCard key={s.station_id} s={s} />)}
        </div>
      )}
    </div>
  )
}
