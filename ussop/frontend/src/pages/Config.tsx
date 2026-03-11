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
    <div>
      <label className="block text-xs font-semibold text-slate-500 capitalize mb-1.5">{label}</label>
      {children}
    </div>
  )
}

function TextInput({ value, onChange, placeholder, mono }: { value: string; onChange: (v: string) => void; placeholder?: string; mono?: boolean }) {
  return (
    <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className={`w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${mono ? 'font-mono' : ''}`} />
  )
}

function NumInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <input type="number" value={value} onChange={e => onChange(Number(e.target.value))}
      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${checked ? 'bg-indigo-600' : 'bg-slate-300'}`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
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
        <CardHeader><h2 className="font-semibold text-slate-900">General</h2></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Station ID">
              <TextInput value={config.station_id} onChange={v => update('station_id', v)} mono />
            </Field>
            <Field label="API Port">
              <NumInput value={config.api_port} onChange={v => update('api_port', v)} />
            </Field>
            <Field label="Confidence Threshold">
              <div className="flex items-center gap-3">
                <input type="range" min="0" max="1" step="0.01" value={config.confidence_threshold}
                  onChange={e => update('confidence_threshold', parseFloat(e.target.value))}
                  className="flex-1 accent-indigo-600" />
                <span className="text-sm font-semibold w-12 text-slate-700">{(config.confidence_threshold * 100).toFixed(0)}%</span>
              </div>
            </Field>
            <Field label="Max Detections">
              <NumInput value={config.max_detections} onChange={v => update('max_detections', v)} />
            </Field>
            <Field label="Debug Mode">
              <Toggle checked={config.debug} onChange={v => update('debug', v)} />
            </Field>
            <Field label="Active Learning">
              <Toggle checked={config.active_learning_enabled} onChange={v => update('active_learning_enabled', v)} />
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Camera */}
      <Card>
        <CardHeader><h2 className="font-semibold text-slate-900">Camera</h2></CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Camera Type">
              <select value={config.camera_type} onChange={e => update('camera_type', e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                <option value="webcam">Webcam</option>
                <option value="basler">Basler</option>
                <option value="hikvision">Hikvision</option>
                <option value="file">File / Folder</option>
              </select>
            </Field>
            <Field label="Camera Index">
              <NumInput value={config.camera_index} onChange={v => update('camera_index', v)} />
            </Field>
            <Field label="FPS">
              <NumInput value={config.camera_fps} onChange={v => update('camera_fps', v)} />
            </Field>
            <Field label="Width">
              <NumInput value={config.camera_width} onChange={v => update('camera_width', v)} />
            </Field>
            <Field label="Height">
              <NumInput value={config.camera_height} onChange={v => update('camera_height', v)} />
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Model */}
      <Card>
        <CardHeader><h2 className="font-semibold text-slate-900">Model</h2></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Detector Backbone">
              <select value={config.detector_backbone} onChange={e => update('detector_backbone', e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                <option value="mobilenet_v3_large">MobileNet v3 Large (fast)</option>
                <option value="resnet50">ResNet-50 (accurate)</option>
              </select>
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card>
        <CardHeader><h2 className="font-semibold text-slate-900">Integrations</h2></CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <Toggle checked={config.modbus_enabled} onChange={v => update('modbus_enabled', v)} />
                <span className="font-medium text-sm text-slate-800">Modbus TCP (PLC)</span>
              </div>
              {config.modbus_enabled && (
                <div className="grid grid-cols-2 gap-4 pl-14">
                  <Field label="Host">
                    <TextInput value={config.modbus_host} onChange={v => update('modbus_host', v)} placeholder="192.168.1.100" mono />
                  </Field>
                  <Field label="Port">
                    <NumInput value={config.modbus_port} onChange={v => update('modbus_port', v)} />
                  </Field>
                </div>
              )}
            </div>

            <div className="border-t border-slate-100 pt-4">
              <div className="flex items-center gap-3 mb-3">
                <Toggle checked={config.mqtt_enabled} onChange={v => update('mqtt_enabled', v)} />
                <span className="font-medium text-sm text-slate-800">MQTT (IoT)</span>
              </div>
              {config.mqtt_enabled && (
                <div className="grid grid-cols-2 gap-4 pl-14">
                  <Field label="Broker">
                    <TextInput value={config.mqtt_broker} onChange={v => update('mqtt_broker', v)} placeholder="mqtt.local" mono />
                  </Field>
                  <Field label="Port">
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
          <div className="flex items-center gap-2">
            <Brain size={18} className="text-indigo-500" />
            <h2 className="font-semibold text-slate-900">Vision Language Model (VLM)</h2>
          </div>
          {config.vlm_enabled && (
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${config.vlm_loaded ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-amber-50 text-amber-700 border-amber-100'}`}>
              {config.vlm_loaded
                ? <><CheckCircle size={12} /> Loaded</>
                : <><CircleNotch size={12} className="animate-spin" /> Not loaded yet</>}
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <Toggle checked={config.vlm_enabled} onChange={v => update('vlm_enabled', v)} />
              <span className="text-sm font-medium text-slate-700">Enable VLM (natural language defect descriptions &amp; AI Query)</span>
            </div>

            {config.vlm_enabled && (
              <div className="space-y-4 pt-2 border-t border-slate-100">
                <Field label="Backend">
                  <select value={config.vlm_backend} onChange={e => update('vlm_backend', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                    <option value="local">Local (offline — Moondream, LLaVA, etc.)</option>
                    <option value="anthropic">Anthropic (Claude)</option>
                    <option value="openai">OpenAI (GPT-4o)</option>
                    <option value="google">Google (Gemini)</option>
                    <option value="groq">Groq (LLaVA, fast)</option>
                    <option value="nim">NVIDIA NIM</option>
                  </select>
                </Field>

                {config.vlm_backend === 'local' && (
                  <div className="space-y-3">
                    <Field label="Local Model">
                      <select value={config.vlm_local_model} onChange={e => update('vlm_local_model', e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                        <option value="moondream2">Moondream 2 — 1.8B, ~3 GB RAM (recommended)</option>
                        <option value="internvl2">InternVL2 — 2B, ~4 GB RAM</option>
                        <option value="qwen2vl">Qwen2-VL — 2B, ~4 GB RAM</option>
                        <option value="phi35vision">Phi-3.5 Vision — 4B, ~5 GB RAM</option>
                        <option value="llava">LLaVA 1.5 — 7B, ~6 GB RAM</option>
                        <option value="paligemma">PaliGemma — 3B, ~5 GB RAM</option>
                      </select>
                    </Field>
                    <button onClick={downloadModel} disabled={downloading}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-700 text-sm font-semibold hover:bg-indigo-100 transition-colors disabled:opacity-60">
                      {downloading
                        ? <><CircleNotch size={14} className="animate-spin" /> Starting download…</>
                        : <><DownloadSimple size={14} /> Download {config.vlm_local_model}</>}
                    </button>
                    <p className="text-xs text-slate-400">Model downloads from HuggingFace into <code className="bg-slate-100 px-1 rounded">data/models/vlm/</code>. First inspection will load it automatically.</p>
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
                        className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
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
            <h2 className="font-semibold text-slate-900">Storage</h2>
            <Button variant="ghost" size="sm" onClick={cleanup} disabled={cleaningUp} className="gap-1.5 text-red-600 hover:bg-red-50">
              <Trash size={14} /> {cleaningUp ? 'Cleaning…' : 'Clean Up Old Files'}
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-6">
              {[
                { label: 'Images',   value: `${storage.images_gb.toFixed(2)} GB` },
                { label: 'Database', value: `${storage.database_mb.toFixed(1)} MB` },
                { label: 'Total',    value: `${storage.total_gb.toFixed(2)} GB` },
              ].map(({ label, value }) => (
                <div key={label} className="text-center p-4 bg-slate-50 rounded-xl">
                  <p className="text-xs font-semibold text-slate-500 capitalize">{label}</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end">
        <Button variant="primary" onClick={save} disabled={saving} className="px-8">
          {saving ? 'Saving…' : 'Save Configuration'}
        </Button>
      </div>
    </div>
  )
}
