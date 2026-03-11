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
  pending:   'bg-slate-100 text-slate-600',
  running:   'bg-indigo-100 text-indigo-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed:    'bg-red-100 text-red-700',
}

function JobRow({ job, onStart, onCancel }: { job: BatchJob; onStart: (id: string) => void; onCancel: (id: string) => void }) {
  const pct = job.total_files > 0 ? (job.processed_files / job.total_files) * 100 : 0
  return (
    <tr className="border-b border-slate-50 hover:bg-slate-50">
      <td className="px-6 py-4">
        <p className="font-medium text-slate-800 text-sm">{job.name}</p>
        <p className="text-xs text-slate-400 font-mono mt-0.5">{job.input_dir}</p>
      </td>
      <td className="px-6 py-4">
        <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${statusColors[job.status] ?? statusColors.pending}`}>
          {job.status}
        </span>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
            <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs text-slate-500 whitespace-nowrap">{job.processed_files}/{job.total_files}</span>
        </div>
      </td>
      <td className="px-6 py-4 text-xs text-slate-500">{new Date(job.created_at).toLocaleString()}</td>
      <td className="px-6 py-4">
        <div className="flex gap-2">
          {job.status === 'pending' && (
            <button onClick={() => onStart(job.id)} className="px-3 py-1 text-xs font-medium bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 flex items-center gap-1">
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500">{jobs.length} jobs</span>
          {runningCount > 0 && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700">
              {runningCount} running
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={loadJobs} className="gap-1.5">
            <ArrowClockwise size={14} /> Refresh
          </Button>
          <Button variant="primary" onClick={() => setShowForm(v => !v)} className="gap-1.5">
            <Plus size={16} /> New Job
          </Button>
        </div>
      </div>

      {showForm && (
        <Card>
          <CardHeader><h2 className="font-semibold text-slate-900">Create Batch Job</h2></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 capitalize mb-1.5">Job Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="Production Run #42"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 capitalize mb-1.5">Input Directory</label>
                <input value={inputDir} onChange={e => setInputDir(e.target.value)} placeholder="/data/images/batch01"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 capitalize mb-1.5">File Pattern</label>
                <input value={filePattern} onChange={e => setFilePattern(e.target.value)} placeholder="*.jpg"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono" />
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="primary" onClick={createJob} disabled={!name || !inputDir || creating} className="gap-1.5">
                {creating ? 'Creating…' : 'Create Job'}
              </Button>
              <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><h2 className="font-semibold text-slate-900">Batch Jobs</h2></CardHeader>
        {loading ? <LoadingSpinner /> : jobs.length === 0 ? (
          <EmptyState title="No batch jobs" description="Create a job to process a folder of images" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  {['Job', 'Status', 'Progress', 'Created', 'Actions'].map(h => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-semibold text-slate-500 capitalize">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobs.map(job => <JobRow key={job.id} job={job} onStart={startJob} onCancel={cancelJob} />)}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
