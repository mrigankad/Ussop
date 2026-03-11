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
    <div className="space-y-6 animate-in max-w-3xl mx-auto">
      <div className="flex items-center gap-3 bg-white/40 p-3 rounded-2xl border border-slate-200/60 shadow-sm backdrop-blur-md">
        <div className="w-8 h-8 rounded-lg bg-violet-50 border border-violet-100 flex items-center justify-center">
          <Lightning size={16} className="text-violet-600" weight="bold" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-700">AI Query Assistant</p>
          <p className="text-[11px] text-slate-400 font-medium">Ask questions about your inspection data in plain English</p>
        </div>
      </div>

      <Card className="flex flex-col" style={{ minHeight: '480px' }}>
        <CardContent className="flex-1 overflow-y-auto p-6 space-y-4" style={{ maxHeight: '480px' }}>
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center gap-6 py-8">
              <div className="w-16 h-16 rounded-2xl bg-violet-50 border border-violet-100 flex items-center justify-center shadow-sm">
                <Robot size={32} weight="duotone" className="text-violet-600" />
              </div>
              <div className="text-center">
                <p className="text-sm font-extrabold text-slate-800">Ask anything about your data</p>
                <p className="text-xs text-slate-400 font-medium mt-1">Powered by the configured VLM backend</p>
              </div>
              <div className="grid grid-cols-2 gap-2 w-full max-w-lg">
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => send(s)}
                    className="text-left text-xs font-semibold text-slate-600 bg-slate-50 hover:bg-violet-50 hover:text-violet-700 border border-slate-200 hover:border-violet-200 rounded-xl px-4 py-3 transition-all">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border shadow-sm ${
                m.role === 'user' ? 'bg-indigo-50 border-indigo-100' :
                m.role === 'error' ? 'bg-red-50 border-red-100' : 'bg-violet-50 border-violet-100'
              }`}>
                {m.role === 'user'
                  ? <User size={14} weight="duotone" className="text-indigo-600" />
                  : <Robot size={14} weight="duotone" className={m.role === 'error' ? 'text-red-600' : 'text-violet-600'} />
                }
              </div>
              <div className={`flex-1 max-w-[85%] ${m.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                <div className={`px-4 py-3 rounded-2xl text-sm font-medium leading-relaxed whitespace-pre-wrap ${
                  m.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-sm shadow-[0_4px_15px_rgba(79,70,229,0.2)]'
                    : m.role === 'error'
                    ? 'bg-red-50 text-red-700 border border-red-100 rounded-tl-sm'
                    : 'bg-white text-slate-700 border border-slate-100 rounded-tl-sm shadow-sm'
                }`}>
                  {m.text}
                </div>
                {m.backend && (
                  <p className="text-[10px] text-slate-400 font-medium flex items-center gap-1 px-1">
                    <Info size={10} /> via {m.backend}
                  </p>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-xl bg-violet-50 border border-violet-100 flex items-center justify-center shrink-0 shadow-sm">
                <Robot size={14} weight="duotone" className="text-violet-600" />
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white border border-slate-100 shadow-sm flex items-center gap-2">
                <Spinner size={14} className="text-violet-500 animate-spin" />
                <span className="text-sm text-slate-400 font-medium">Thinking…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </CardContent>

        <div className="border-t border-slate-100 p-4">
          <div className="flex gap-3 items-end">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a question about your inspection data… (Enter to send, Shift+Enter for newline)"
              rows={2}
              className="flex-1 resize-none px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 font-medium placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-300 transition-all"
            />
            <Button
              variant="primary"
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="gap-2 bg-violet-600 hover:bg-violet-700 text-white border-transparent shadow-[0_2px_10px_rgba(124,58,237,0.3)] hover:shadow-[0_4px_15px_rgba(124,58,237,0.4)] transition-all disabled:opacity-50 h-12 px-5"
            >
              <PaperPlaneRight size={16} weight="bold" />
            </Button>
          </div>
          <p className="text-[10px] text-slate-400 font-medium mt-2 text-center">
            Queries use recent statistics as context. VLM must be enabled in Configuration.
          </p>
        </div>
      </Card>
    </div>
  )
}
