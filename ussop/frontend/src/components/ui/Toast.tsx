import React, { createContext, useContext, useState, useCallback } from 'react'
import * as ToastPrimitive from '@radix-ui/react-toast'
import { cn } from '@/lib/cn'
import { CheckCircle, XCircle, Warning, Info, X } from '@phosphor-icons/react'

type ToastType = 'success' | 'error' | 'warning' | 'info'
interface ToastItem { id: number; message: string; type: ToastType }

interface ToastContextValue { toast: (message: string, type?: ToastType) => void }
const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

export function useToast() { return useContext(ToastContext) }

const icons = { success: CheckCircle, error: XCircle, warning: Warning, info: Info }
const styles = {
  success: 'bg-green-600 text-white',
  error:   'bg-red-600 text-white',
  warning: 'bg-amber-500 text-white',
  info:    'bg-blue-600 text-white',
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const toast = useCallback((message: string, type: ToastType = 'info') => {
    setToasts(prev => [...prev, { id: Date.now(), message, type }])
  }, [])
  const remove = (id: number) => setToasts(prev => prev.filter(t => t.id !== id))

  return (
    <ToastContext.Provider value={{ toast }}>
      <ToastPrimitive.Provider swipeDirection="right">
        {children}
        {toasts.map(t => {
          const Icon = icons[t.type]
          return (
            <ToastPrimitive.Root
              key={t.id}
              duration={t.type === 'error' ? 5000 : 3500}
              onOpenChange={open => { if (!open) remove(t.id) }}
              className={cn(
                'flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg text-sm font-medium',
                'data-[state=open]:animate-in data-[state=closed]:animate-out',
                'data-[swipe=end]:animate-out data-[state=closed]:fade-out-80',
                'data-[state=open]:slide-in-from-bottom-full',
                styles[t.type]
              )}
            >
              <Icon size={16} className="shrink-0" />
              <ToastPrimitive.Description className="flex-1">{t.message}</ToastPrimitive.Description>
              <ToastPrimitive.Close onClick={() => remove(t.id)}>
                <X size={14} />
              </ToastPrimitive.Close>
            </ToastPrimitive.Root>
          )
        })}
        <ToastPrimitive.Viewport className="fixed bottom-6 right-6 flex flex-col gap-2 z-50 w-80 max-w-full" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}
