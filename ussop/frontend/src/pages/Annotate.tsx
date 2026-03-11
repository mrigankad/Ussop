import { useEffect, useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { ActiveLearningStats, QueueItem } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { CheckCircle, SkipForward, Tag } from '@phosphor-icons/react'

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
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-5">
        {[
          { label: 'Pending Review', value: stats?.pending ?? 0,  color: 'border-l-amber-500' },
          { label: 'Labeled',        value: stats?.labeled ?? 0,  color: 'border-l-indigo-500' },
          { label: 'Trained',        value: stats?.trained ?? 0,  color: 'border-l-emerald-500' },
          { label: 'Total Samples',  value: stats?.total ?? 0,    color: 'border-l-slate-400' },
        ].map(({ label, value, color }) => (
          <Card key={label} className={`border-l-4 ${color}`}>
            <CardContent className="py-5">
              <p className="text-xs font-semibold text-slate-500 capitalize">{label}</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {item ? (
        <div className="grid grid-cols-[1fr_320px] gap-6">
          <Card>
            <CardHeader>
              <div>
                <h2 className="font-semibold text-slate-900">Review Image</h2>
                <p className="text-xs text-slate-500 mt-0.5">Uncertainty: {(item.uncertainty_score * 100).toFixed(1)}%</p>
              </div>
              <span className="text-xs text-slate-400 font-mono">{item.id.slice(0, 8)}…</span>
            </CardHeader>
            <CardContent>
              <img
                src={`/api/v1/images/${item.image_path}`}
                alt="Sample to annotate"
                className="w-full rounded-xl border border-slate-200 object-contain max-h-[520px]"
                onError={e => { (e.target as HTMLImageElement).src = '' }}
              />
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader><h3 className="font-semibold text-slate-900 flex items-center gap-2"><Tag size={16} /> Label</h3></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => setLabel('pass')}
                      className={`py-3 rounded-xl font-semibold text-sm transition-colors border-2 ${label === 'pass' ? 'bg-emerald-600 text-white border-emerald-600' : 'border-slate-200 text-slate-600 hover:border-emerald-400 hover:text-emerald-600'}`}
                    >
                      ✓ Pass
                    </button>
                    <button
                      onClick={() => setLabel('fail')}
                      className={`py-3 rounded-xl font-semibold text-sm transition-colors border-2 ${label === 'fail' ? 'bg-red-600 text-white border-red-600' : 'border-slate-200 text-slate-600 hover:border-red-400 hover:text-red-600'}`}
                    >
                      ✗ Fail
                    </button>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-500 capitalize mb-1.5">Notes (optional)</label>
                    <textarea
                      value={notes}
                      onChange={e => setNotes(e.target.value)}
                      rows={3}
                      placeholder="Describe defect type, location…"
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                    />
                  </div>

                  <Button
                    variant="primary"
                    className="w-full justify-center gap-2"
                    disabled={!label || submitting}
                    onClick={() => label && submit(label)}
                  >
                    <CheckCircle size={16} />
                    {submitting ? 'Saving…' : 'Save & Next'}
                  </Button>

                  <Button
                    variant="ghost"
                    className="w-full justify-center gap-2 text-slate-500"
                    onClick={loadNext}
                    disabled={submitting}
                  >
                    <SkipForward size={16} /> Skip
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4">
                <p className="text-xs text-slate-500">
                  The model flagged this image as <span className="font-medium text-amber-600">uncertain</span>.
                  Your label will be used for the next training cycle.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <Card>
          <EmptyState
            title="No images to review"
            description="The active learning queue is empty. Run more inspections to generate new samples."
          />
        </Card>
      )}
    </div>
  )
}
