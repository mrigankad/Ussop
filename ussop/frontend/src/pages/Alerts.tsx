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
    info: 'bg-blue-50/50 text-blue-600 border-blue-100',
    warning: 'bg-amber-50/50 text-amber-600 border-amber-100',
    error: 'bg-red-50/50 text-red-600 border-red-100',
    critical: 'bg-red-100/50 text-red-700 border-red-200',
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
      <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-2xl border backdrop-blur-md gap-4" style={{ background: 'color-mix(in srgb, var(--surface) 40%, transparent)', borderColor: 'var(--border-subtle)' }}>
        <p className="text-sm font-bold flex items-center gap-3 pl-2" style={{ color: 'var(--text)' }}>
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-pulse absolute inline-flex h-full w-full rounded-full opacity-75 ${
              alerts.length > 0 ? 'bg-red-400' : 'bg-emerald-400'
            }`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
              alerts.length > 0 ? 'bg-red-500' : 'bg-emerald-500'
            }`}></span>
          </span>
          Alerts
        </p>
        <div className="text-[11px] font-bold border px-4 py-2 rounded-lg shadow-sm" style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' }}>
          {alerts.length} Alert{alerts.length !== 1 ? 's' : ''}
        </div>
      </div>

      <Card className="flex flex-col">
        <CardHeader className="border-b border-slate-50 p-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text)' }}>Active Alerts</h2>
              <p className="text-[11px] font-bold mt-1" style={{ color: 'var(--muted)' }}>
                Ongoing system alerts and notifications {filter && `• ${filter}`}
              </p>
            </div>
          </div>
        </CardHeader>

        <div className="flex flex-wrap gap-2 p-6 border-b" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface-2)' }}>
          {SEVERITIES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-[11px] font-bold transition-all border ${
                filter === value
                  ? 'bg-olive-600 text-white border-olive-600 shadow-lg shadow-olive-900/10'
                  : 'hover:border-olive-200 hover:text-olive-700'
              }`}
              style={filter !== value ? { background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' } : undefined}
            >
              <Icon size={14} weight={filter === value ? 'bold' : 'regular'} />
              {label}
            </button>
          ))}
        </div>

        <label className="flex items-center gap-3 px-8 py-4 border-b text-[11px] font-bold transition-colors cursor-pointer select-none" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface)', color: 'var(--muted)' }}>
          <input
            type="checkbox"
            checked={showUnacked}
            onChange={e => setShowUnacked(e.target.checked)}
            className="rounded-lg border-slate-200 text-olive-600 focus:ring-olive-500 w-4 h-4"
          />
          Filter by unread alerts only
        </label>

        <CardContent className="flex-1 overflow-y-auto p-8" style={{ minHeight: '500px' }}>
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
              <Spinner size={32} weight="bold" className="animate-spin text-olive-500" />
              <span className="text-xs font-bold tracking-tight">Synchronizing Analytics Cache…</span>
            </div>
          ) : alerts.length === 0 ? (
            <div className="py-20">
              <EmptyState
                title={showUnacked ? 'Everything Looks Good' : 'No Records Found'}
                description={showUnacked ? 'No unread alerts at this time' : 'Adjust the filters to see more results'}
              />
            </div>
          ) : (
            <div className="space-y-4">
              {alerts.map(alert => (
                <div
                  key={alert.id}
                  className="flex flex-col sm:flex-row items-start gap-6 p-6 rounded-xl border transition-all group"
                  style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}
                >
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border group-hover:scale-110 transition-transform" style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
                    {alert.severity === 'critical' && <X size={20} className="text-red-700" weight="bold" />}
                    {alert.severity === 'error' && <XCircle size={20} className="text-red-600" weight="bold" />}
                    {alert.severity === 'warning' && <WarningCircle size={20} className="text-amber-600" weight="bold" />}
                    {alert.severity === 'info' && <Info size={20} className="text-blue-600" weight="bold" />}
                  </div>

                  <div className="flex-1 min-w-0 pt-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-sm font-bold tracking-tight" style={{ color: 'var(--text)' }}>{alert.title}</h3>
                      <SeverityBadge severity={alert.severity} />
                    </div>
                    <p className="text-xs font-medium leading-relaxed mb-4" style={{ color: 'var(--muted)' }}>{alert.message}</p>
                    <div className="flex items-center gap-4">
                      <span className="text-[10px] font-bold flex items-center gap-1.5 px-3 py-1 rounded-full" style={{ background: 'var(--surface-2)', color: 'var(--muted)' }}>
                        <Clock size={12} weight="bold" />
                        {new Date(alert.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => acknowledge(alert.id)}
                    disabled={acknowledging === alert.id}
                    className="shrink-0 px-5 py-3 rounded-xl bg-emerald-50/50 text-emerald-700 border border-emerald-100 hover:bg-emerald-50 transition-all text-[11px] font-semibold disabled:opacity-50 flex items-center gap-2 group-hover:scale-105"
                  >
                    {acknowledging === alert.id ? (
                      <>
                        <Spinner size={14} weight="bold" className="animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <CheckCircle size={14} weight="bold" />
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
