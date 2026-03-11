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
      <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[95vw] max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl p-4 sm:p-6" style={{ background: 'var(--surface)' }}>
        <div className="flex items-center justify-between mb-5">
          <Dialog.Title className="text-lg font-semibold" style={{ color: 'var(--text)' }}>Inspection Detail</Dialog.Title>
          <Dialog.Close asChild>
            <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-slate-100" style={{ color: 'var(--muted)' }}><X size={18} /></button>
          </Dialog.Close>
        </div>

        {loading ? (
          <div className="py-12 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-olive-600" /></div>
        ) : detail ? (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <DecisionBadge decision={detail.decision} />
              <span className="text-sm text-slate-500">{(detail.confidence * 100).toFixed(1)}% confidence</span>
              <span className="text-sm text-slate-400 ml-auto">{new Date(detail.timestamp).toLocaleString()}</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                  { label: 'Part ID', value: detail.part_id || '—' },
                  { label: 'Station ID', value: detail.station_id || '—' },
                  { label: 'Items Found', value: String(detail.objects_found) },
                  { label: 'Detection Time', value: detail.detection_time_ms ? `${Math.round(detail.detection_time_ms)}ms` : '—' },
                  { label: 'Segmentation Time', value: detail.segmentation_time_ms ? `${Math.round(detail.segmentation_time_ms)}ms` : '—' },
                  { label: 'Total Time', value: detail.total_time_ms ? `${Math.round(detail.total_time_ms)}ms` : '—' },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between items-center p-2.5 rounded-xl text-sm" style={{ background: 'var(--surface-2)' }}>
                    <span className="font-medium" style={{ color: 'var(--muted)' }}>{row.label}</span>
                    <span className="font-bold" style={{ color: 'var(--text)' }}>{row.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {detail.vlm_description && (
              <div className="p-4 bg-olive-50 border border-olive-100 rounded-xl">
                <p className="text-xs font-bold text-olive-600 mb-2">AI Visual Analysis</p>
                <MiniMarkdown text={detail.vlm_description} />
              </div>
            )}
            {detail.detections && detail.detections.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-slate-700 mb-2">Detections</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50">
                      {['Class', 'Confidence', 'Box'].map(h => (
                        <th key={h} className="px-3 py-2 text-left text-xs font-bold text-slate-500">{h}</th>
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
    <div className="space-y-6 animate-in">
      <Card className="rounded-2xl overflow-hidden border-slate-100/60 shadow-2xl shadow-slate-900/[0.03]">
        <CardHeader className="p-10 border-b border-slate-50">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-6">
              <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center border border-slate-100 shadow-sm transition-transform hover:scale-110 duration-500">
                <Image size={28} weight="bold" style={{ color: 'var(--text)' }} />
              </div>
              <div className="flex flex-col">
                <h2 className="text-2xl font-semibold tracking-tight leading-none mb-2" style={{ color: 'var(--text)' }}>Inspection History</h2>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-semibold text-slate-400 bg-slate-50 px-4 py-1.5 rounded-full border border-slate-100 tracking-wider leading-none">
                    {total.toLocaleString()} Inspections
                  </span>
                </div>
              </div>
            </div>
            <a href={api.exportCsv()} className="inline-flex items-center gap-3 text-[11px] font-semibold text-slate-600 border border-slate-200 px-8 py-4 rounded-xl hover:bg-slate-900 hover:text-white hover:border-slate-900 transition-all active:scale-95 shadow-sm">
              <DownloadSimple size={16} weight="bold" /> Export CSV
            </a>
          </div>
        </CardHeader>

        {/* Filters */}
        <div className="px-10 py-8 bg-slate-50/30 border-b border-slate-50 flex flex-wrap gap-8 items-end">
          <div className="flex flex-col gap-2.5">
            <label className="text-[10px] font-semibold text-slate-400 tracking-wider pl-1">Status</label>
            <select value={decision} onChange={e => setDecision(e.target.value)} className="px-5 py-3.5 border border-slate-100 rounded-xl text-[11px] font-semibold focus:outline-none focus:ring-4 focus:ring-olive-50 bg-white transition-all min-w-[180px] shadow-sm">
              <option value="">All Results</option>
              <option value="pass">Pass Only</option>
              <option value="fail">Fail Only</option>
              <option value="uncertain">Uncertain Only</option>
            </select>
          </div>
          <div className="flex flex-col gap-2.5">
            <label className="text-[10px] font-semibold text-slate-400 tracking-wider pl-1">Station ID</label>
            <input value={station} onChange={e => setStation(e.target.value)} placeholder="Search Station..." className="px-5 py-3.5 border border-slate-100 rounded-xl text-[11px] font-semibold focus:outline-none focus:ring-4 focus:ring-olive-50 w-48 bg-white transition-all shadow-sm font-mono" />
          </div>
          <div className="flex flex-col gap-2.5">
            <label className="text-[10px] font-semibold text-slate-400 tracking-wider pl-1">Date From</label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="px-5 py-3.5 border border-slate-100 rounded-xl text-[11px] font-semibold focus:outline-none focus:ring-4 focus:ring-olive-50 bg-white transition-all shadow-sm" />
          </div>
          <div className="flex flex-col gap-2.5">
            <label className="text-[10px] font-semibold text-slate-400 tracking-wider pl-1">Date To</label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="px-5 py-3.5 border border-slate-100 rounded-xl text-[11px] font-semibold focus:outline-none focus:ring-4 focus:ring-olive-50 bg-white transition-all shadow-sm" />
          </div>
          {hasFilters && (
            <Button variant="secondary" size="sm" onClick={resetFilters} className="gap-2.5 bg-red-50 text-red-600 hover:bg-red-600 hover:text-white border-transparent text-[11px] font-semibold py-4 px-8 rounded-xl transition-all active:scale-95 shadow-sm">
              <X size={14} weight="bold" /> Reset Filters
            </Button>
          )}
        </div>

        {loading ? <div className="p-20"><LoadingSpinner /></div> : items.length === 0 ? <div className="py-20"><EmptyState title="No Results Found" description="Try adjusting your filters to see more results." /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr style={{ background: 'var(--surface)' }}>
                  <th className="px-10 py-6 text-[10px] font-semibold text-slate-400 tracking-wider">Image</th>
                  {(['timestamp', 'decision', 'objects_found'] as SortCol[]).map(col => (
                    <th key={col} onClick={() => handleSort(col)} className="px-10 py-6 text-[10px] font-semibold text-slate-400 tracking-wider cursor-pointer hover:bg-slate-50 select-none group">
                      <div className="flex items-center gap-1.5">
                        {col === 'timestamp' ? 'Date/Time' : col === 'decision' ? 'Status' : 'Items Found'}
                        <SortIcon col={col} />
                      </div>
                    </th>
                  ))}
                  <th className="px-10 py-6 text-[10px] font-semibold text-slate-400 tracking-wider">Station</th>
                  <th className="px-10 py-6 text-[10px] font-semibold text-slate-400 tracking-wider">Part ID</th>
                  <th className="px-10 py-6 text-[10px] font-semibold text-slate-400 tracking-wider text-right pr-20">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {items.map(item => (
                  <tr key={item.id} className="hover:bg-slate-50/40 transition-all group">
                    <td className="px-10 py-6">
                      {item.thumbnail
                        ? <img src={`/api/v1/images/${item.thumbnail}`} alt="" className="w-24 h-14 object-cover rounded-xl border border-slate-100 shadow-sm transition-transform group-hover:scale-105 duration-300" loading="lazy" />
                        : <div className="w-24 h-14 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-center text-slate-300 text-[10px] font-semibold tracking-tighter">Null Image</div>}
                    </td>
                    <td className="px-10 py-6 text-xs font-semibold whitespace-nowrap tracking-tighter" style={{ color: 'var(--text)' }}>{new Date(item.timestamp).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</td>
                    <td className="px-10 py-6"><DecisionBadge decision={item.decision} /></td>
                    <td className="px-10 py-6">
                      <div className="flex items-center gap-2">
                         <span className="text-xs font-semibold text-slate-900">{item.objects_found}</span>
                         <span className="text-[10px] font-bold text-slate-400 tracking-tighter">Items</span>
                      </div>
                    </td>
                    <td className="px-10 py-6 text-[11px] font-semibold text-slate-500 font-mono tracking-tighter">{item.station_id || 'ID_UNASSIGNED'}</td>
                    <td className="px-10 py-6 text-[11px] font-semibold text-slate-500 font-mono tracking-tighter">{item.part_id || 'ID_UNASSIGNED'}</td>
                    <td className="px-10 py-6 text-right pr-20">
                      <button onClick={() => setSelectedId(item.id)} className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl bg-white border border-slate-100 text-slate-900 text-[11px] font-semibold hover:bg-olive-600 hover:text-white hover:border-olive-600 transition-all duration-300 shadow-sm active:scale-95 group">
                        <Eye size={16} weight="bold" className="text-slate-400 group-hover:text-white transition-colors duration-300" /> View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="p-4 sm:p-10 border-t" style={{ borderColor: 'var(--border-subtle)', background: 'var(--surface)' }}>
          <Pagination page={page} totalPages={Math.ceil(total / limit)} onPageChange={p => { setPage(p); load(p) }} />
        </div>
      </Card>
    </div>
    </>
  )
}
