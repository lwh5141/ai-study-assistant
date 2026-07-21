import { useState, useEffect, useRef, useCallback } from 'react'
import { MessageSquare, Plus, Menu, X } from 'lucide-react'
import { ChatMessage } from '@/components/chat/ChatMessage'
import { ChatInput } from '@/components/chat/ChatInput'
import { ConversationSidebar } from '@/components/chat/ConversationSidebar'
import { DocumentMultiSelect } from '@/components/chat/DocumentMultiSelect'
import {
  getDocuments,
  getSession,
  getSessions,
  deleteSession,
  renameSession,
  sendMessageStream,
} from '@/api/client'
import type { Document, ChatSource, ChatSession, SendMessageResponse } from '@/types/api'

const STORAGE_KEY = 'ai_study_session_id'

interface LocalMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
}

export function StudyPage() {
  // ---- 状态 ----
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  // 侧边栏状态
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // 初始加载状态
  const [initialLoading, setInitialLoading] = useState(true)

  // 新对话确认弹窗
  const [showNewChatConfirm, setShowNewChatConfirm] = useState(false)
  const [isRestoring, setIsRestoring] = useState(false)

  // ---- 初始化：并行加载资料列表 + 会话列表 + 恢复上次会话 ----
  useEffect(() => {
    const savedId = localStorage.getItem(STORAGE_KEY)

    Promise.all([
      getDocuments({ page_size: 100 })
        .then((data) => setDocuments(data.items.filter((d) => d.status === 'ready')))
        .catch(() => {}),
      getSessions()
        .then((data) => setSessions(data || []))
        .catch(() => setSessions([])),
    ]).then(() => {
      setInitialLoading(false)
      // 恢复上次会话
      if (savedId) restoreSession(savedId)
    })
  }, [])

  /** 从后端加载指定会话的消息 */
  const restoreSession = async (sid: string) => {
    setIsRestoring(true)
    try {
      const data = await getSession(sid)
      setSessionId(sid)
      setMessages(
        (data.messages || []).map((m) => ({
          id: m.message_id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          sources: m.sources as ChatSource[] | undefined,
        })),
      )
      localStorage.setItem(STORAGE_KEY, sid)
    } catch {
      // 会话已被删除或后端不可用
      localStorage.removeItem(STORAGE_KEY)
      setSessionId(null)
      setMessages([])
    } finally {
      setIsRestoring(false)
    }
  }

  // 刷新会话列表（发送消息后调用）
  const loadSessions = useCallback(() => {
    setSessionsLoading(true)
    getSessions()
      .then((data) => setSessions(data || []))
      .catch(() => setSessions([]))
      .finally(() => setSessionsLoading(false))
  }, [])

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // ---- 发送消息 ----
  const handleSend = () => {
    const text = inputValue.trim()
    if (!text || isStreaming) return

    const userMsg: LocalMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
    }

    setMessages((prev) => [...prev, userMsg])
    setInputValue('')
    setIsStreaming(true)

    // 创建占位的 AI 消息
    const assistantMsgId = `ai_${Date.now()}`
    setMessages((prev) => [
      ...prev,
      { id: assistantMsgId, role: 'assistant', content: '' },
    ])

    let fullContent = ''

    const controller = sendMessageStream(
      {
        session_id: sessionId || undefined,
        message: text,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      },
      // onToken
      (token) => {
        fullContent += token
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: fullContent } : m,
          ),
        )
      },
      // onDone
      (result: SendMessageResponse) => {
        abortRef.current = null
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, sources: result.sources }
              : m,
          ),
        )
        if (!sessionId && result.session_id) {
          setSessionId(result.session_id)
          localStorage.setItem(STORAGE_KEY, result.session_id)
          loadSessions()
        } else {
          loadSessions()
        }
        setIsStreaming(false)
      },
      // onError
      (err) => {
        abortRef.current = null
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: `抱歉，请求失败：${err.message}。请确认后端服务已启动。`,
                }
              : m,
          ),
        )
        setIsStreaming(false)
      },
    )

    abortRef.current = controller
  }

  // ---- 选择历史会话 ----
  const handleSelectSession = (sid: string) => {
    if (sid === sessionId) return
    if (isStreaming) {
      // 流式进行中，先取消
      abortRef.current?.abort()
      abortRef.current = null
      setIsStreaming(false)
    }
    restoreSession(sid)
  }

  // ---- 新对话 ----
  const handleNewChatRequest = () => {
    if (messages.length > 0) {
      // 当前有对话内容，先提示确认
      setShowNewChatConfirm(true)
    } else {
      // 当前为空对话，直接重置
      resetChat()
    }
  }

  const handleNewChatConfirm = () => {
    setShowNewChatConfirm(false)
    // 当前对话已通过后端自动保存，直接重置即可
    resetChat()
  }

  const handleNewChatCancel = () => {
    setShowNewChatConfirm(false)
  }

  const resetChat = () => {
    // 取消进行中的流式请求
    abortRef.current?.abort()
    abortRef.current = null
    setMessages([])
    setSessionId(null)
    setInputValue('')
    setIsStreaming(false)
    localStorage.removeItem(STORAGE_KEY)
    loadSessions()
  }

  // ---- 重命名会话 ----
  const handleRename = async (sid: string, title: string) => {
    await renameSession(sid, title)
    // 乐观更新本地列表
    setSessions((prev) =>
      prev.map((s) =>
        s.session_id === sid ? { ...s, title } : s,
      ),
    )
  }

  // ---- 删除会话 ----
  const handleDelete = async (sid: string) => {
    await deleteSession(sid)
    setSessions((prev) => prev.filter((s) => s.session_id !== sid))
    // 如果删除的是当前活动会话，重置
    if (sid === sessionId) {
      resetChat()
    }
  }

  // ---- 切换侧边栏折叠 ----
  const handleToggleCollapse = () => {
    setSidebarCollapsed((prev) => !prev)
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex overflow-hidden">
      {/* 桌面端：会话历史侧边栏（≥ md 显示） */}
      <div className="hidden md:block">
        <ConversationSidebar
          sessions={sessions}
          activeSessionId={sessionId}
          loading={sessionsLoading}
          collapsed={sidebarCollapsed}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onSelect={handleSelectSession}
          onNewChat={handleNewChatRequest}
          onRename={handleRename}
          onDelete={handleDelete}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* 移动端：会话侧边栏抽屉（< md 显示） */}
      {mobileSidebarOpen && (
        <div className="md:hidden fixed inset-0 z-50" onClick={() => setMobileSidebarOpen(false)}>
          <div className="absolute inset-0 bg-black/40 animate-in fade-in duration-150" />
          <div
            className="absolute left-0 top-0 h-full animate-in slide-in-from-left duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative h-full">
              <button
                onClick={() => setMobileSidebarOpen(false)}
                className="absolute -right-12 top-3 p-2 text-white bg-black/30 rounded-lg hover:bg-black/50"
                aria-label="关闭会话列表"
              >
                <X className="w-5 h-5" />
              </button>
              <ConversationSidebar
                sessions={sessions}
                activeSessionId={sessionId}
                loading={sessionsLoading}
                collapsed={false}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onSelect={(id) => {
                  handleSelectSession(id)
                  setMobileSidebarOpen(false)
                }}
                onNewChat={() => {
                  handleNewChatRequest()
                  setMobileSidebarOpen(false)
                }}
                onRename={handleRename}
                onDelete={handleDelete}
                onToggleCollapse={() => {}}
              />
            </div>
          </div>
        </div>
      )}

      {/* 右侧：主聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部操作栏 */}
        <div className="shrink-0 border-b border-gray-200 bg-white px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3">
            {/* 移动端：会话列表按钮 */}
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="md:hidden shrink-0 p-2 -ml-2 text-gray-600 hover:text-gray-900"
              aria-label="打开会话列表"
            >
              <Menu className="w-5 h-5" />
            </button>
            {/* 资料多选器 */}
            <DocumentMultiSelect
              documents={documents}
              selectedIds={selectedDocIds}
              onChange={setSelectedDocIds}
            />

            {/* 新对话按钮 */}
            <button
              onClick={handleNewChatRequest}
              disabled={isStreaming}
              className="shrink-0 flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 disabled:opacity-50 transition-colors"
            >
              <Plus className="w-4 h-4" />
              新对话
            </button>
          </div>
        </div>

        {/* 聊天区域 */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-4">
            {initialLoading ? (
              /* 初始加载中 */
              <div className="flex flex-col items-center justify-center h-full min-h-[50vh] text-center">
                <div className="w-8 h-8 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin mb-3" />
                <p className="text-sm text-gray-400">加载中...</p>
              </div>
            ) : isRestoring ? (
              /* 恢复中 */
              <div className="flex flex-col items-center justify-center h-full min-h-[50vh] text-center">
                <div className="w-8 h-8 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin mb-3" />
                <p className="text-sm text-gray-400">加载对话历史...</p>
              </div>
            ) : messages.length === 0 ? (
              /* 空状态 */
              <div className="flex flex-col items-center justify-center h-full min-h-[50vh] text-center">
                <div className="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center mb-4">
                  <MessageSquare className="w-6 h-6 text-primary-400" />
                </div>
                <p className="text-gray-900 font-medium text-lg mb-1">
                  选择资料，开始对话吧
                </p>
                <p className="text-gray-400 text-sm max-w-sm">
                  上传资料后即可基于资料内容进行问答，AI 将准确引用资料来源
                </p>
              </div>
            ) : (
              /* 消息列表 */
              messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                />
              ))
            )}
          </div>
        </div>

        {/* 底部输入区域 */}
        <div className="shrink-0">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            disabled={false}
            loading={isStreaming}
          />
        </div>
      </div>

      {/* 新对话确认弹窗 */}
      {showNewChatConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="bg-white rounded-xl shadow-xl p-6 mx-4 max-w-sm w-full">
            <div className="w-10 h-10 rounded-full bg-primary-50 flex items-center justify-center mb-4">
              <MessageSquare className="w-5 h-5 text-primary-500" />
            </div>
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              开始新对话
            </h3>
            <p className="text-sm text-gray-500 mb-5">
              当前对话将自动保存至历史记录，你可以在左侧边栏中随时恢复。
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={handleNewChatCancel}
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleNewChatConfirm}
                className="px-4 py-2 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors"
              >
                开始新对话
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
