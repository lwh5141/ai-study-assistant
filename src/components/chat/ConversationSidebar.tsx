import { useState, useRef, useEffect } from 'react'
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  Pencil,
  Check,
  X,
  PanelLeftClose,
  PanelLeft,
  MoreHorizontal,
} from 'lucide-react'
import type { ChatSession } from '@/types/api'

// ---- 相对时间格式化 ----
function relativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diff = now - then

  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`

  const date = new Date(isoString)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

interface ConversationSidebarProps {
  sessions: ChatSession[]
  activeSessionId: string | null
  loading: boolean
  collapsed: boolean
  searchQuery: string
  onSearchChange: (q: string) => void
  onSelect: (sessionId: string) => void
  onNewChat: () => void
  onRename: (sessionId: string, title: string) => Promise<void>
  onDelete: (sessionId: string) => void
  onToggleCollapse: () => void
}

export function ConversationSidebar({
  sessions,
  activeSessionId,
  loading,
  collapsed,
  searchQuery,
  onSearchChange,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  onToggleCollapse,
}: ConversationSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [actionMenuId, setActionMenuId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const editInputRef = useRef<HTMLInputElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭菜单
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActionMenuId(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 编辑模式自动聚焦
  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus()
      editInputRef.current.select()
    }
  }, [editingId])

  const handleStartRename = (session: ChatSession) => {
    setEditingId(session.session_id)
    setEditTitle(session.title || '新对话')
    setActionMenuId(null)
  }

  const handleConfirmRename = async () => {
    if (!editingId || !editTitle.trim()) return
    try {
      await onRename(editingId, editTitle.trim())
    } finally {
      setEditingId(null)
      setEditTitle('')
    }
  }

  const handleCancelRename = () => {
    setEditingId(null)
    setEditTitle('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleConfirmRename()
    if (e.key === 'Escape') handleCancelRename()
  }

  const handleDelete = (sessionId: string) => {
    setActionMenuId(null)
    setConfirmDeleteId(sessionId)
  }

  const handleConfirmDelete = () => {
    if (confirmDeleteId) {
      onDelete(confirmDeleteId)
      setConfirmDeleteId(null)
    }
  }

  // 筛选后的会话列表
  const filteredSessions = searchQuery.trim()
    ? sessions.filter(
        (s) =>
          (s.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
          (s.preview || '').toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : sessions

  // 折叠状态
  if (collapsed) {
    return (
      <div className="flex flex-col items-center w-14 shrink-0 border-r border-gray-200 bg-gray-50/50 pt-4">
        <button
          onClick={onToggleCollapse}
          className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors mb-4"
          title="展开侧边栏"
        >
          <PanelLeft className="w-4 h-4" />
        </button>
        <button
          onClick={onNewChat}
          className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          title="新对话"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col w-64 shrink-0 border-r border-gray-200 bg-gray-50/50 h-full overflow-hidden">
      {/* 顶部操作区 */}
      <div className="shrink-0 px-3 py-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            历史对话
          </span>
          <button
            onClick={onToggleCollapse}
            className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            title="收起侧边栏"
          >
            <PanelLeftClose className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 新对话按钮 */}
        <button
          onClick={onNewChat}
          className="flex items-center gap-2 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors"
        >
          <Plus className="w-4 h-4" />
          新对话
        </button>

        {/* 搜索框 */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="搜索对话..."
            className="w-full rounded-lg border border-gray-200 bg-white pl-8 pr-3 py-1.5 text-sm text-gray-700 placeholder:text-gray-400 outline-none focus:border-primary-300 focus:ring-1 focus:ring-primary-300 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-gray-400 hover:text-gray-600"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin" />
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageSquare className="w-6 h-6 text-gray-300 mb-2" />
            <p className="text-xs text-gray-400">
              {searchQuery ? '无匹配的对话' : '暂无历史对话'}
            </p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {filteredSessions.map((session) => {
              const isActive = session.session_id === activeSessionId
              const isEditing = editingId === session.session_id

              return (
                <div key={session.session_id} className="group relative">
                  {/* 会话条目 */}
                  {isEditing ? (
                    <div className="flex items-center gap-1 px-2 py-2">
                      <input
                        ref={editInputRef}
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className="flex-1 rounded border border-primary-300 bg-white px-2 py-1 text-sm text-gray-900 outline-none focus:ring-1 focus:ring-primary-400"
                      />
                      <button
                        onClick={handleConfirmRename}
                        className="p-1 rounded text-green-600 hover:bg-green-50 transition-colors"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={handleCancelRename}
                        className="p-1 rounded text-gray-400 hover:bg-gray-100 transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => onSelect(session.session_id)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                        isActive
                          ? 'bg-primary-50 text-primary-900'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <p className="text-sm font-medium truncate flex-1">
                          {session.title || '新对话'}
                        </p>
                        <div className="relative" ref={actionMenuId === session.session_id ? menuRef : undefined}>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setActionMenuId(
                                actionMenuId === session.session_id
                                  ? null
                                  : session.session_id,
                              )
                            }}
                            className={`p-0.5 rounded transition-colors ${
                              actionMenuId === session.session_id
                                ? 'text-primary-600 bg-primary-100'
                                : 'text-gray-400 opacity-0 group-hover:opacity-100 hover:text-gray-600'
                            }`}
                          >
                            <MoreHorizontal className="w-3.5 h-3.5" />
                          </button>

                          {/* 操作菜单 */}
                          {actionMenuId === session.session_id && (
                            <div className="absolute right-0 top-6 z-20 w-28 rounded-lg border border-gray-200 bg-white shadow-lg py-1">
                              <button
                                onClick={() => handleStartRename(session)}
                                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 transition-colors"
                              >
                                <Pencil className="w-3 h-3" />
                                重命名
                              </button>
                              <button
                                onClick={() => handleDelete(session.session_id)}
                                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 transition-colors"
                              >
                                <Trash2 className="w-3 h-3" />
                                删除
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* 预览 */}
                      {session.preview && (
                        <p className="text-xs text-gray-400 truncate mt-0.5">
                          {session.preview}
                        </p>
                      )}

                      {/* 时间 */}
                      <p className="text-xs text-gray-400 mt-0.5">
                        {relativeTime(session.updated_at)}
                        {session.message_count > 0 && (
                          <span className="ml-2">
                            {session.message_count} 条消息
                          </span>
                        )}
                      </p>
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 删除确认弹窗 */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="bg-white rounded-xl shadow-xl p-6 mx-4 max-w-sm w-full">
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              确认删除
            </h3>
            <p className="text-sm text-gray-500 mb-5">
              此操作将永久删除该对话及其所有消息，无法恢复。
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
