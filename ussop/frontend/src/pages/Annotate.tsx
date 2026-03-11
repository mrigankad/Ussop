import { useEffect, useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { ActiveLearningStats, QueueItem } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { CheckCircle, SkipForward, Tag, XCircle, Info } from '@phosphor-icons/react'

export default function Annotate() {
  const { toast } = useToast()
  const [stats, setStats] = useState<ActiveLearningStats | null>(null)
  const [item, setItem] = useState<QueueItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [label, setLabel] = useState<'pass' | 'fail' | ''>('')
  const [notes, setNotes] = useState('')

  const user = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null } })()

  const loadNext = useCallback(async () => {
    setLoading(true); setLabel(''); setNotes('')
    try {
      const [s, q] = await Promise.all([api.getALStats(), api.getQueue(1)])
      setStats(s)
      setItem(q[0] ?? null)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadNext() }, [loadNext])

  async function submit(decision: 'pass' | 'fail') {
    if (!item) return
    setSubmitting(true)
    try {
      const annotation = { label: decision, notes }
      await api.submitAnnotation(item.id, [annotation], user?.username ?? 'unknown')
      toast('Annotation saved', 'success')
      loadNext()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed to save annotation', 'error')
    } finally { setSubmitting(false) }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-8 animate-in">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {[
          { label: 'Awaiting Review',  value: stats?.pending ?? 0,  color: 'border-l-amber-500', sub: 'In Queue' },
          { label: 'Reviewed Samples', value: stats?.labeled ?? 0,  color: 'border-l-olive-500', sub: 'Annotated' },
          { label: 'Model Training',   value: stats?.trained ?? 0,  color: 'border-l-emerald-500', sub: 'Trained' },
          { label: 'Total Dataset',    value: stats?.total ?? 0,    color: 'border-l-slate-300', sub: 'Total' },
        ].map(({ label, value, color, sub }) => (
          <Card key={label} className={`border-l-4 ${color} transition-transform hover:scale-105 duration-300`}>
            <CardContent className="py-6 px-7">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-[10px] font-semibold tracking-wider leading-none" style={{ color: 'var(--muted)' }}>{label}</p>
                  <p className="text-3xl font-semibold mt-3 tracking-tighter" style={{ color: 'var(--text)' }}>{value}</p>
                </div>
                <span className="text-[10px] font-bold tracking-tighter" style={{ color: 'var(--border-subtle)' }}>{sub}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {item ? (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
          <Card className="overflow-hidden">
            <CardHeader className="border-b p-8" style={{ borderColor: 'var(--border-subtle)' }}>
              <div>
                <h2 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text)' }}>Annotate Sample</h2>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50/50 text-amber-600 border border-amber-100">
                    Uncertainty Score: {(item.uncertainty_score * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] font-semibold tracking-tighter" style={{ color: 'var(--muted)' }}>UID: {item.id.slice(0, 12)}</span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0" style={{ background: 'var(--surface-2)' }}>
              <div className="p-8">
                <img
                  src={`/api/v1/images/${item.image_path}`}
                  alt="Sample to annotate"
                  className="w-full rounded-2xl border object-contain max-h-[600px] shadow-2xl shadow-slate-900/5"
                  style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}
                  onError={e => { (e.target as HTMLImageElement).src = '' }}
                />
              </div>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="border-olive-100 shadow-lg shadow-olive-900/5">
              <CardHeader className="border-b p-6" style={{ borderColor: 'var(--border-subtle)' }}>
                <h3 className="text-[11px] font-semibold tracking-wider flex items-center gap-2" style={{ color: 'var(--muted)' }}>
                  <Tag size={18} weight="bold" className="text-olive-500" /> 
                  Identify Sample
                </h3>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-6">
                  <div className="grid grid-cols-1 gap-3">
                    <button
                      onClick={() => setLabel('pass')}
                      className={`flex items-center justify-between px-6 py-5 rounded-xl font-semibold text-xs transition-all border-2 ${label === 'pass' ? 'bg-emerald-600 text-white border-emerald-600 shadow-lg shadow-emerald-900/20 scale-[1.02]' : 'hover:border-emerald-200 hover:text-emerald-700'}`}
                      style={label !== 'pass' ? { background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' } : undefined}
                    >
                      <span>Pass</span>
                      <CheckCircle size={18} weight="bold" />
                    </button>
                    <button
                      onClick={() => setLabel('fail')}
                      className={`flex items-center justify-between px-6 py-5 rounded-xl font-semibold text-xs transition-all border-2 ${label === 'fail' ? 'bg-red-600 text-white border-red-600 shadow-lg shadow-red-900/20 scale-[1.02]' : 'hover:border-red-200 hover:text-red-700'}`}
                      style={label !== 'fail' ? { background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' } : undefined}
                    >
                      <span>Fail</span>
                      <XCircle size={18} weight="bold" />
                    </button>
                  </div>

                  <div>
                    <label className="block text-[10px] font-semibold tracking-wider mb-2.5 pl-1" style={{ color: 'var(--muted)' }}>Notes</label>
                    <textarea
                      value={notes}
                      onChange={e => setNotes(e.target.value)}
                      rows={4}
                      placeholder="Add any observations or notes here..."
                      className="w-full px-5 py-4 border rounded-xl text-[11px] font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 transition-all focus:bg-white placeholder:text-slate-300 resize-none"
                      style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }}
                    />
                  </div>

                  <div className="space-y-3 pt-2">
                    <Button
                      variant="primary"
                      className="w-full justify-center gap-2 py-6 text-[11px] font-semibold rounded-xl shadow-xl shadow-olive-900/10"
                      disabled={!label || submitting}
                      onClick={() => label && submit(label)}
                    >
                      {submitting ? 'Saving...' : 'Submit and Next'}
                    </Button>

                    <Button
                      variant="ghost"
                      className="w-full justify-center gap-2 py-4 text-[10px] font-bold rounded-xl"
                      style={{ color: 'var(--muted)' }}
                      onClick={loadNext}
                      disabled={submitting}
                    >
                      <SkipForward size={16} weight="bold" /> Skip Sample
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900 border-none">
              <CardContent className="py-6 px-7">
                <div className="flex gap-4">
                  <div className="shrink-0 w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center">
                    <Info size={16} className="text-amber-500" weight="bold" />
                  </div>
                  <p className="text-[11px] font-bold text-slate-400 leading-relaxed">
                    This image was flagged because the AI was unsure. Your label helps improve the model.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <div className="py-20">
          <EmptyState
            title="Verification Complete"
            description="All samples have been reviewed. No further action needed."
          />
        </div>
      )}
    </div>
  )
}
