import { useState, useEffect, useCallback, useRef } from 'react'
import {
  FileText,
  CheckCircle2,
  BookOpen,
  TrendingUp,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Edit3,
} from 'lucide-react'
import { RadarChart } from '@/components/charts/RadarChart'
import { SmartTooltip } from '@/components/common/SmartTooltip'
import { getProgressOverview, getKnowledgePoints, getDocuments } from '@/api/client'
import type { ProgressOverview, KnowledgePoint, Document } from '@/types/api'

// ---- 常量 ----

const MASTERY_LABELS: Record<string, { label: string; color: string }> = {
  high: { label: '已掌握', color: 'bg-green-100 text-green-700' },
  medium: { label: '学习中', color: 'bg-amber-100 text-amber-700' },
  low: { label: '薄弱', color: 'bg-red-100 text-red-700' },
}

function getMasteryLevel(value: number): 'high' | 'medium' | 'low' {
  if (value >= 0.8) return 'high'
  if (value >= 0.5) return 'medium'
  return 'low'
}

const WEAK_THRESHOLD = 0.5  // 与 getMasteryLevel 的 low 阈值一致，避免徽章与专区矛盾

// ---- 笔记自动保存工具 ----

const NOTES_STORAGE_KEY = 'ai_study_notes'

function loadNotes(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(NOTES_STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

function saveNotes(notes: Record<string, string>) {
  localStorage.setItem(NOTES_STORAGE_KEY, JSON.stringify(notes))
}

// ---- 子组件 ----

function StatCard({
  icon: Icon,
  label,
  value,
  colorClass,
}: {
  icon: React.ElementType
  label: string
  value: string | number
  colorClass: string
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3.5 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${colorClass}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="min-w-0">
        <p className="text-lg font-semibold text-gray-900 leading-tight truncate">{value}</p>
        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      </div>
    </div>
  )
}

function ProgressBar({ value, size = 'md' }: { value: number; size?: 'sm' | 'md' }) {
  const pct = Math.round(value * 100)
  const barColor =
    value >= 0.8 ? 'bg-green-500' : value >= 0.5 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div
        className={`flex-1 bg-gray-100 rounded-full overflow-hidden ${
          size === 'sm' ? 'h-1.5' : 'h-2'
        }`}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 w-9 text-right">{pct}%</span>
    </div>
  )
}

function DocumentDetailCard({
  doc,
  noteMap,
  onNoteChange,
}: {
  doc: Document
  noteMap: Record<string, string>
  onNoteChange: (docId: string, text: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')
  const note = noteMap[doc.id] || ''
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  const handleNoteInput = (text: string) => {
    // 立即更新本地状态（父组件持久化）
    onNoteChange(doc.id, text)
    setSaveStatus('saving')
    // 延迟自动保存
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSaveStatus('saved')
      // 2 秒后恢复 idle
      setTimeout(() => setSaveStatus('idle'), 2000)
    }, 800)
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      {/* 标题栏 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-3.5 hover:bg-gray-50 transition-colors"
      >
        <FileText className="w-4 h-4 text-gray-400 shrink-0" />
        <span className="text-sm font-medium text-gray-900 truncate flex-1 text-left">
          {doc.filename}
        </span>
        <span
          className={`shrink-0 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
            doc.status === 'ready'
              ? 'bg-green-100 text-green-700'
              : doc.status === 'processing'
                ? 'bg-amber-100 text-amber-700'
                : 'bg-red-100 text-red-700'
          }`}
        >
          {doc.status === 'ready' ? '已解析' : doc.status === 'processing' ? '解析中' : '失败'}
        </span>
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
        )}
      </button>

      {/* 展开区域 */}
      {expanded && (
        <div className="px-5 pb-4 border-t border-gray-100 space-y-3 animate-in fade-in slide-in-from-top-1 duration-150">
          {/* 基本信息：label + value 横排，清晰层级 */}
          <div className="flex flex-wrap items-baseline gap-x-5 gap-y-2 pt-3 text-sm">
            <div className="flex items-baseline gap-1.5">
              <span className="text-xs text-gray-400">类型</span>
              <span className="text-sm font-medium text-gray-900">{doc.file_type.toUpperCase()}</span>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xs text-gray-400">分块</span>
              <span className="text-sm font-medium text-gray-900">{doc.chunk_count}</span>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xs text-gray-400">上传</span>
              <span className="text-sm font-medium text-gray-900">
                {new Date(doc.created_at).toLocaleDateString('zh-CN')}
              </span>
            </div>
          </div>

          {/* 笔记区域 */}
          <div className="pt-1">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Edit3 className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-xs font-medium text-gray-500">学习笔记</span>
              </div>
              {saveStatus === 'saving' && (
                <span className="text-xs text-gray-400">保存中…</span>
              )}
              {saveStatus === 'saved' && (
                <span className="text-xs text-green-600">已保存</span>
              )}
            </div>
            <div className="max-h-40 overflow-y-auto rounded-lg border border-gray-200 transition-colors focus-within:border-primary-400 focus-within:ring-1 focus-within:ring-primary-400">
              <textarea
                value={note}
                onChange={(e) => handleNoteInput(e.target.value)}
                onBlur={() => {
                  // 失焦时立即触发保存（清掉 pending 的 debounce）
                  if (debounceRef.current) {
                    clearTimeout(debounceRef.current)
                    setSaveStatus('saved')
                    setTimeout(() => setSaveStatus('idle'), 2000)
                  }
                }}
                placeholder="在此记录学习心得..."
                rows={4}
                className="w-full resize-none border-0 bg-transparent px-3 py-2.5 text-sm text-gray-700 placeholder-gray-400 outline-none"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---- 主页面 ----

export function ProgressPage() {
  const [overview, setOverview] = useState<ProgressOverview | null>(null)
  const [knowledgePoints, setKnowledgePoints] = useState<KnowledgePoint[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [noteMap, setNoteMap] = useState<Record<string, string>>(() => loadNotes())
  const [loading, setLoading] = useState(true)

  // 加载数据
  useEffect(() => {
    Promise.all([
      getProgressOverview().catch(() => null),
      getKnowledgePoints().catch(() => []),
      getDocuments({ page_size: 100 }).then((d) => d.items.filter((doc) => doc.status === 'ready')),
    ]).then(([ov, kp, docs]) => {
      setOverview(ov)
      setKnowledgePoints(kp as KnowledgePoint[])
      setDocuments(docs)
      setLoading(false)
    })
  }, [])

  // 笔记变更自动持久化
  const handleNoteChange = useCallback((docId: string, text: string) => {
    setNoteMap((prev) => {
      const next = { ...prev, [docId]: text }
      saveNotes(next)
      return next
    })
  }, [])

  // ---- 计算统计数据 ----

  const masteredCount = knowledgePoints.filter((k) => k.mastery_level >= 0.8).length
  const weakPoints = knowledgePoints.filter((k) => k.mastery_level < WEAK_THRESHOLD)
  const avgScore = overview ? Math.round(overview.avg_accuracy * 100) : 0

  // ---- 雷达图数据：取掌握度最低的 8 个（更有指导意义） ----

  const radarData = [...knowledgePoints]
    .sort((a, b) => a.mastery_level - b.mastery_level)
    .slice(0, 8)
    .map((k) => ({
      label: k.knowledge_point,
      value: k.mastery_level,
    }))

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-gray-400 text-sm">加载中...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6 animate-page-in">
      {/* ===== 0. 页面标题 ===== */}
      <div>
        <h1 className="text-lg font-semibold text-gray-900">学习进度</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          追踪知识点掌握情况，识别薄弱环节
        </p>
      </div>

      {/* ===== 1. 顶部统计卡片 ===== */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={FileText} label="资料总数" value={overview?.total_documents || 0} colorClass="bg-blue-50 text-blue-600" />
        <StatCard icon={BookOpen} label="测评次数" value={overview?.total_quizzes || 0} colorClass="bg-purple-50 text-purple-600" />
        <StatCard icon={TrendingUp} label="平均分" value={`${avgScore}分`} colorClass="bg-amber-50 text-amber-600" />
        <StatCard icon={CheckCircle2} label="已掌握知识点" value={masteredCount} colorClass="bg-green-50 text-green-600" />
      </div>

      {/* ===== 2. 中部：雷达图 + 知识点列表 ===== */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 雷达图 */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 min-h-[340px] flex flex-col">
          <h2 className="text-sm font-semibold text-gray-900 mb-1">
            知识点掌握雷达图
          </h2>
          <p className="text-xs text-gray-400 mb-3">
            展示掌握度最低的 {radarData.length} 个知识点
          </p>
          {radarData.length > 0 ? (
            <div className="flex-1 flex justify-center items-center">
              <RadarChart data={radarData} size={280} />
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
              暂无知识点数据，请先完成测评
            </div>
          )}
        </div>

        {/* 知识点列表 */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 min-h-[340px] flex flex-col">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">
            知识点掌握详情
          </h2>
          {knowledgePoints.length > 0 ? (
            <div className="flex-1 space-y-2.5 overflow-y-auto pr-1 max-h-[340px]">
              {knowledgePoints.map((kp) => {
                const level = getMasteryLevel(kp.mastery_level)
                const m = MASTERY_LABELS[level]
                const pct = Math.round(kp.mastery_level * 100)
                return (
                  <SmartTooltip
                    key={`${kp.knowledge_point}_${kp.document_name}`}
                    content={
                      <div className="space-y-0.5">
                        <div className="font-medium text-white">{kp.knowledge_point}</div>
                        <div className="text-gray-300">{kp.document_name}</div>
                        <div className="text-gray-400 mt-1">
                          掌握度 {pct}% · 共 {kp.total_questions} 题 · 正确 {kp.correct_count} 题
                        </div>
                      </div>
                    }
                  >
                    <div
                      className="border border-gray-100 rounded-lg px-3.5 py-2.5 cursor-default hover:border-gray-200 hover:bg-gray-50/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1.5 gap-2">
                        <span className="text-sm text-gray-900 font-medium truncate min-w-0">
                          {kp.knowledge_point}
                        </span>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${m.color}`}>
                          {m.label}
                        </span>
                      </div>
                      <ProgressBar value={kp.mastery_level} size="sm" />
                      <p className="text-xs text-gray-400 mt-1.5 truncate">
                        共 {kp.total_questions} 题 · 正确 {kp.correct_count} 题 · {kp.document_name}
                      </p>
                    </div>
                  </SmartTooltip>
                )
              })}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
              暂无知识点数据，请先完成测评
            </div>
          )}
        </div>
      </div>

      {/* ===== 3. 薄弱知识点专区 ===== */}
      {weakPoints.length > 0 && (
        <div className="bg-white border border-amber-200 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h2 className="text-sm font-semibold text-gray-900">
              薄弱知识点专区
              <span className="ml-2 text-xs font-normal text-amber-600">
                （掌握程度低于 {WEAK_THRESHOLD * 100}%）
              </span>
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {weakPoints.map((kp) => (
              <div
                key={`weak_${kp.knowledge_point}_${kp.document_name}`}
                className="border border-amber-100 bg-amber-50/30 rounded-lg px-4 py-3"
              >
                <p className="text-sm font-medium text-gray-900 truncate">
                  {kp.knowledge_point}
                </p>
                <p className="text-xs text-gray-500 truncate mt-0.5">
                  {kp.document_name}
                </p>
                <p className="text-xs text-gray-600 mt-1.5">
                  正确率 {Math.round(kp.mastery_level * 100)}% · 共 {kp.total_questions} 题仅答对 {kp.correct_count} 题
                </p>
                <div className="mt-2">
                  <ProgressBar value={kp.mastery_level} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===== 4. 资料学习详情 ===== */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">
            资料学习详情
            {documents.length > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                ({documents.length} 份)
              </span>
            )}
          </h2>
        </div>

        {documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-sm text-gray-500">暂无已解析的资料</p>
            <p className="text-xs text-gray-400 mt-1">
              上传资料并等待解析完成后即可查看详情
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {documents.map((doc) => (
              <DocumentDetailCard
                key={doc.id}
                doc={doc}
                noteMap={noteMap}
                onNoteChange={handleNoteChange}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
