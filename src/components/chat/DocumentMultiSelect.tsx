import { useState, useRef, useEffect, useCallback } from 'react'
import { ChevronDown, Search, X, Check } from 'lucide-react'
import type { Document } from '@/types/api'

interface DocumentMultiSelectProps {
  documents: Document[]
  selectedIds: string[]
  onChange: (ids: string[]) => void
}

export function DocumentMultiSelect({
  documents,
  selectedIds,
  onChange,
}: DocumentMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  const readyDocs = documents.filter((d) => d.status === 'ready')
  const filtered = query.trim()
    ? readyDocs.filter((d) => d.filename.toLowerCase().includes(query.toLowerCase()))
    : readyDocs

  const allSelected = readyDocs.length > 0 && selectedIds.length === readyDocs.length
  const noneSelected = selectedIds.length === 0

  // 点击外部关闭
  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
      setOpen(false)
      setQuery('')
    }
  }, [])

  useEffect(() => {
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open, handleClickOutside])

  // Esc 关闭
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  const toggle = (id: string) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((sid) => sid !== id))
    } else {
      onChange([...selectedIds, id])
    }
  }

  const selectAll = () => onChange(readyDocs.map((d) => d.id))
  const clearAll = () => onChange([])

  // 已选资料（用于 chip 展示）
  const selectedDocs = readyDocs.filter((d) => selectedIds.includes(d.id))
  const visibleChips = selectedDocs.slice(0, 3)
  const overflowCount = Math.max(0, selectedDocs.length - 3)

  return (
    <div ref={containerRef} className="relative">
      {/* 触发区域 */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors shrink-0"
        >
          <span>
            {noneSelected
              ? '选择资料'
              : `已选 ${selectedIds.length} 份资料`}
          </span>
          <ChevronDown
            className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`}
          />
        </button>

        {/* 已选 chip 标签 */}
        {!noneSelected && (
          <>
            {visibleChips.map((doc) => (
              <span
                key={doc.id}
                className="inline-flex items-center gap-1 rounded-md border border-primary-200 bg-primary-50 px-2 py-1 text-xs text-primary-700 shrink-0"
              >
                <span className="max-w-[140px] truncate">
                  {doc.filename}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onChange(selectedIds.filter((id) => id !== doc.id))
                  }}
                  className="ml-0.5 rounded-sm p-0.5 hover:bg-primary-100 transition-colors"
                  aria-label={`移除 ${doc.filename}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {overflowCount > 0 && (
              <span className="inline-flex items-center rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs text-gray-500 shrink-0">
                +{overflowCount}
              </span>
            )}
          </>
        )}
      </div>

      {/* 下拉面板 */}
      {open && (
        <div className="absolute left-0 top-full mt-1.5 z-40 w-[380px] rounded-xl border border-gray-200 bg-white shadow-lg animate-in fade-in slide-in-from-top-2 duration-150">
          {/* 搜索栏 */}
          <div className="flex items-center gap-2 px-3 py-2.5 border-b border-gray-100">
            <Search className="w-4 h-4 text-gray-400 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索资料..."
              className="flex-1 text-sm text-gray-900 placeholder-gray-400 outline-none bg-transparent"
              autoFocus
            />
          </div>

          {/* 操作栏 */}
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-50">
            <button
              type="button"
              onClick={allSelected ? clearAll : selectAll}
              className="text-xs text-primary-600 hover:text-primary-700 transition-colors"
            >
              {allSelected ? '清空全部' : '全选'}
            </button>
            {!noneSelected && (
              <span className="text-xs text-gray-400">
                已选 {selectedIds.length}/{readyDocs.length} 份
              </span>
            )}
          </div>

          {/* 文档列表 */}
          <div className="max-h-[260px] overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-gray-400">
                {query.trim() ? '无匹配资料' : '暂无可用资料'}
              </p>
            ) : (
              filtered.map((doc) => {
                const checked = selectedIds.includes(doc.id)
                return (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => toggle(doc.id)}
                    className="flex items-center gap-2.5 w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors"
                  >
                    {/* checkbox */}
                    <span
                      className={`shrink-0 w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                        checked
                          ? 'bg-primary-600 border-primary-600'
                          : 'border-gray-300'
                      }`}
                    >
                      {checked && <Check className="w-3 h-3 text-white" />}
                    </span>

                    {/* 文件图标 + 名称 */}
                    <span className="flex-1 min-w-0 flex items-center gap-2">
                      <span className="text-sm text-gray-700 truncate">
                        {doc.filename}
                      </span>
                    </span>

                    {/* 块数 */}
                    <span className="shrink-0 text-xs text-gray-400">
                      {doc.chunk_count} 块
                    </span>
                  </button>
                )
              })
            )}
          </div>

          {/* 底部提示 */}
          <div className="px-3 py-2 border-t border-gray-100">
            <p className="text-xs text-gray-400">
              {noneSelected
                ? '不选 = 全局检索对话'
                : '仅检索所选资料范围内的内容'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
