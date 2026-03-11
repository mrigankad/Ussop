import { useEffect, useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { BatchJob } from '@/types/api'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { Plus, Play, X, ArrowClockwise } from '@phosphor-icons/react'

const statusColors: Record<string, string> = {
  pending:   'bg-slate-100/50 text-slate-600 border-slate-200',
  running:   'bg-olive-100/50 text-olive-600 border-olive-200',
  completed: 'bg-emerald-100/50 text-emerald-600 border-emerald-200',
  failed:    'bg-red-100/50 text-red-600 border-red-200',
}

function JobRow({ job, onStart, onCancel }: { job: BatchJob; onStart: (id: string) => void; onCancel: (id: string) => void }) {
  const pct = job.total_files > 0 ? (job.processed_files / job.total_files) * 100 : 0
  return (
    <tr className="border-b transition-all" style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
      <td className="px-6 py-4">
        <p className="font-semibold text-sm" style={{ color: 'var(--text)' }}>{job.name}</p>
        <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--muted)' }}>{job.input_dir}</p>
      </td>
      <td className="px-6 py-4">
        <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize border ${statusColors[job.status] ?? statusColors.pending}`}>
          {job.status}
        </span>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full overflow-hidden w-24" style={{ background: 'var(--surface-2)' }}>
            <div className="h-full bg-olive-500 rounded-full" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs whitespace-nowrap" style={{ color: 'var(--muted)' }}>{job.processed_files}/{job.total_files}</span>
        </div>
      </td>
      <td className="px-6 py-4 text-xs" style={{ color: 'var(--muted)' }}>{new Date(job.created_at).toLocaleString()}</td>
      <td className="px-6 py-4">
        <div className="flex gap-2">
          {job.status === 'pending' && (
            <button onClick={() => onStart(job.id)} className="px-3 py-1 text-xs font-medium bg-olive-600 text-white rounded-xl hover:bg-olive-700 flex items-center gap-1">
              <Play size={11} /> Start
            </button>
          )}
          {job.status === 'running' && (
            <button onClick={() => onCancel(job.id)} className="px-3 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-xl hover:bg-red-200 flex items-center gap-1">
              <X size={11} /> Cancel
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

export default function Batch() {
  const { toast } = useToast()
  const [jobs, setJobs] = useState<BatchJob[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [inputDir, setInputDir] = useState('')
  const [filePattern, setFilePattern] = useState('*.jpg')
  const [creating, setCreating] = useState(false)

  const loadJobs = useCallback(async () => {
    try {
      const data = await api.getBatchJobs()
      setJobs(data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    loadJobs()
    const id = setInterval(loadJobs, 5000)
    return () => clearInterval(id)
  }, [loadJobs])

  async function createJob() {
    if (!name || !inputDir) return
    setCreating(true)
    try {
      await api.createBatchJob({ name, input_dir: inputDir, file_pattern: filePattern })
      toast('Batch job created', 'success')
      setShowForm(false); setName(''); setInputDir(''); setFilePattern('*.jpg')
      loadJobs()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed to create job', 'error')
    } finally { setCreating(false) }
  }

  async function startJob(id: string) {
    try {
      await api.startBatchJob(id)
      toast('Job started', 'success')
      loadJobs()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed to start job', 'error')
    }
  }

  async function cancelJob(id: string) {
    try {
      await api.cancelBatchJob(id)
      toast('Job cancelled', 'info')
      loadJobs()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed to cancel job', 'error')
    }
  }

  const runningCount = jobs.filter(j => j.status === 'running').length

  return (
    <div className="space-y-6 animate-in">
      <div className="flex flex-col sm:flex-row items-center justify-between p-5 rounded-xl border backdrop-blur-md gap-4" style={{ background: 'color-mix(in srgb, var(--surface) 40%, transparent)', borderColor: 'var(--border-subtle)' }}>
        <div className="flex items-center gap-4 pl-2">
          <div className="flex items-center gap-2 px-4 py-2 border rounded-lg shadow-sm" style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
             <span className="text-[11px] font-semibold tracking-tight" style={{ color: 'var(--text)' }}>{jobs.length} Total Job{jobs.length !== 1 ? 's' : ''}</span>
          </div>
          {runningCount > 0 && (
            <div className="flex items-center gap-2 px-4 py-2 bg-olive-50 border border-olive-100 rounded-lg shadow-sm shadow-olive-900/5 animate-pulse">
              <div className="w-1.5 h-1.5 rounded-full bg-olive-500" />
              <span className="text-[11px] font-semibold text-olive-700 tracking-tight">
                {runningCount} Active Execution{runningCount !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={loadJobs} className="gap-2 text-[11px] font-bold border px-4 py-2.5 rounded-xl" style={{ borderColor: 'var(--border-subtle)', color: 'var(--muted)' }}>
            <ArrowClockwise size={14} weight="bold" /> Refresh
          </Button>
          <Button variant="primary" onClick={() => setShowForm(v => !v)} className="gap-2 text-[11px] font-semibold px-6 py-2.5 rounded-xl shadow-lg shadow-olive-900/10">
            <Plus size={16} weight="bold" /> New Batch Job
          </Button>
        </div>
      </div>

      {showForm && (
        <Card className="animate-in slide-in-from-top-4 duration-300">
          <CardHeader className="border-b p-8" style={{ borderColor: 'var(--border-subtle)' }}>
            <h2 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text)' }}>New Batch Job</h2>
            <p className="text-[10px] font-bold mt-1 tracking-wider" style={{ color: 'var(--muted)' }}>Configure a new processing task</p>
          </CardHeader>
          <CardContent className="p-8">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-8">
              <div>
                <label className="block text-[10px] font-semibold tracking-wider mb-2.5 pl-1" style={{ color: 'var(--muted)' }}>Job Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="Batch run 01"
                  className="w-full px-4 py-3 border rounded-xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-olive-50 transition-all focus:bg-white" style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold tracking-wider mb-2.5 pl-1" style={{ color: 'var(--muted)' }}>Folder Path</label>
                <input value={inputDir} onChange={e => setInputDir(e.target.value)} placeholder="/path/to/images"
                  className="w-full px-4 py-3 border rounded-xl text-[11px] font-semibold focus:outline-none focus:ring-2 focus:ring-olive-50 transition-all focus:bg-white font-mono" style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold tracking-wider mb-2.5 pl-1" style={{ color: 'var(--muted)' }}>File Pattern</label>
                <input value={filePattern} onChange={e => setFilePattern(e.target.value)} placeholder="*.jpg"
                  className="w-full px-4 py-3 border rounded-xl text-[11px] font-semibold focus:outline-none focus:ring-2 focus:ring-olive-50 transition-all focus:bg-white font-mono" style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }} />
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 mt-8 pt-8 border-t" style={{ borderColor: 'var(--border-subtle)' }}>
              <Button variant="primary" onClick={createJob} disabled={!name || !inputDir || creating} className="gap-2 px-8 py-3.5 text-[11px] font-semibold rounded-xl w-full sm:w-auto">
                {creating ? <><LoadingSpinner /> Creating...</> : <><Play size={14} weight="bold" /> Create Job</>}
              </Button>
              <Button variant="ghost" onClick={() => setShowForm(false)} className="px-8 text-[11px] font-bold" style={{ color: 'var(--muted)' }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="border-b p-8" style={{ borderColor: 'var(--border-subtle)' }}>
          <h2 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text)' }}>Job History</h2>
          <p className="text-[10px] font-bold mt-1 tracking-wider" style={{ color: 'var(--muted)' }}>Review past and running jobs</p>
        </CardHeader>
        {loading ? <div className="p-20"><LoadingSpinner /></div> : jobs.length === 0 ? (
          <div className="p-20">
            <EmptyState title="No Jobs Found" description="Create a new batch job to process multiple images at once" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
                  {['Job Name', 'Status', 'Progress', 'Created', 'Actions'].map(h => (
                    <th key={h} className="px-8 py-4 text-left text-[10px] font-semibold tracking-wider" style={{ color: 'var(--muted)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {jobs.map(job => <JobRow key={job.id} job={job} onStart={startJob} onCancel={cancelJob} />)}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
