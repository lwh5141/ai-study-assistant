import { useState, useEffect, useCallback, useRef } from 'react'
import { Trash2, RefreshCw, FileText, FileSpreadsheet, Loader2 } from 'lucide-react'
import { UploadZone } from '@/components/chat/UploadZone'
import { showToast } from '@/components/common/Toast'
import { getDocuments, uploadDocument, deleteDocument, reparseDocument } from '@/api/client'
import type { Document, FileType } from '@/types/api'

const TYPE_LABELS: Record<FileType, string> = {
  pdf: 'PDF',
  ppt: 'PPT',
  pptx: 'PPTX',
  md: 'MD',
  doc: 'Word',
  docx: 'Word',
  txt: 'TXT',
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  processing: { label: '解析中', className: 'bg-amber-100 text-amber-700' },
  ready: { label: '完成', className: 'bg-green-100 text-green-700' },
  error: { label: '失败', className: 'bg-red-100 text-red-700' },
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [uploading, setUploading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [retryingId, setRetryingId] = useState<string | null>(null)

  // 加载资料列表
  const loadDocuments = useCallback(async () => {
    try {
      const data = await getDocuments({ page_size: 100 })
      setDocuments(data.items)
    } catch {
      // 后端未启动时静默
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  // 轮询：有解析中的文档时每 2 秒刷新
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const hasProcessing = documents.some((d) => d.status === 'processing')

  useEffect(() => {
    if (hasProcessing && !pollingRef.current) {
      pollingRef.current = setInterval(loadDocuments, 2000)
    } else if (!hasProcessing && pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [hasProcessing, loadDocuments])

  // 上传文件
  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true)
      try {
        const result = await uploadDocument(file)
        showToast('success', `《${result.filename}》上传成功，正在解析中...`)
        await loadDocuments()
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : '上传失败，请重试'
        showToast('error', message)
      } finally {
        setUploading(false)
      }
    },
    [loadDocuments],
  )

  // 删除文件
  const handleDelete = useCallback(
    async (doc: Document) => {
      setDeletingId(doc.id)
      try {
        await deleteDocument(doc.id)
        showToast('success', `《${doc.filename}》已删除`)
        await loadDocuments()
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : '删除失败，请重试'
        showToast('error', message)
      } finally {
        setDeletingId(null)
      }
    },
    [loadDocuments],
  )

  // 重试 / 重新解析
  const handleRetry = useCallback(
    async (doc: Document) => {
      setRetryingId(doc.id)
      try {
        await reparseDocument(doc.id)
        const label = doc.status === 'error' ? '重试' : '重新解析'
        showToast('success', `《${doc.filename}》${label}中，正在后台处理...`)
        await loadDocuments()
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : '重试失败'
        showToast('error', message)
      } finally {
        setRetryingId(null)
      }
    },
    [loadDocuments],
  )

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h1 className="text-lg font-semibold text-gray-900 mb-1">上传资料</h1>
        <p className="text-sm text-gray-500 mb-4">
          上传学习资料，系统将自动解析并构建知识库
        </p>
        <UploadZone onUpload={handleUpload} uploading={uploading} />
      </div>

      {/* 资料列表 */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            已上传资料
            {documents.length > 0 && (
              <span className="ml-2 text-sm font-normal text-gray-400">
                ({documents.length})
              </span>
            )}
          </h2>
        </div>

        {documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FileSpreadsheet className="w-10 h-10 text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">暂无资料，请上传学习资料</p>
            <p className="text-xs text-gray-400 mt-1">
              支持 PDF、PPT、Word、Markdown、TXT 格式
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-[30%]">
                    文件名
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    类型
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    大小
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    分块
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-gray-50/50 transition-colors"
                  >
                    {/* 文件名 */}
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate max-w-[240px]">
                            {doc.filename}
                          </p>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {formatTime(doc.created_at)}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* 类型 */}
                    <td className="px-4 py-3">
                      <span className="inline-block rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                        {TYPE_LABELS[doc.file_type] || doc.file_type.toUpperCase()}
                      </span>
                    </td>

                    {/* 大小 */}
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {formatFileSize(doc.file_size)}
                    </td>

                    {/* 分块数 */}
                    <td className="px-4 py-3 text-sm text-gray-600 text-center">
                      {doc.status === 'ready' ? doc.chunk_count : '-'}
                    </td>

                    {/* 状态 */}
                    <td className="px-4 py-3 text-center">
                      <div className="relative group inline-block">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            STATUS_CONFIG[doc.status]?.className || ''
                          }`}
                        >
                          {doc.status === 'processing' && (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          )}
                          {STATUS_CONFIG[doc.status]?.label || doc.status}
                        </span>
                        {doc.status === 'error' && doc.error_message && (
                          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 hidden group-hover:block z-10">
                            <div className="bg-gray-800 text-white text-xs rounded-lg px-3 py-2 max-w-[280px] whitespace-pre-wrap shadow-lg">
                              {doc.error_message}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>

                    {/* 操作 */}
                    <td className="px-6 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {(doc.status === 'error' || doc.status === 'ready') && (
                          <button
                            onClick={() => handleRetry(doc)}
                            disabled={retryingId === doc.id}
                            className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors ${
                              doc.status === 'error'
                                ? 'text-red-600 hover:bg-red-50'
                                : 'text-gray-400 hover:text-primary-600 hover:bg-primary-50'
                            } disabled:opacity-50`}
                          >
                            <RefreshCw
                              className={`w-3.5 h-3.5 ${
                                retryingId === doc.id ? 'animate-spin' : ''
                              }`}
                            />
                            {doc.status === 'error' ? '重试' : '重新解析'}
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(doc)}
                          disabled={deletingId === doc.id}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
                        >
                          {deletingId === doc.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
