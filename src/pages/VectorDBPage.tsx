import { useState, useEffect, useMemo } from 'react'
import {
  Database,
  Search,
  ChevronDown,
  ChevronUp,
  Circle,
  Hash,
  Layers,
  AlertTriangle,
  CheckCircle,
  FileText,
  Table2,
  BarChart3,
} from 'lucide-react'
import { getChunks, getVectorDBStats } from '@/api/client'
import type { ChunkItem, VectorDBStats, DocChunkStat } from '@/types/api'

export function VectorDBPage() {
  // ---- 状态 ----
  const [stats, setStats] = useState<VectorDBStats | null>(null)
  const [chunks, setChunks] = useState<ChunkItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filterDocId, setFilterDocId] = useState('')
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [mobileView, setMobileView] = useState<'stats' | 'table'>('table')

  // ---- 加载统计 ----
  useEffect(() => {
    getVectorDBStats()
      .then(setStats)
      .catch(() => {})
  }, [])

  // ---- 加载 chunk 列表 ----
  useEffect(() => {
    setLoading(true)
    getChunks({
      page,
      page_size: pageSize,
      document_id: filterDocId || undefined,
      search: search || undefined,
    })
      .then((data) => {
        setChunks(data.items)
        setTotal(data.total)
      })
      .catch(() => {
        setChunks([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [page, pageSize, filterDocId, search])

  // 切换筛选条件时回到第一页
  useEffect(() => {
    setPage(1)
  }, [filterDocId, search])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  // 文档筛选选项（去重）
  const docOptions = useMemo(() => {
    if (!stats?.by_document) return []
    return stats.by_document.filter((d) => d.chunk_count > 0)
  }, [stats])

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col overflow-hidden">
      {/* 移动端：顶部视图切换（< lg 显示） */}
      <div className="lg:hidden shrink-0 border-b border-gray-200 bg-white px-4 py-2">
        <div className="flex gap-1">
          <button
            onClick={() => setMobileView('table')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              mobileView === 'table'
                ? 'bg-primary-50 text-primary-700'
                : 'text-gray-500 hover:bg-gray-50'
            }`}
          >
            <Table2 className="w-4 h-4" />
            知识块
          </button>
          <button
            onClick={() => setMobileView('stats')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              mobileView === 'stats'
                ? 'bg-primary-50 text-primary-700'
                : 'text-gray-500 hover:bg-gray-50'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            统计
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
      {/* ======== 左侧：统计面板（桌面端 ≥ lg 显示，移动端按 mobileView 切换） ======== */}
      <aside className={`w-72 shrink-0 border-r border-gray-200 bg-white overflow-y-auto ${mobileView === 'stats' ? 'flex-1 w-full' : 'hidden'} lg:block lg:flex-none lg:w-72`}>
        <div className="p-4 space-y-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Database className="w-4 h-4 text-primary-500" />
            向量库概况
          </h2>

          {!stats ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-5 h-5 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin" />
            </div>
          ) : (
            <>
              {/* Collection 信息 */}
              <section>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Collection
                </h3>
                <div className="space-y-1.5 text-sm">
                  <InfoRow label="名称" value={stats.collection_name} />
                  <InfoRow label="距离算法" value={stats.distance_metric} />
                  <InfoRow
                    label="Embedding"
                    value="text-embedding-v4"
                    mono
                  />
                </div>
              </section>

              {/* 数量统计 */}
              <section>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  数据量
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  <StatCard
                    icon={Layers}
                    label="SQLite 块"
                    value={stats.sqlite_count}
                    color="text-blue-600"
                    bg="bg-blue-50"
                  />
                  <StatCard
                    icon={Hash}
                    label="ChromaDB 向量"
                    value={stats.chroma_count}
                    color="text-green-600"
                    bg="bg-green-50"
                  />
                </div>

                {/* 同步状态 */}
                <div className="mt-2 flex items-center gap-1.5 text-xs">
                  {stats.synced ? (
                    <>
                      <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                      <span className="text-green-600">数据已同步</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                      <span className="text-amber-600">
                        数据不一致（差值 {Math.abs(stats.sqlite_count - stats.chroma_count)}）
                      </span>
                    </>
                  )}
                </div>

                {/* 平均 token */}
                <div className="mt-2 text-xs text-gray-500">
                  平均 {stats.avg_tokens_per_chunk} tokens/块
                </div>
              </section>

              {/* 文档分布 */}
              <section>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  文档分布
                </h3>
                <div className="space-y-0.5 max-h-[30vh] overflow-y-auto">
                  {docOptions.length === 0 ? (
                    <p className="text-xs text-gray-400 py-4 text-center">
                      暂无数据
                    </p>
                  ) : (
                    docOptions.map((doc) => (
                      <DocumentBar key={doc.document_id} doc={doc} />
                    ))
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </aside>

      {/* ======== 右侧：知识块表格（桌面端 ≥ lg 显示，移动端按 mobileView 切换） ======== */}
      <main className={`flex-1 flex flex-col min-w-0 bg-gray-50 ${mobileView === 'table' ? 'flex' : 'hidden'} lg:flex`}>
        {/* 工具栏 */}
        <div className="shrink-0 border-b border-gray-200 bg-white px-4 py-3">
          <div className="flex items-center gap-3">
            {/* 搜索 */}
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索知识块内容..."
                className="w-full rounded-lg border border-gray-200 bg-white pl-8 pr-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 outline-none focus:border-primary-300 focus:ring-1 focus:ring-primary-300"
              />
            </div>

            {/* 文档筛选 */}
            <select
              value={filterDocId}
              onChange={(e) => setFilterDocId(e.target.value)}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-primary-300 focus:ring-1 focus:ring-primary-300"
            >
              <option value="">全部文档</option>
              {docOptions.map((d) => (
                <option key={d.document_id} value={d.document_id}>
                  {d.document_name} ({d.chunk_count})
                </option>
              ))}
            </select>

            {/* 总数 */}
            <span className="text-xs text-gray-400 ml-auto">
              共 {total} 条
            </span>
          </div>
        </div>

        {/* 表格 */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin" />
            </div>
          ) : chunks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FileText className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm text-gray-400">
                {search || filterDocId ? '无匹配的知识块' : '暂无知识块数据，请先上传资料'}
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="sticky top-0 bg-gray-100 text-left">
                  <th className="px-4 py-2.5 font-medium text-gray-500 w-1/12">
                    #
                  </th>
                  <th className="px-4 py-2.5 font-medium text-gray-500 w-1/6">
                    文档
                  </th>
                  <th className="px-4 py-2.5 font-medium text-gray-500">
                    内容预览
                  </th>
                  <th className="px-4 py-2.5 font-medium text-gray-500 w-20 text-right">
                    Tokens
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {chunks.map((chunk) => {
                  const isExpanded = expandedId === chunk.id
                  return (
                    <>
                      <tr
                        key={chunk.id}
                        onClick={() =>
                          setExpandedId(isExpanded ? null : chunk.id)
                        }
                        className={`cursor-pointer transition-colors ${
                          isExpanded
                            ? 'bg-primary-50'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                          {chunk.chunk_index}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                            <span className="text-gray-700 truncate max-w-[160px]">
                              {chunk.document_name}
                            </span>
                          </div>
                          {chunk.page_number && (
                            <span className="text-xs text-gray-400 ml-5">
                              p.{chunk.page_number}
                              {chunk.section_title &&
                                ` · ${chunk.section_title}`}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-start gap-2">
                            <span className="text-gray-600 line-clamp-2 flex-1">
                              {chunk.content}
                            </span>
                            <span className="shrink-0 text-gray-400 mt-0.5">
                              {isExpanded ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-400 font-mono text-xs">
                          {chunk.token_count ?? '-'}
                        </td>
                      </tr>
                      {/* 展开详情 */}
                      {isExpanded && (
                        <tr>
                          <td
                            colSpan={4}
                            className="px-4 py-4 bg-primary-50/50"
                          >
                            <div className="space-y-3">
                              <div className="flex items-center gap-4 text-xs text-gray-500">
                                <span>
                                  <span className="font-medium">ID:</span>{' '}
                                  <code className="text-gray-700">{chunk.id}</code>
                                </span>
                                <span>
                                  <span className="font-medium">Chroma:</span>{' '}
                                  <code className="text-gray-700">
                                    {chunk.chroma_id}
                                  </code>
                                </span>
                                <span>
                                  <span className="font-medium">页:</span>{' '}
                                  {chunk.page_number ?? '-'}
                                </span>
                                <span>
                                  <span className="font-medium">节:</span>{' '}
                                  {chunk.section_title || '-'}
                                </span>
                              </div>
                              <div className="rounded-lg border border-primary-200 bg-white p-4">
                                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                                  {chunk.content}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="shrink-0 border-t border-gray-200 bg-white px-4 py-3 flex items-center justify-center gap-1">
            <PageBtn
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              上一页
            </PageBtn>
            {renderPageNumbers(page, totalPages, setPage)}
            <PageBtn
              onClick={() =>
                setPage((p) => Math.min(totalPages, p + 1))
              }
              disabled={page >= totalPages}
            >
              下一页
            </PageBtn>
            <span className="ml-3 text-xs text-gray-400">
              {page} / {totalPages}
            </span>
          </div>
        )}
      </main>
      </div>
    </div>
  )
}

// ---- 子组件 ----

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-500">{label}</span>
      <span
        className={`text-gray-800 ${mono ? 'font-mono text-xs' : ''}`}
      >
        {value}
      </span>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  bg,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  color: string
  bg: string
}) {
  return (
    <div className={`rounded-lg ${bg} p-3`}>
      <div className={`flex items-center gap-1.5 ${color} mb-1`}>
        <Icon className="w-3.5 h-3.5" />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className={`text-xl font-semibold ${color}`}>{value}</p>
    </div>
  )
}

function DocumentBar({ doc }: { doc: DocChunkStat }) {
  // 简单柱状图（相对宽度）
  const maxBlocks = 100 // 假设最多 100 块用于比例参考
  const widthPct = Math.min(100, (doc.chunk_count / maxBlocks) * 100)

  return (
    <div className="group flex items-center gap-2 py-1">
      <span className="text-xs text-gray-500 truncate flex-1">
        {doc.document_name}
      </span>
      <div className="flex items-center gap-2 w-24 shrink-0">
        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary-400 rounded-full transition-all"
            style={{ width: `${widthPct}%` }}
          />
        </div>
        <span className="text-xs text-gray-400 font-mono w-6 text-right">
          {doc.chunk_count}
        </span>
      </div>
    </div>
  )
}

function PageBtn({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void
  disabled: boolean
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-3 py-1.5 text-xs rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
    >
      {children}
    </button>
  )
}

function renderPageNumbers(
  current: number,
  total: number,
  setPage: (p: number) => void,
) {
  const pages: (number | '...')[] = []

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    if (current > 3) pages.push('...')

    const start = Math.max(2, current - 1)
    const end = Math.min(total - 1, current + 1)
    for (let i = start; i <= end; i++) pages.push(i)

    if (current < total - 2) pages.push('...')
    pages.push(total)
  }

  return pages.map((p, i) =>
    p === '...' ? (
      <span key={`dots-${i}`} className="px-2 text-xs text-gray-400">
        ...
      </span>
    ) : (
      <button
        key={p}
        onClick={() => setPage(p)}
        className={`w-8 h-8 text-xs rounded-md transition-colors ${
          p === current
            ? 'bg-primary-600 text-white'
            : 'text-gray-600 hover:bg-gray-100'
        }`}
      >
        {p}
      </button>
    ),
  )
}
