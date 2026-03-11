import { useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { PaperPlaneRight, Robot, User, Lightning, Spinner, Info } from '@phosphor-icons/react'

interface Message {
  role: 'user' | 'assistant' | 'error'
  text: string
  backend?: string
}

const SUGGESTIONS = [
  'How many defects were found today?',
  'What is the pass rate over the last 7 days?',
  'Which defect type appears most often?',
  'Show me the average inspection cycle time this week.',
]

export default function Query() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(question = input.trim()) {
    if (!question || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: question }])
    setLoading(true)
    try {
      const res = await api.query(question)
      setMessages(prev => [...prev, { role: 'assistant', text: res.answer, backend: res.backend }])
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'error', text: e.message || 'Query failed.' }])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="space-y-8 animate-in max-w-4xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row items-center gap-4 p-5 rounded-xl border backdrop-blur-md" style={{ background: 'color-mix(in srgb, var(--surface) 40%, transparent)', borderColor: 'var(--border-subtle)' }}>
        <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 shadow-sm border" style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
          <Lightning size={20} className="text-olive-600" weight="bold" />
        </div>
        <div>
          <h1 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text)' }}>AI Search</h1>
          <p className="text-[11px] font-bold mt-1 tracking-wider" style={{ color: 'var(--muted)' }}>Ask questions about your inspection data</p>
        </div>
      </div>

      <Card className="flex flex-col overflow-hidden shadow-2xl shadow-slate-900/5" style={{ minHeight: '600px', borderColor: 'var(--border-subtle)' }}>
        <CardContent className="flex-1 overflow-y-auto p-4 sm:p-10 space-y-6" style={{ maxHeight: '600px', background: 'var(--surface-2)' }}>
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center gap-10 py-16">
              <div className="w-24 h-24 rounded-2xl border flex items-center justify-center shadow-xl shadow-slate-900/5 transition-transform hover:scale-110 duration-500" style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}>
                <Robot size={48} weight="duotone" className="text-olive-600" />
              </div>
              <div className="text-center space-y-2">
                <h2 className="text-lg font-semibold tracking-tight" style={{ color: 'var(--text)' }}>Search your data</h2>
                <p className="text-[11px] font-bold tracking-wider" style={{ color: 'var(--muted)' }}>AI-powered inspection analytics</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl px-4">
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => send(s)}
                    className="text-left text-xs font-bold transition-all shadow-sm hover:shadow-lg hover:shadow-olive-900/20 rounded-xl px-6 py-4 border hover:bg-olive-600 hover:text-white"
                    style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--muted)' }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-5 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'} animate-in slide-in-from-bottom-2 duration-500`}>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border shadow-sm ${
                m.role === 'user' ? '' :
                m.role === 'error' ? 'bg-red-50 border-red-100' : 'bg-olive-600 border-olive-600'
              }`} style={m.role === 'user' ? { background: 'var(--surface)', borderColor: 'var(--border-subtle)' } : undefined}>
                {m.role === 'user'
                  ? <User size={18} weight="bold" className="text-slate-600" />
                  : <Robot size={18} weight="bold" className={m.role === 'error' ? 'text-red-600' : 'text-white'} />
                }
              </div>
              <div className={`flex-1 max-w-[85%] ${m.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
                <div className={`px-6 py-4 rounded-xl text-[13px] font-bold leading-relaxed whitespace-pre-wrap shadow-sm ${
                  m.role === 'user'
                    ? 'bg-slate-900 text-white rounded-tr-none'
                    : m.role === 'error'
                    ? 'bg-white text-red-700 border border-red-100 rounded-tl-none'
                    : 'border rounded-tl-none shadow-olive-900/5'
                }`} style={(m.role === 'assistant' || m.role === 'error') ? { background: 'var(--surface)', borderColor: 'var(--border-subtle)', color: 'var(--text)' } : undefined}>
                  {m.text}
                </div>
                {m.backend && (
                  <div className="flex items-center gap-2 px-3 py-1 bg-slate-100/50 rounded-full border border-slate-50">
                    <span className="text-[10px] text-slate-400 font-semibold tracking-tighter">Strategy: {m.backend}</span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-5 animate-pulse">
              <div className="w-10 h-10 rounded-xl bg-olive-600 border border-olive-600 flex items-center justify-center shrink-0 shadow-lg shadow-olive-900/20">
                <Robot size={18} weight="bold" className="text-white" />
              </div>
              <div className="px-6 py-4 rounded-xl rounded-tl-none border border-slate-50 flex items-center gap-3 shadow-sm" style={{ background: 'var(--surface)' }}>
                <Spinner size={16} weight="bold" className="text-olive-600 animate-spin" />
                <span className="text-[11px] text-slate-400 font-semibold tracking-wider">Searching...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </CardContent>

        <div className="border-t border-slate-50 p-8 bg-white">
          <div className="flex flex-col sm:flex-row gap-4 items-end max-w-4xl mx-auto">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a question..."
              rows={2}
              className="flex-1 resize-none px-6 py-4 rounded-xl border text-[13px] font-bold placeholder:text-slate-300 focus:outline-none focus:ring-4 focus:ring-olive-50 focus:border-olive-200 transition-all focus:bg-white w-full"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)', color: 'var(--text)' }}
            />
            <Button
              variant="primary"
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="w-16 h-16 rounded-xl flex items-center justify-center p-0 shrink-0"
            >
              <PaperPlaneRight size={24} weight="bold" />
            </Button>
          </div>
          <p className="text-[10px] font-bold mt-6 text-center tracking-tight opacity-60" style={{ color: 'var(--muted)' }}>
            AI engine is active and analyzing your dataset
          </p>
        </div>
      </Card>
    </div>
  )
}
