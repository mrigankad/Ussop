import { useState, useRef, useCallback, useEffect } from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import { api } from '@/lib/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { DecisionBadge } from '@/components/shared/DecisionBadge'
import { UploadSimple, Camera, CircleNotch, Image, Circle, Square } from '@phosphor-icons/react'
import { cn } from '@/lib/cn'
import { MiniMarkdown } from '@/components/shared/MiniMarkdown'
import { useToast } from '@/components/ui/Toast'

interface InspectionResult {
  id: string; decision: string; confidence: number; objects_found: number
  detections: Array<{ class_name: string; confidence: number; bbox: number[]; box?: {x1:number;y1:number;x2:number;y2:number}; iou?: number }>
  result_image?: string; annotated_image?: string; detection_time_ms: number; segmentation_time_ms: number; total_time_ms: number
  vlm_description?: string
}

function CameraTab({ onCapture }: { onCapture: (file: File) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState('')

  async function startCamera() {
    setError('')
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } })
      setStream(s)
      if (videoRef.current) videoRef.current.srcObject = s
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Camera access denied')
    }
  }

  function stopCamera() {
    stream?.getTracks().forEach(t => t.stop())
    setStream(null)
    if (videoRef.current) videoRef.current.srcObject = null
  }

  function capture() {
    const video = videoRef.current
    if (!video) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth; canvas.height = video.videoHeight
    canvas.getContext('2d')!.drawImage(video, 0, 0)
    canvas.toBlob(blob => {
      if (blob) onCapture(new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' }))
    }, 'image/jpeg', 0.92)
  }

  useEffect(() => () => { stream?.getTracks().forEach(t => t.stop()) }, [stream])

  return (
    <div className="space-y-3">
      <div className="aspect-video bg-slate-900 rounded-xl overflow-hidden relative">
        <video ref={videoRef} autoPlay playsInline muted className={cn('w-full h-full object-cover', !stream && 'hidden')} />
        {!stream && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <Camera size={32} className="mx-auto mb-2" />
              <p className="text-sm">{error || 'Camera off'}</p>
            </div>
          </div>
        )}
        {stream && (
          <div className="absolute top-2 right-2 flex items-center gap-1.5 bg-black/50 rounded-full px-2 py-1">
            <Circle size={8} className="text-red-500 fill-red-500 animate-pulse" />
            <span className="text-white text-xs">LIVE</span>
          </div>
        )}
      </div>
      <div className="flex gap-2">
        {!stream
          ? <button onClick={startCamera} className="flex-1 py-3 bg-olive-600 text-white rounded-xl text-[11px] font-bold hover:bg-olive-700 flex items-center justify-center gap-2 transition-all"><Camera size={14} weight="bold"/> Start Camera</button>
          : <>
              <button onClick={capture} className="flex-1 py-3 bg-emerald-600 text-white rounded-xl text-[11px] font-bold hover:bg-emerald-700 flex items-center justify-center gap-2 transition-all"><Circle size={14} weight="bold"/> Capture Image</button>
              <button onClick={stopCamera} className="py-3 px-4 bg-slate-100 text-slate-500 rounded-xl text-[11px] font-bold hover:bg-slate-200 transition-all"><Square size={14} weight="bold"/></button>
            </>}
      </div>
      {error && <p className="text-[11px] font-bold text-red-500 px-2">{error}</p>}
    </div>
  )
}

export default function Inspect() {
  const { toast } = useToast()
  const [result, setResult] = useState<InspectionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [partId, setPartId] = useState('')
  const [stationId, setStationId] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const runInspection = useCallback(async (file: File) => {
    setLoading(true); setResult(null)
    const fd = new FormData()
    fd.append('file', file)
    if (partId) fd.append('part_id', partId)
    if (stationId) fd.append('station_id', stationId)
    try {
      const r = await api.inspect(fd)
      setResult(r)
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Inspection Failed', 'error')
    } finally { setLoading(false) }
  }, [partId, stationId, toast])

  function handleFile(f: File) { if (f) runInspection(f) }
  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 lg:gap-8 animate-in">
      <div className="space-y-6">
        <Card>
          <CardContent className="p-8">
            <TabsPrimitive.Root defaultValue="upload">
              <TabsPrimitive.List className="flex gap-2 mb-6 p-1.5 bg-slate-50 rounded-xl border border-slate-100">
                {['upload', 'camera'].map(v => (
                  <TabsPrimitive.Trigger key={v} value={v}
                    className="flex-1 py-2.5 text-[11px] font-bold rounded-lg transition-all data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:border-slate-100 data-[state=active]:shadow-sm border border-transparent text-slate-400 hover:text-slate-600">
                    {v === 'upload' ? <span className="flex items-center justify-center gap-2"><UploadSimple size={14} weight="bold"/> Upload File</span> : <span className="flex items-center justify-center gap-2"><Camera size={14} weight="bold"/> Live Camera</span>}
                  </TabsPrimitive.Trigger>
                ))}
              </TabsPrimitive.List>

              <TabsPrimitive.Content value="upload">
                <div
                  className={cn('border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer group', dragOver ? 'border-olive-500 bg-olive-50' : 'border-slate-100 bg-slate-50/30 hover:border-slate-200 hover:bg-slate-50/50')}
                  onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileRef.current?.click()}
                >
                  <div className="w-16 h-16 rounded-2xl bg-white border border-slate-100 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform">
                    <Image size={32} weight="bold" className="text-slate-400" />
                  </div>
                  <p className="text-xs font-bold" style={{ color: 'var(--text)' }}>Drop image here</p>
                  <p className="text-[11px] font-bold text-slate-400 mt-1">Or click to browse files</p>
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
                </div>
              </TabsPrimitive.Content>

              <TabsPrimitive.Content value="camera">
                <CameraTab onCapture={handleFile} />
              </TabsPrimitive.Content>
            </TabsPrimitive.Root>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-8 space-y-6">
            <div className="flex flex-col gap-2">
              <label className="text-[11px] font-bold text-slate-500">Part Serial ID (Optional)</label>
              <input value={partId} onChange={e => setPartId(e.target.value)} placeholder="e.g. Serial-2024-X"
                className="w-full px-4 py-3 border border-slate-100 rounded-xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50" />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[11px] font-bold text-slate-500">Station Identifier (Optional)</label>
              <input value={stationId} onChange={e => setStationId(e.target.value)} placeholder="e.g. Assembly-Station-01"
                className="w-full px-4 py-3 border border-slate-100 rounded-xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="min-h-[600px] flex flex-col">
        {loading ? (
          <div className="flex-1 flex items-center justify-center p-20">
            <div className="text-center">
              <div className="w-20 h-20 rounded-2xl bg-olive-50 border border-olive-100 flex items-center justify-center mx-auto mb-8 animate-pulse">
                <CircleNotch size={32} weight="bold" className="animate-spin text-olive-600" />
              </div>
              <p className="text-sm font-bold" style={{ color: 'var(--text)' }}>Running AI Analysis</p>
              <p className="text-[11px] font-bold text-slate-400 mt-2">Processing image...</p>
            </div>
          </div>
        ) : result ? (
          <div className="flex flex-col h-full animate-in">
            <CardHeader className="px-8 py-6">
              <div className="flex items-center gap-4">
                <DecisionBadge decision={result.decision} />
                <span className="text-[11px] font-bold text-slate-400">{(result.confidence * 100).toFixed(1)}% Confidence</span>
              </div>
            </CardHeader>
            <div className="flex-1 p-8 grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-8">
              <div className="relative group">
                {(result.annotated_image || result.result_image) ? (
                  <div className="rounded-2xl overflow-hidden border border-slate-100 bg-slate-50">
                    <img src={`/api/v1/images/${result.annotated_image || result.result_image}`} alt="Inspection Result" className="w-full h-auto" />
                  </div>
                ) : (
                  <div className="aspect-video bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-center text-slate-400">
                    <Image size={48} weight="bold" />
                  </div>
                )}
              </div>
              <div className="space-y-3">
                {[
                  { label: 'Objects Found', value: result.objects_found },
                  { label: 'Confidence Score', value: `${(result.confidence * 100).toFixed(1)}%` },
                  { label: 'Detection Time', value: `${result.detection_time_ms?.toFixed(0)}ms` },
                  { label: 'Segmentation Time', value: `${result.segmentation_time_ms?.toFixed(0)}ms` },
                  { label: 'Total Processing', value: `${result.total_time_ms?.toFixed(0)}ms` },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between items-center p-4 bg-slate-50/50 rounded-xl border border-slate-50">
                    <span className="text-[11px] font-bold text-slate-500">{row.label}</span>
                    <span className="text-xs font-bold" style={{ color: 'var(--text)' }}>{row.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {result.vlm_description && (
              <div className="px-8 pb-8">
                <div className="p-6 bg-olive-50 border border-olive-100 rounded-xl">
                  <p className="text-[11px] font-bold text-olive-600 mb-4 flex items-center gap-2">
                    <Circle size={10} weight="fill" className="animate-pulse" />
                    AI Analysis Report
                  </p>
                  <MiniMarkdown text={result.vlm_description} />
                </div>
              </div>
            )}

            {result.detections?.length > 0 && (
              <div className="px-8 pb-8">
                <div className="border-t border-slate-50 pt-8">
                  <h3 className="text-xs font-bold mb-4" style={{ color: 'var(--text)' }}>Detection Breakdown</h3>
                  <div className="overflow-hidden rounded-xl border border-slate-100">
                    <table className="w-full text-left">
                      <thead className="bg-slate-50/50">
                        <tr>
                          {['Class Label', 'Confidence', 'Location Box'].map(h => (
                            <th key={h} className="px-6 py-3 text-[11px] font-bold text-slate-400">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {result.detections.map((d, i) => (
                          <tr key={i} className="hover:bg-slate-50/30 transition-colors">
                            <td className="px-6 py-4 text-xs font-bold" style={{ color: 'var(--text)' }}>{d.class_name}</td>
                            <td className="px-6 py-4 text-xs font-bold text-slate-500">{(d.confidence * 100).toFixed(1)}%</td>
                            <td className="px-6 py-4 text-[10px] font-bold text-slate-400 font-mono tracking-tighter">
                              {d.box
                                ? `${Math.round(d.box.x1)}, ${Math.round(d.box.y1)}, ${Math.round(d.box.x2)}, ${Math.round(d.box.y2)}`
                                : d.bbox?.map(v => Math.round(v)).join(', ')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center p-20">
            <div className="text-center max-w-xs">
              <div className="w-20 h-20 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center mx-auto mb-8">
                <Image size={32} weight="bold" className="text-slate-300" />
              </div>
              <p className="text-sm font-bold" style={{ color: 'var(--text)' }}>Waiting for image</p>
              <p className="text-[11px] font-bold text-slate-400 mt-2 leading-relaxed">Please upload an image or start the camera to begin the inspection process.</p>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
