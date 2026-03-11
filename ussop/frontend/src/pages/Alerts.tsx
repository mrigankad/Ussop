import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import type { Alert } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { WarningCircle, CheckCircle, Info, X, XCircle, Clock, Spinner } from '@phosphor-icons/react'
import { EmptyState } from '@/components/shared/EmptyState'

const SEVERITIES = [
  { value: '', label: 'All Alerts', icon: Info, color: 'text-slate-600' },
  { value: 'info', label: 'Info', icon: Info, color: 'text-blue-600' },
  { value: 'warning', label: 'Warnings', icon: WarningCircle, color: 'text-amber-600' },
  { value: 'error', label: 'Errors', icon: XCircle, color: 'text-red-600' },
  { value: 'critical', label: 'Critical', icon: X, color: 'text-red-700' },
]

function SeverityBadge({ severity }: { severity: Alert['severity'] }) {
  const colors = {
    info: 'bg-blue-50 text-blue-700 border-blue-100',
    warning: 'bg-amber-50 text-amber-700 border-amber-100',
    error: 'bg-red-50 text-red-700 border-red-100',
    critical: 'bg-red-100 text-red-800 border-red-200',
  }
  return (
    <span className={`text-xs font-bold px-2.5 py-1 rounded-lg border capitalize ${colors[severity]}`}>
      {severity}
    </span>
  )
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [showUnacked, setShowUnacked] = useState(true)
  const [acknowledging, setAcknowledging] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try {
      const acknowledged = showUnacked ? false : undefined
      const res = await api.getAlerts(filter || undefined, acknowledged)
      setAlerts(res.alerts)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [filter, showUnacked])

  async function acknowledge(id: string) {
    setAcknowledging(id)
    try {
      await api.acknowledgeAlert(id)
      setAlerts(prev => prev.filter(a => a.id !== id))
    } catch (e) {
      console.error(e)
    } finally {
      setAcknowledging(null)
    }
  }

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-center justify-between bg-white/40 p-3 rounded-2xl border border-slate-200/60 shadow-sm backdrop-blur-md">
        <p className="text-sm font-semibold text-slate-600 flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-pulse absolute inline-flex h-full w-full rounded-full opacity-75 ${
              alerts.length > 0 ? 'bg-red-400' : 'bg-emerald-400'
            }`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
              alerts.length > 0 ? 'bg-red-500' : 'bg-emerald-500'
            }`}></span>
          </span>
          System Alerts
        </p>
        <div className="text-xs font-bold text-slate-500">{alerts.length} active</div>
      </div>

      <Card className="flex flex-col">
        <CardHeader className="border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-extrabold text-slate-800">Active Alerts</h2>
              <p className="text-[11px] font-bold text-slate-500 mt-0.5 capitalize">
                Unacknowledged system notifications {filter && `• ${filter}`}
              </p>
            </div>
          </div>
        </CardHeader>

        <div className="flex flex-wrap gap-2 p-4 border-b border-slate-100 bg-slate-50/50">
          {SEVERITIES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all border ${
                filter === value
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-[0_2px_8px_rgba(79,70,229,0.25)]'
                  : 'bg-white text-slate-700 border-slate-200 hover:border-indigo-300 hover:bg-indigo-50'
              }`}
            >
              <Icon size={14} weight={filter === value ? 'bold' : 'regular'} />
              {label}
            </button>
          ))}
        </div>

        <label className="flex items-center gap-2.5 px-4 py-3 border-b border-slate-100 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer">
          <input
            type="checkbox"
            checked={showUnacked}
            onChange={e => setShowUnacked(e.target.checked)}
            className="rounded"
          />
          Show only unacknowledged
        </label>

        <CardContent className="flex-1 overflow-y-auto p-4" style={{ minHeight: '400px' }}>
          {loading ? (
            <div className="flex items-center justify-center h-full gap-2 text-slate-400">
              <Spinner size={18} className="animate-spin" />
              <span className="text-sm font-medium">Loading alerts…</span>
            </div>
          ) : alerts.length === 0 ? (
            <EmptyState
              title={showUnacked ? 'No active alerts' : 'No alerts found'}
              description={showUnacked ? 'All systems operating normally' : 'Try adjusting filters'}
            />
          ) : (
            <div className="space-y-3">
              {alerts.map(alert => (
                <div
                  key={alert.id}
                  className="flex items-start gap-4 p-4 rounded-xl border border-slate-100 bg-white hover:shadow-sm hover:border-slate-200 transition-all group"
                >
                  <div className="pt-0.5">
                    {alert.severity === 'critical' && <X size={20} className="text-red-700" weight="bold" />}
                    {alert.severity === 'error' && <XCircle size={20} className="text-red-600" weight="bold" />}
                    {alert.severity === 'warning' && <WarningCircle size={20} className="text-amber-600" weight="bold" />}
                    {alert.severity === 'info' && <Info size={20} className="text-blue-600" weight="bold" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 mb-1">
                      <h3 className="text-sm font-bold text-slate-800">{alert.title}</h3>
                      <SeverityBadge severity={alert.severity} />
                    </div>
                    <p className="text-sm text-slate-600 mb-2">{alert.message}</p>
                    <p className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                      <Clock size={11} />
                      {new Date(alert.timestamp).toLocaleString()}
                    </p>
                  </div>

                  <button
                    onClick={() => acknowledge(alert.id)}
                    disabled={acknowledging === alert.id}
                    className="shrink-0 px-3 py-2 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100 hover:bg-emerald-100 hover:border-emerald-200 text-xs font-bold transition-all disabled:opacity-50 flex items-center gap-1.5 group-hover:shadow-sm"
                  >
                    {acknowledging === alert.id ? (
                      <>
                        <Spinner size={12} className="animate-spin" />
                        Acking…
                      </>
                    ) : (
                      <>
                        <CheckCircle size={12} weight="bold" />
                        Acknowledge
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
