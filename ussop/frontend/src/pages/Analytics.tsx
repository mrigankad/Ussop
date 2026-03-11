import { useEffect, useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { Statistics, TrendData } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { ArrowClockwise, DownloadSimple, FunnelSimple } from '@phosphor-icons/react'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, LineElement, PointElement,
  Title, Tooltip, Legend, ArcElement, Filler,
} from 'chart.js'
import { Bar, Line, Doughnut, Chart } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement, PointElement,
  Title, Tooltip, Legend, ArcElement, Filler,
)

const RANGES = [
  { label: '6h',  hours: 6,   interval: 'hour' },
  { label: '24h', hours: 24,  interval: 'hour' },
  { label: '7d',  hours: 168, interval: 'day'  },
  { label: '30d', hours: 720, interval: 'day'  },
]

const CHART_COLORS = {
  pass:      { solid: '#059669', bg: 'rgba(5,150,105,0.12)'  },
  fail:      { solid: '#dc2626', bg: 'rgba(220,38,38,0.12)'  },
  uncertain: { solid: '#d97706', bg: 'rgba(217,119,6,0.12)'  },
  time:      { solid: '#6366f1', bg: 'rgba(99,102,241,0.10)' },
}

function StatCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent: string }) {
  return (
    <Card className={`border-l-4`} style={{ borderLeftColor: accent }}>
      <CardContent className="py-5">
        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">{label}</p>
        <p className="text-3xl font-black text-slate-900 mt-1 tracking-tight">{value}</p>
        {sub && <p className="text-xs font-semibold text-slate-400 mt-1">{sub}</p>}
      </CardContent>
    </Card>
  )
}

export default function Analytics() {
  const [rangeIdx, setRangeIdx]     = useState(1)
  const [station, setStation]       = useState('')
  const [stations, setStations]     = useState<string[]>([])
  const [stats, setStats]           = useState<Statistics | null>(null)
  const [trend, setTrend]           = useState<TrendData | null>(null)
  const [loading, setLoading]       = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    else setLoading(true)
    try {
      const { hours, interval } = RANGES[rangeIdx]
      const params: Record<string, string | number> = { hours, limit: 1000 }
      if (station) params.station_id = station
      const [s, t, hist] = await Promise.all([
        api.getStatistics(hours),
        api.getTrends(hours, interval),
        api.getInspections(params),
      ])
      setStats(s)
      setTrend(t)
      // Extract unique station IDs for the filter dropdown
      const ids = [...new Set(hist.items.map(i => i.station_id).filter(Boolean))]
      if (ids.length > 1) setStations(ids)
    } catch (e) { console.error(e) }
    finally { setLoading(false); setRefreshing(false) }
  }, [rangeIdx, station])

  useEffect(() => { load() }, [load])

  if (loading) return <LoadingSpinner />

  const passRate = ((stats?.pass_rate ?? 0) * 100).toFixed(1)
  const failRate = (((stats?.failed ?? 0) / Math.max(stats?.total_inspections ?? 1, 1)) * 100).toFixed(1)
  const defects  = Object.entries(stats?.defect_breakdown ?? {}).sort((a, b) => b[1] - a[1])
  const total    = defects.reduce((s, [, v]) => s + v, 0)

  // Pareto data: counts + cumulative %
  const paretoLabels = defects.map(([n]) => n)
  const paretoCounts = defects.map(([, v]) => v)
  let cum = 0
  const paretoCumPct = paretoCounts.map(v => { cum += v; return total > 0 ? Math.round((cum / total) * 100) : 0 })

  const trendOpts = {
    responsive: true, maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    plugins: { legend: { position: 'bottom' as const, labels: { boxWidth: 12, font: { size: 11 } } } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 10 } } },
      y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { size: 10 } } },
    },
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Toolbar */}
      <div className="flex items-center justify-between bg-white/40 p-3 rounded-2xl border border-slate-200/60 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-2">
          {RANGES.map((opt, i) => (
            <button key={opt.label} onClick={() => setRangeIdx(i)}
              className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all ${
                rangeIdx === i
                  ? 'bg-indigo-600 text-white shadow-[0_2px_8px_rgba(79,70,229,0.3)]'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}>
              {opt.label}
            </button>
          ))}
          {stations.length > 0 && (
            <div className="flex items-center gap-1.5 ml-2 pl-2 border-l border-slate-200">
              <FunnelSimple size={13} className="text-slate-400" />
              <select value={station} onChange={e => setStation(e.target.value)}
                className="text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300">
                <option value="">All stations</option>
                {stations.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button onClick={() => load(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 shadow-sm transition-all">
            <ArrowClockwise size={12} weight="bold" className={refreshing ? 'animate-spin' : ''} /> Refresh
          </button>
          <a href={api.exportCsv()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 shadow-sm transition-all">
            <DownloadSimple size={12} weight="bold" /> Export CSV
          </a>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-5">
        <StatCard label="Total Inspections" value={String(stats?.total_inspections ?? 0)}
          sub={`Last ${RANGES[rangeIdx].label}`} accent="#6366f1" />
        <StatCard label="Pass Rate" value={`${passRate}%`}
          sub={`${stats?.passed ?? 0} passed`} accent="#059669" />
        <StatCard label="Fail Rate" value={`${failRate}%`}
          sub={`${stats?.failed ?? 0} failed`} accent="#dc2626" />
        <StatCard label="Avg Cycle Time" value={`${(stats?.avg_inspection_time_ms ?? 0).toFixed(0)}ms`}
          sub="Per inspection" accent="#d97706" />
      </div>

      {/* Volume + Decision split */}
      <div className="grid grid-cols-3 gap-6">
        <Card className="col-span-2">
          <CardHeader>
            <h2 className="text-base font-extrabold text-slate-800">Inspection Volume</h2>
            <p className="text-[11px] font-bold text-slate-400">Pass vs. fail over time</p>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <Bar data={{
                labels: trend?.labels ?? [],
                datasets: [
                  { label: 'Passed', data: trend?.passed ?? [], backgroundColor: CHART_COLORS.pass.solid, borderRadius: 3, stack: 'a' },
                  { label: 'Failed', data: trend?.failed ?? [], backgroundColor: CHART_COLORS.fail.solid, borderRadius: 3, stack: 'a' },
                ],
              }} options={trendOpts} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-base font-extrabold text-slate-800">Decision Split</h2>
            <p className="text-[11px] font-bold text-slate-400">{stats?.total_inspections ?? 0} total</p>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center">
              <Doughnut
                data={{
                  labels: ['Passed', 'Failed', 'Uncertain'],
                  datasets: [{
                    data: [stats?.passed ?? 0, stats?.failed ?? 0, stats?.uncertain ?? 0],
                    backgroundColor: [CHART_COLORS.pass.solid, CHART_COLORS.fail.solid, CHART_COLORS.uncertain.solid],
                    borderWidth: 2, borderColor: '#fff',
                  }],
                }}
                options={{
                  responsive: true, maintainAspectRatio: false,
                  cutout: '65%',
                  plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
                }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cycle time trend */}
      {trend?.avg_time_ms && trend.avg_time_ms.some(v => v > 0) && (
        <Card>
          <CardHeader>
            <h2 className="text-base font-extrabold text-slate-800">Cycle Time Trend</h2>
            <p className="text-[11px] font-bold text-slate-400">Average inspection latency (ms)</p>
          </CardHeader>
          <CardContent>
            <div className="h-48">
              <Line data={{
                labels: trend.labels,
                datasets: [{
                  label: 'Avg ms', data: trend.avg_time_ms,
                  borderColor: CHART_COLORS.time.solid, backgroundColor: CHART_COLORS.time.bg,
                  fill: true, tension: 0.4, pointRadius: 3, pointHoverRadius: 5,
                }],
              }} options={trendOpts} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pass-rate trend line */}
      {(trend?.passed?.length ?? 0) > 1 && (
        <Card>
          <CardHeader>
            <h2 className="text-base font-extrabold text-slate-800">Pass Rate Over Time</h2>
            <p className="text-[11px] font-bold text-slate-400">% passing per time bucket</p>
          </CardHeader>
          <CardContent>
            <div className="h-48">
              <Line data={{
                labels: trend!.labels,
                datasets: [{
                  label: 'Pass rate %',
                  data: trend!.total.map((t, i) => t > 0 ? Math.round(((trend!.passed[i] ?? 0) / t) * 100) : null),
                  borderColor: CHART_COLORS.pass.solid, backgroundColor: CHART_COLORS.pass.bg,
                  fill: true, tension: 0.4, pointRadius: 3, pointHoverRadius: 5,
                  spanGaps: true,
                }],
              }} options={{
                ...trendOpts,
                scales: {
                  ...trendOpts.scales,
                  y: { ...trendOpts.scales.y, min: 0, max: 100, ticks: { callback: (v: any) => `${v}%`, font: { size: 10 } } },
                },
              }} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pareto chart */}
      {defects.length > 0 && (
        <Card>
          <CardHeader>
            <div>
              <h2 className="text-base font-extrabold text-slate-800">Defect Pareto</h2>
              <p className="text-[11px] font-bold text-slate-400">
                Defect frequency with cumulative % — focus on the left side
              </p>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <Chart
                type="bar"
                data={{
                  labels: paretoLabels,
                  datasets: [
                    {
                      type: 'bar' as const,
                      label: 'Count',
                      data: paretoCounts,
                      backgroundColor: CHART_COLORS.fail.solid,
                      borderRadius: 4,
                      yAxisID: 'y',
                    },
                    {
                      type: 'line' as const,
                      label: 'Cumulative %',
                      data: paretoCumPct,
                      borderColor: '#6366f1',
                      backgroundColor: 'transparent',
                      borderWidth: 2,
                      pointRadius: 4,
                      tension: 0.1,
                      yAxisID: 'y2',
                    },
                  ],
                } as any}
                options={{
                  responsive: true, maintainAspectRatio: false,
                  interaction: { mode: 'index', intersect: false },
                  plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
                  scales: {
                    x: { grid: { display: false }, ticks: { font: { size: 10 } } },
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { size: 10 } }, position: 'left' },
                    y2: {
                      beginAtZero: true, max: 100, position: 'right', grid: { drawOnChartArea: false },
                      ticks: { callback: (v: any) => `${v}%`, font: { size: 10 } },
                    },
                  },
                } as any}
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
