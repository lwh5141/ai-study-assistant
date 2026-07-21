import { useState, useEffect, useCallback } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'

export interface ToastItem {
  id: string
  type: 'success' | 'error'
  message: string
}

// 全局 toast 状态（组件外可调用）
let addToastFn: ((type: 'success' | 'error', message: string) => void) | null = null

export function showToast(type: 'success' | 'error', message: string) {
  addToastFn?.(type, message)
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const addToast = useCallback((type: 'success' | 'error', message: string) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    setToasts((prev) => [...prev, { id, type, message }])
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  useEffect(() => {
    addToastFn = addToast
    return () => { addToastFn = null }
  }, [addToast])

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-16 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <Toast key={toast.id} item={toast} onDismiss={removeToast} />
      ))}
    </div>
  )
}

function Toast({ item, onDismiss }: { item: ToastItem; onDismiss: (id: string) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(item.id), 4000)
    return () => clearTimeout(timer)
  }, [item.id, onDismiss])

  const isSuccess = item.type === 'success'

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg bg-white min-w-[320px] max-w-[420px] animate-in slide-in-from-right ${
        isSuccess ? 'border-green-200' : 'border-red-200'
      }`}
    >
      {isSuccess ? (
        <CheckCircle className="w-5 h-5 text-green-500 shrink-0 mt-0.5" />
      ) : (
        <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
      )}
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${isSuccess ? 'text-green-800' : 'text-red-800'}`}>
          {isSuccess ? '上传成功' : '上传失败'}
        </p>
        <p className="text-sm text-gray-600 mt-0.5 break-words">{item.message}</p>
      </div>
      <button
        onClick={() => onDismiss(item.id)}
        className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
