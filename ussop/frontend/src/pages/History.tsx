import { useEffect, useState, useCallback } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { api } from '@/lib/api'
import type { Inspection } from '@/types/api'
import { Card, CardHeader } from '@/components/ui/Card'
import { DecisionBadge } from '@/components/shared/DecisionBadge'
import { Pagination } from '@/components/shared/Pagination'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Button } from '@/components/ui/Button'
import { DownloadSimple, X, CaretUp, CaretDown, Eye, Image } from '@phosphor-icons/react'
import { MiniMarkdown } from '@/components/shared/MiniMarkdown'

interface InspectionDetail extends Inspection {
  detections?: Array<{ class_name: string; confidence: number; box?: { x1: number; y1: number; x2: number; y2: number } }>
  annotated_image?: string
  original_image?: string
  detection_time_ms?: number
  segmentation_time_ms?: number
  vlm_description?: string
}

function DetailModal({ id, onClose }: { id: string; onClose: () => void }) {
  const [detail, setDetail] = useState<InspectionDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/v1/inspect/${id}`, {
      headers: localStorage.getItem('access_token')
        ? { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        : {}
    })
      .then(r => r.json())
      .then(setDetail)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40 animate-in fade-in-0" />
      <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <Dialog.Title className="text-lg font-semibold text-slate-900">Inspection Detail</Dialog.Title>
          <Dialog.Close asChild>
            <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-500"><X size={18} /></button>
          </Dialog.Close>
        </div>

        {loading ? (
          <div className="py-12 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" /></div>
        ) : detail ? (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <DecisionBadge decision={detail.decision} />
              <span className="text-sm text-slate-500">{(detail.confidence * 100).toFixed(1)}% confidence</span>
              <span className="text-sm text-slate-400 ml-auto">{new Date(detail.timestamp).toLocaleString()}</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                {(detail.annotated_image || detail.original_image) ? (
                  <img src={`/api/v1/images/${detail.annotated_image || detail.original_image}`} alt="Result" className="w-full rounded-xl border border-slate-200" />
                ) : (
                  <div className="aspect-video bg-slate-100 rounded-xl flex items-center justify-center text-slate-300">
                    <Image size={40} />
                  </div>
                )}
              </div>
              <div className="space-y-2">
                {[
                  ['Part ID',     detail.part_id || '—'],
                  ['Station',     detail.station_id || '—'],
                  ['Objects',     String(detail.objects_found)],
                  ['Detection',   detail.detection_time_ms ? `${Math.round(detail.detection_time_ms)}ms` : '—'],
                  ['Segmentation',detail.segmentation_time_ms ? `${Math.round(detail.segmentation_time_ms)}ms` : '—'],
                  ['Total Time',  detail.total_time_ms ? `${Math.round(detail.total_time_ms)}ms` : '—'],
                ].map(([l, v]) => (
                  <div key={l} className="flex justify-between items-center p-2.5 bg-slate-50 rounded-xl text-sm">
                    <span className="text-slate-500">{l}</span>
                    <span className="font-medium text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            {detail.vlm_description && (
              <div className="p-4 bg-indigo-50 border border-indigo-100 rounded-xl">
                <p className="text-xs font-bold text-indigo-500 uppercase tracking-wide mb-2">AI Analysis · Llama 3.2 Vision</p>
                <MiniMarkdown text={detail.vlm_description} />
              </div>
            )}
            {detail.detections && detail.detections.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Detections</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50">
                      {['Class', 'Confidence', 'Bounding Box'].map(h => (
                        <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-slate-500 capitalize">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.detections.map((d, i) => (
                      <tr key={i} className="border-b border-slate-50">
                        <td className="px-3 py-2 font-medium text-slate-700">{d.class_name}</td>
                        <td className="px-3 py-2 text-slate-600">{(d.confidence * 100).toFixed(1)}%</td>
                        <td className="px-3 py-2 text-slate-400 text-xs font-mono">
                          {d.box ? `${Math.round(d.box.x1)}, ${Math.round(d.box.y1)}, ${Math.round(d.box.x2)}, ${Math.round(d.box.y2)}` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <p className="text-slate-500 text-sm py-8 text-center">Could not load inspection details.</p>
        )}
      </Dialog.Content>
    </Dialog.Portal>
  )
}

type SortDir = 'asc' | 'desc'
type SortCol = 'timestamp' | 'decision' | 'objects_found'

export default function History() {
  const [items, setItems] = useState<Inspection[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [decision, setDecision] = useState('')
  const [station, setStation] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [sortCol, setSortCol] = useState<SortCol>('timestamp')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const limit = 20

  const load = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { limit, offset: p * limit, order_by: sortCol, order_dir: sortDir }
      if (decision) params.decision = decision
      if (station) params.station_id = station
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const data = await api.getInspections(params)
      setItems(data.items); setTotal(data.total)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [decision, station, dateFrom, dateTo, sortCol, sortDir])

  useEffect(() => { setPage(0); load(0) }, [decision, station, dateFrom, dateTo, sortCol, sortDir])

  function handleSort(col: SortCol) {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
  }

  function SortIcon({ col }: { col: SortCol }) {
    if (sortCol !== col) return <span className="opacity-30 ml-1">↕</span>
    return sortDir === 'asc' ? <CaretUp size={12} className="inline ml-1" /> : <CaretDown size={12} className="inline ml-1" />
  }

  function resetFilters() { setDecision(''); setStation(''); setDateFrom(''); setDateTo('') }
  const hasFilters = !!(decision || station || dateFrom || dateTo)

  return (
    <>
    <Dialog.Root open={!!selectedId} onOpenChange={open => { if (!open) setSelectedId(null) }}>
      {selectedId && <DetailModal id={selectedId} onClose={() => setSelectedId(null)} />}
    </Dialog.Root>
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <h2 className="font-semibold text-slate-900">All Inspections</h2>
            <span className="text-sm text-slate-400">{total.toLocaleString()} results</span>
          </div>
          <a href={api.exportCsv()} className="inline-flex items-center gap-1.5 text-sm text-slate-600 border border-slate-200 px-3 py-1.5 rounded-xl hover:bg-slate-50">
            <DownloadSimple size={14} /> Export CSV
          </a>
        </CardHeader>

        {/* Filters */}
        <div className="px-6 py-3 border-b border-slate-100 flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-400 capitalize mb-1">Decision</label>
            <select value={decision} onChange={e => setDecision(e.target.value)} className="px-3 py-1.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
              <option value="">All</option>
              <option value="pass">Pass</option>
              <option value="fail">Fail</option>
              <option value="uncertain">Uncertain</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 capitalize mb-1">Station</label>
            <input value={station} onChange={e => setStation(e.target.value)} placeholder="Any" className="px-3 py-1.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-32" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 capitalize mb-1">From</label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="px-3 py-1.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 capitalize mb-1">To</label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="px-3 py-1.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={resetFilters} className="mb-0.5 gap-1 text-slate-500">
              <X size={12} /> Clear
            </Button>
          )}
        </div>

        {loading ? <LoadingSpinner /> : items.length === 0 ? <EmptyState title="No inspections found" description="Try adjusting your filters" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 capitalize">Image</th>
                  {(['timestamp', 'decision', 'objects_found'] as SortCol[]).map(col => (
                    <th key={col} onClick={() => handleSort(col)} className="px-6 py-3 text-left text-xs font-semibold text-slate-500 capitalize cursor-pointer hover:bg-slate-100 select-none">
                      {col === 'timestamp' ? 'Timestamp' : col === 'decision' ? 'Decision' : 'Objects'}
                      <SortIcon col={col} />
                    </th>
                  ))}
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 capitalize">Station</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 capitalize">Part ID</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 capitalize">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-3">
                      {item.thumbnail
                        ? <img src={`/api/v1/images/${item.thumbnail}`} alt="" className="w-16 h-10 object-cover rounded-lg" loading="lazy" />
                        : <div className="w-16 h-10 bg-slate-100 rounded-lg flex items-center justify-center text-slate-300 text-xs">No img</div>}
                    </td>
                    <td className="px-6 py-3 text-slate-600 whitespace-nowrap">{new Date(item.timestamp).toLocaleString()}</td>
                    <td className="px-6 py-3"><DecisionBadge decision={item.decision} /></td>
                    <td className="px-6 py-3 text-slate-600">{item.objects_found}</td>
                    <td className="px-6 py-3 text-slate-600">{item.station_id || '—'}</td>
                    <td className="px-6 py-3 text-slate-600">{item.part_id || '—'}</td>
                    <td className="px-6 py-3">
                      <button onClick={() => setSelectedId(item.id)} className="flex items-center gap-1 text-indigo-600 text-xs font-medium hover:underline">
                        <Eye size={12} /> View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} totalPages={Math.ceil(total / limit)} onPageChange={p => { setPage(p); load(p) }} />
      </Card>
    </div>
    </>
  )
}
