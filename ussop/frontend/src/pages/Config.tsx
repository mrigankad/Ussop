import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { AppConfig } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { useToast } from '@/components/ui/Toast'
import { StorageUsage } from '@/types/api'
import { Trash, Brain, CircleNotch, CheckCircle, DownloadSimple } from '@phosphor-icons/react'
import React from 'react'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-[11px] font-bold text-slate-400 tracking-tight">{label}</label>
      {children}
    </div>
  )
}

function TextInput({ value, onChange, placeholder, mono }: { value: string; onChange: (v: string) => void; placeholder?: string; mono?: boolean }) {
  return (
    <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className={`w-full px-4 py-3 border border-slate-100 rounded-2xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50 transition-all focus:bg-white ${mono ? 'font-mono' : ''}`} />
  )
}

function NumInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <input type="number" value={value} onChange={e => onChange(Number(e.target.value))}
      className="w-full px-4 py-3 border border-slate-100 rounded-2xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50 transition-all focus:bg-white" />
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all ${checked ? 'bg-olive-600' : 'bg-slate-200'}`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'} shadow-sm`} />
    </button>
  )
}

export default function Config() {
  const { toast } = useToast()
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [storage, setStorage] = useState<StorageUsage | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [cleaningUp, setCleaningUp] = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    Promise.all([api.getConfig(), api.getStorageUsage()])
      .then(([c, s]) => { setConfig(c); setStorage(s) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  function update<K extends keyof AppConfig>(key: K, val: AppConfig[K]) {
    setConfig(prev => prev ? { ...prev, [key]: val } : prev)
  }

  async function save() {
    if (!config) return
    setSaving(true)
    try {
      await api.saveConfig(config)
      toast('Configuration saved', 'success')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed to save', 'error')
    } finally { setSaving(false) }
  }

  async function downloadModel() {
    if (!config) return
    setDownloading(true)
    try {
      await api.vlmDownload(config.vlm_local_model)
      toast(`Downloading ${config.vlm_local_model} in background — check server logs`, 'success')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Download failed', 'error')
    } finally { setDownloading(false) }
  }

  async function cleanup() {
    setCleaningUp(true)
    try {
      const r = await api.cleanupStorage()
      toast(`Deleted ${r.deleted_count} old files`, 'success')
      const s = await api.getStorageUsage()
      setStorage(s)
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Cleanup failed', 'error')
    } finally { setCleaningUp(false) }
  }

  if (loading || !config) return <LoadingSpinner />

  return (
    <div className="space-y-6 max-w-4xl">
      {/* General */}
      <Card>
        <CardHeader><h2 className="text-sm font-bold text-slate-900">Edge Device Parameters</h2></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
            <Field label="Station Identification">
              <TextInput value={config.station_id} onChange={v => update('station_id', v)} mono />
            </Field>
            <Field label="Network Interface Port">
              <NumInput value={config.api_port} onChange={v => update('api_port', v)} />
            </Field>
            <Field label="AI Confidence Threshold">
              <div className="flex items-center gap-4 py-1">
                <input type="range" min="0" max="1" step="0.01" value={config.confidence_threshold}
                  onChange={e => update('confidence_threshold', parseFloat(e.target.value))}
                  className="flex-1 accent-olive-600 h-1.5 bg-slate-100 rounded-lg appearance-none" />
                <span className="text-xs font-semibold w-10 text-slate-900">{(config.confidence_threshold * 100).toFixed(0)}%</span>
              </div>
            </Field>
            <Field label="Detection Limit Per Frame">
              <NumInput value={config.max_detections} onChange={v => update('max_detections', v)} />
            </Field>
            <Field label="Verbose Debugging Logs">
              <div className="pt-1"><Toggle checked={config.debug} onChange={v => update('debug', v)} /></div>
            </Field>
            <Field label="Autonomous Learning Engine">
              <div className="pt-1"><Toggle checked={config.active_learning_enabled} onChange={v => update('active_learning_enabled', v)} /></div>
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Camera */}
      <Card>
        <CardHeader><h2 className="text-sm font-bold text-slate-900">Imaging Hardware Strategy</h2></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
            <Field label="Active Sensor Variant">
              <select value={config.camera_type} onChange={e => update('camera_type', e.target.value)}
                className="w-full px-4 py-3 border border-slate-100 rounded-2xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50 transition-all focus:bg-white text-slate-900">
                <option value="webcam">Integrated Webcam</option>
                <option value="basler">Basler GigE Vision</option>
                <option value="hikvision">Hikvision IP Stream</option>
                <option value="file">Local File Directory</option>
              </select>
            </Field>
            <Field label="Device Bus Index">
              <NumInput value={config.camera_index} onChange={v => update('camera_index', v)} />
            </Field>
            <Field label="Sampling Framerate">
              <NumInput value={config.camera_fps} onChange={v => update('camera_fps', v)} />
            </Field>
            <Field label="Resolution Width (px)">
              <NumInput value={config.camera_width} onChange={v => update('camera_width', v)} />
            </Field>
            <Field label="Resolution Height (px)">
              <NumInput value={config.camera_height} onChange={v => update('camera_height', v)} />
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Model */}
      <Card>
        <CardHeader><h2 className="text-sm font-bold text-slate-900">Neural Inference Backbone</h2></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Architectural Variant">
              <select value={config.detector_backbone} onChange={e => update('detector_backbone', e.target.value)}
                className="w-full px-4 py-3 border border-slate-100 rounded-2xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50 transition-all focus:bg-white text-slate-900">
                <option value="mobilenet_v3_large">MobileNet V3 Large (Performance Optimized)</option>
                <option value="resnet50">ResNet-50 (Accuracy Optimized)</option>
              </select>
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card>
        <CardHeader><h2 className="text-sm font-bold text-slate-900">Digital Factory Integration</h2></CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <Toggle checked={config.modbus_enabled} onChange={v => update('modbus_enabled', v)} />
                <span className="text-xs font-bold text-slate-900">Modbus TCP Industrial Interface</span>
              </div>
              {config.modbus_enabled && (
                <div className="grid grid-cols-2 gap-4 pl-14">
                  <Field label="Host Address">
                    <TextInput value={config.modbus_host} onChange={v => update('modbus_host', v)} placeholder="192.168.1.100" mono />
                  </Field>
                  <Field label="Communication Port">
                    <NumInput value={config.modbus_port} onChange={v => update('modbus_port', v)} />
                  </Field>
                </div>
              )}
            </div>

            <div className="border-t border-slate-50 pt-6">
              <div className="flex items-center gap-3 mb-3">
                <Toggle checked={config.mqtt_enabled} onChange={v => update('mqtt_enabled', v)} />
                <span className="text-xs font-bold text-slate-900">MQTT IoT Message Broker</span>
              </div>
              {config.mqtt_enabled && (
                <div className="grid grid-cols-2 gap-4 pl-14">
                  <Field label="Broker Endpoint">
                    <TextInput value={config.mqtt_broker} onChange={v => update('mqtt_broker', v)} placeholder="mqtt.local" mono />
                  </Field>
                  <Field label="Broker Port">
                    <NumInput value={config.mqtt_port} onChange={v => update('mqtt_port', v)} />
                  </Field>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* VLM */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-olive-50 border border-olive-100 flex items-center justify-center">
              <Brain size={16} className="text-olive-600" weight="bold" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">Cognitive Vision Architecture (VLM)</h2>
          </div>
          {config.vlm_enabled && (
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-xl text-[10px] font-bold border ${config.vlm_loaded ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-amber-50 text-amber-700 border-amber-100'}`}>
              {config.vlm_loaded
                ? <><CheckCircle size={12} weight="bold" /> Runtime Ready</>
                : <><CircleNotch size={12} weight="bold" className="animate-spin" /> Provisioning Engine</>}
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <Toggle checked={config.vlm_enabled} onChange={v => update('vlm_enabled', v)} />
              <span className="text-xs font-bold text-slate-700">Enable Neural Description Language (Natural AI Query Capable)</span>
            </div>

            {config.vlm_enabled && (
              <div className="space-y-4 pt-6 border-t border-slate-50">
                <Field label="Compute Backend Strategy">
                  <select value={config.vlm_backend} onChange={e => update('vlm_backend', e.target.value)}
                    className="w-full px-4 py-3 border border-slate-100 rounded-2xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50 transition-all focus:bg-white text-slate-900">
                    <option value="local">Local Inference (Moondream/LLaVA Offline)</option>
                    <option value="anthropic">Anthropic Claude Hybrid</option>
                    <option value="openai">OpenAI GPT-4o Integration</option>
                    <option value="google">Google Gemini Pro Vision</option>
                    <option value="groq">Groq LPU Acceleration</option>
                    <option value="nim">NVIDIA NIM Microservice</option>
                  </select>
                </Field>

                {config.vlm_backend === 'local' && (
                  <div className="space-y-3">
                    <Field label="Local LLM Model Selection">
                      <select value={config.vlm_local_model} onChange={e => update('vlm_local_model', e.target.value)}
                        className="w-full px-4 py-3 border border-slate-100 rounded-2xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 bg-slate-50/50 transition-all focus:bg-white text-slate-900">
                        <option value="moondream2">Moondream 2 — 1.8B Highly Optimized (Recommended)</option>
                        <option value="internvl2">InternVL2 — 2B Balanced</option>
                        <option value="qwen2vl">Qwen2-VL — 2B Advanced</option>
                        <option value="phi35vision">Phi-3.5 Vision — 4B High Accuracy</option>
                        <option value="llava">LLaVA 1.5 — 7B Full Detail</option>
                        <option value="paligemma">PaliGemma — 3B Research</option>
                      </select>
                    </Field>
                    <div className="pt-2">
                       <button onClick={downloadModel} disabled={downloading} 
                          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-olive-50 border border-olive-100 text-olive-700 text-[11px] font-bold hover:bg-olive-100 transition-colors disabled:opacity-60">
                         {downloading
                            ? <><CircleNotch size={14} className="animate-spin" /> Fetching Weights…</>
                            : <><DownloadSimple size={14} weight="bold" /> Synchronize Model Assets</>}
                       </button>
                    </div>
                    <p className="text-[10px] text-slate-400 font-bold px-1">Synchronizes data from HuggingFace repositories into <code className="bg-slate-100 px-1 rounded">data/models/vlm/</code>.</p>
                  </div>
                )}

                {config.vlm_backend === 'anthropic' && (
                  <Field label="Anthropic API Key">
                    <TextInput value={config.anthropic_api_key || ''} onChange={v => update('anthropic_api_key', v)} placeholder="sk-ant-…" mono />
                  </Field>
                )}

                {config.vlm_backend === 'openai' && (
                  <Field label="OpenAI API Key">
                    <TextInput value={config.openai_api_key || ''} onChange={v => update('openai_api_key', v)} placeholder="sk-…" mono />
                  </Field>
                )}

                {config.vlm_backend === 'google' && (
                  <Field label="Google API Key">
                    <TextInput value={config.google_api_key || ''} onChange={v => update('google_api_key', v)} placeholder="AIza…" mono />
                  </Field>
                )}

                {config.vlm_backend === 'groq' && (
                  <Field label="Groq API Key">
                    <TextInput value={config.groq_api_key || ''} onChange={v => update('groq_api_key', v)} placeholder="gsk_…" mono />
                  </Field>
                )}

                {config.vlm_backend === 'nim' && (
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="NVIDIA NIM API Key">
                      <TextInput value={config.nvidia_nim_api_key || ''} onChange={v => update('nvidia_nim_api_key', v)} placeholder="nvapi-…" mono />
                    </Field>
                    <Field label="NIM Model">
                      <select value={config.nvidia_nim_model || ''} onChange={e => update('nvidia_nim_model', e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-olive-500 bg-white">
                        <option value="microsoft/phi-3-vision-128k-instruct">Phi-3 Vision</option>
                        <option value="meta/llama-3.2-11b-vision-instruct">Llama 3.2 11B Vision</option>
                        <option value="nvidia/neva-22b">NEVA 22B</option>
                        <option value="adept/fuyu-8b">Fuyu 8B</option>
                      </select>
                    </Field>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Storage */}
      {storage && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-bold text-slate-900">Data Lifecycle Management</h2>
            <Button variant="ghost" size="sm" onClick={cleanup} disabled={cleaningUp} className="gap-2 text-red-600 hover:bg-red-50 rounded-xl px-4">
              <Trash size={14} weight="bold" /> {cleaningUp ? 'Purging…' : 'Purge Analytics Cache'}
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-8">
              {[
                { label: 'Image Repository', value: `${storage.images_gb.toFixed(2)} GB` },
                { label: 'System Database',  value: `${storage.database_mb.toFixed(1)} MB` },
                { label: 'Total Footprint',   value: `${storage.total_gb.toFixed(2)} GB` },
              ].map(({ label, value }) => (
                <div key={label} className="p-5 bg-slate-50/50 rounded-2xl border border-slate-50">
                  <p className="text-[10px] font-bold text-slate-400 tracking-tight">{label}</p>
                  <p className="text-2xl font-semibold mt-2 tracking-tighter" style={{ color: 'var(--text)' }}>{value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end pt-4">
        <Button variant="primary" onClick={save} disabled={saving} className="px-12 py-6 text-sm font-semibold shadow-lg shadow-olive-900/10">
          {saving ? 'Synchronizing…' : 'Commit System Settings'}
        </Button>
      </div>
    </div>
  )
}
