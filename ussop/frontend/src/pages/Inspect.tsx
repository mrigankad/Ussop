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
          ? <button onClick={startCamera} className="flex-1 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 flex items-center justify-center gap-1.5"><Camera size={14}/> Start Camera</button>
          : <>
              <button onClick={capture} className="flex-1 py-2 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 flex items-center justify-center gap-1.5"><Circle size={14}/> Capture</button>
              <button onClick={stopCamera} className="py-2 px-3 bg-slate-200 text-slate-600 rounded-xl text-sm hover:bg-slate-300"><Square size={14}/></button>
            </>}
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
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
      toast(e instanceof Error ? e.message : 'Inspection failed', 'error')
    } finally { setLoading(false) }
  }, [partId, stationId, toast])

  function handleFile(f: File) { if (f) runInspection(f) }
  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  return (
    <div className="grid grid-cols-[380px_1fr] gap-6">
      <div className="space-y-4">
        <Card>
          <CardContent>
            <TabsPrimitive.Root defaultValue="upload">
              <TabsPrimitive.List className="flex gap-2 mb-4">
                {['upload', 'camera'].map(v => (
                  <TabsPrimitive.Trigger key={v} value={v}
                    className="flex-1 py-2 text-sm font-medium rounded-xl transition-colors data-[state=active]:bg-indigo-600 data-[state=active]:text-white bg-slate-100 text-slate-600 hover:bg-slate-200 capitalize">
                    {v === 'upload' ? <span className="flex items-center justify-center gap-1.5"><UploadSimple size={14}/> Upload</span> : <span className="flex items-center justify-center gap-1.5"><Camera size={14}/> Camera</span>}
                  </TabsPrimitive.Trigger>
                ))}
              </TabsPrimitive.List>

              <TabsPrimitive.Content value="upload">
                <div
                  className={cn('border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer', dragOver ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 hover:border-slate-300')}
                  onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileRef.current?.click()}
                >
                  <Image size={36} className="mx-auto mb-3 text-slate-400" />
                  <p className="text-sm font-medium text-slate-600">Drop image here</p>
                  <p className="text-xs text-slate-400 mt-1">or click to browse</p>
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
          <CardContent>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-500 capitalize mb-1.5">Part ID (optional)</label>
                <input value={partId} onChange={e => setPartId(e.target.value)} placeholder="e.g. PART-001"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 capitalize mb-1.5">Station ID (optional)</label>
                <input value={stationId} onChange={e => setStationId(e.target.value)} placeholder="e.g. STATION-A"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="min-h-96">
        {loading ? (
          <div className="h-full flex items-center justify-center py-20">
            <div className="text-center">
              <CircleNotch size={40} className="animate-spin text-indigo-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500">Running inspection…</p>
            </div>
          </div>
        ) : result ? (
          <div>
            <CardHeader>
              <div className="flex items-center gap-3">
                <DecisionBadge decision={result.decision} />
                <span className="text-sm text-slate-500">{(result.confidence * 100).toFixed(1)}% confidence</span>
              </div>
            </CardHeader>
            <div className="grid grid-cols-[1fr_240px] gap-4 p-6">
              <div>
                {(result.annotated_image || result.result_image) ? (
                  <img src={`/api/v1/images/${result.annotated_image || result.result_image}`} alt="Result" className="w-full rounded-xl border border-slate-200" />
                ) : (
                  <div className="aspect-video bg-slate-100 rounded-xl flex items-center justify-center text-slate-400"><Image size={32} /></div>
                )}
              </div>
              <div className="space-y-2">
                {[
                  ['Objects Found', result.objects_found],
                  ['Confidence', `${(result.confidence * 100).toFixed(1)}%`],
                  ['Detection', `${result.detection_time_ms?.toFixed(0)}ms`],
                  ['Segmentation', `${result.segmentation_time_ms?.toFixed(0)}ms`],
                  ['Total Time', `${result.total_time_ms?.toFixed(0)}ms`],
                ].map(([l, v]) => (
                  <div key={l as string} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                    <span className="text-xs text-slate-500">{l}</span>
                    <span className="text-sm font-semibold text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
            </div>
            {result.vlm_description && (
              <div className="px-6 pb-4">
                <div className="p-4 bg-indigo-50 border border-indigo-100 rounded-xl">
                  <p className="text-xs font-bold text-indigo-500 uppercase tracking-wide mb-2">AI Analysis · Llama 3.2 Vision</p>
                  <MiniMarkdown text={result.vlm_description} />
                </div>
              </div>
            )}
            {result.detections?.length > 0 && (
              <div className="px-6 pb-6 border-t border-slate-100 pt-4">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Detected Objects</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100">
                      {['Class', 'Confidence', 'Bounding Box'].map(h => (
                        <th key={h} className="pb-2 text-left text-xs font-semibold text-slate-500 capitalize">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.detections.map((d, i) => (
                      <tr key={i} className="border-b border-slate-50">
                        <td className="py-2 font-medium text-slate-700">{d.class_name}</td>
                        <td className="py-2 text-slate-600">{(d.confidence * 100).toFixed(1)}%</td>
                        <td className="py-2 text-slate-400 text-xs font-mono">
                          {d.box
                            ? `${Math.round(d.box.x1)}, ${Math.round(d.box.y1)}, ${Math.round(d.box.x2)}, ${Math.round(d.box.y2)}`
                            : d.bbox?.map(v => Math.round(v)).join(', ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center py-20">
            <div className="text-center text-slate-400">
              <Image size={48} className="mx-auto mb-3" />
              <p className="font-medium text-slate-500">No inspection yet</p>
              <p className="text-sm mt-1">UploadSimple an image to run inspection</p>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
