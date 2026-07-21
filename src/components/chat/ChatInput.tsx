import { useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled: boolean
  loading: boolean
}

export function ChatInput({ value, onChange, onSend, disabled, loading }: ChatInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 收到回复后自动聚焦
  useEffect(() => {
    if (!loading && !disabled && inputRef.current) {
      inputRef.current.focus()
    }
  }, [loading, disabled])

  // 自动调整高度
  useEffect(() => {
    const el = inputRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 160) + 'px'
    }
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && !loading && value.trim()) {
        onSend()
      }
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="max-w-3xl mx-auto flex items-end gap-3">
        {/* 输入框 */}
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || loading}
            placeholder={
              loading ? '正在思考...' : '输入问题，回车发送，Shift+回车换行...'
            }
            rows={1}
            className="w-full resize-none rounded-lg border border-gray-200 bg-white px-4 py-2.5 pr-10 text-sm text-gray-900 placeholder-gray-400 outline-none transition-colors focus:border-primary-400 focus:ring-1 focus:ring-primary-400 disabled:bg-gray-50 disabled:text-gray-400"
          />

          {/* 加载动画 */}
          {loading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
            </div>
          )}
        </div>

        {/* 发送按钮 */}
        <button
          onClick={onSend}
          disabled={disabled || loading || !value.trim()}
          className="shrink-0 flex items-center justify-center w-9 h-9 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:bg-gray-200 disabled:text-gray-400 transition-colors"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* 提示文字 */}
      <p className="text-center text-xs text-gray-400 mt-2">
        AI 回答基于上传资料，请注意核查重要信息
      </p>
    </div>
  )
}
