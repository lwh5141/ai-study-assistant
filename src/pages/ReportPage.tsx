import { useState, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Calendar,
  Download,
  Loader2,
  Sparkles,
  FileBarChart,
  ChevronRight,
  Clock,
  TrendingUp,
  AlertTriangle,
  BookOpen,
} from 'lucide-react'
import { showToast } from '@/components/common/Toast'
import { ScoreBadge } from '@/components/common/ScoreBadge'
import { generateReport, getReportList, getReport } from '@/api/client'
import { cn } from '@/lib/utils'
import type { WeeklyReport, ReportListItem } from '@/types/api'

// ---- 日期工具 ----

function getThisWeekRange(): { start: string; end: string } {
  const now = new Date()
  const day = now.getDay()
  const mondayOffset = day === 0 ? -6 : 1 - day // 周日时回退 6 天
  const monday = new Date(now)
  monday.setDate(now.getDate() + mondayOffset)
  monday.setHours(0, 0, 0, 0)

  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  sunday.setHours(23, 59, 59, 999)

  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { start: fmt(monday), end: fmt(sunday) }
}

function formatDateRange(start: string, end: string): string {
  return `${start} ~ ${end}`
}

// ---- 相对时间格式化（与 ConversationSidebar 行为一致，未来可提取到 lib/utils.ts） ----
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

// ---- 子组件：报告内容渲染 ----

function MarkdownBlock({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-lg font-semibold text-gray-900 mt-5 mb-2 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-semibold text-gray-900 mt-4 mb-1.5 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold text-gray-900 mt-3 mb-1 first:mt-0">{children}</h3>
        ),
        p: ({ children }) => (
          <p className="text-sm text-gray-700 leading-relaxed my-1.5">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc pl-5 text-sm text-gray-700 my-1.5 space-y-0.5">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal pl-5 text-sm text-gray-700 my-1.5 space-y-0.5">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="text-sm text-gray-700 leading-relaxed">{children}</li>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-gray-900">{children}</strong>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-primary-300 bg-primary-50/50 pl-3 py-1 my-2 text-sm text-gray-600 rounded-r">
            {children}
          </blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

function ReportContent({
  report,
  compact = false,
}: {
  report: WeeklyReport
  /** 紧凑模式：用于历史报告展开。隐藏"学习周报"标题（列表项已显示日期），下载按钮缩小 */
  compact?: boolean
}) {
  const { content: c } = report

  // 生成下载用的 Markdown
  const handleDownload = useCallback(() => {
    const md = `# 学习周报

**时间范围：** ${report.week_start} ~ ${report.week_end}

---

## 学习概况

${c.summary}

## 关键数据

- 学习时长：${c.study_time_hours} 小时
- 新上传资料：${c.new_documents} 份
- 完成测评：${c.quiz_count} 次
- 平均分：${c.avg_score} 分
- 成绩趋势：${c.accuracy_trend}

## 薄弱环节

${c.weak_points.map((wp) => `- **${wp.point}**（正确率 ${Math.round(wp.accuracy * 100)}%）：${wp.suggestion}`).join('\n')}

## 下周建议

${c.weekly_suggestion}

---
*生成于 ${new Date(report.generated_at).toLocaleString('zh-CN')}*
`

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `学习周报_${report.week_start}_${report.week_end}.md`
    a.click()
    URL.revokeObjectURL(url)
    showToast('success', '报告已下载')
  }, [report, c])

  return (
    <div className={compact ? 'space-y-4' : 'space-y-5'}>
      {/* 周报头部信息：compact 模式下隐藏标题，仅保留下载按钮 */}
      <div className={cn(
        'flex items-center justify-between',
        compact && 'gap-3'
      )}>
        {!compact && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              学习周报
            </h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {formatDateRange(report.week_start, report.week_end)}
            </p>
          </div>
        )}
        <button
          onClick={handleDownload}
          className={cn(
            'flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors',
            compact
              ? 'ml-auto px-2.5 py-1 text-xs'
              : 'px-3 py-1.5 text-sm'
          )}
        >
          <Download className={compact ? 'w-3 h-3' : 'w-4 h-4'} />
          下载
        </button>
      </div>

      {/* 关键数据卡片：compact 模式下保持紧凑 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-blue-50 rounded-lg px-3 py-2.5 flex items-center gap-2.5">
          <Clock className="w-4 h-4 text-blue-500 shrink-0" />
          <div>
            <p className="text-base font-semibold text-blue-700">{c.study_time_hours}h</p>
            <p className="text-xs text-blue-600">学习时长</p>
          </div>
        </div>
        <div className="bg-purple-50 rounded-lg px-3 py-2.5 flex items-center gap-2.5">
          <BookOpen className="w-4 h-4 text-purple-500 shrink-0" />
          <div>
            <p className="text-base font-semibold text-purple-700">{c.new_documents}</p>
            <p className="text-xs text-purple-600">新上传资料</p>
          </div>
        </div>
        <div className="bg-amber-50 rounded-lg px-3 py-2.5 flex items-center gap-2.5">
          <FileBarChart className="w-4 h-4 text-amber-500 shrink-0" />
          <div>
            <p className="text-base font-semibold text-amber-700">{c.quiz_count} 次</p>
            <p className="text-xs text-amber-600">完成测评</p>
          </div>
        </div>
        <div className="bg-green-50 rounded-lg px-3 py-2.5 flex items-center gap-2.5">
          <TrendingUp className="w-4 h-4 text-green-500 shrink-0" />
          <div>
            <p className="text-base font-semibold text-green-700">{c.avg_score}</p>
            <p className="text-xs text-green-600">平均分 {c.accuracy_trend}</p>
          </div>
        </div>
      </div>

      {/* 学习概况 */}
      <div className={cn(
        'bg-white border border-gray-200 rounded-lg',
        compact ? 'p-3' : 'p-4'
      )}>
        <h3 className="text-sm font-semibold text-gray-900 mb-2">学习内容总结</h3>
        <MarkdownBlock content={c.summary} />
      </div>

      {/* 薄弱环节 */}
      {c.weak_points.length > 0 && (
        <div className={cn(
          'bg-white border border-red-200 rounded-lg',
          compact ? 'p-3' : 'p-4'
        )}>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <h3 className="text-sm font-semibold text-gray-900">薄弱环节分析</h3>
          </div>
          <div className="space-y-2">
            {c.weak_points.map((wp, i) => (
              <div
                key={i}
                className="border border-red-100 bg-red-50/30 rounded-lg px-3.5 py-3"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-900">
                    {wp.point}
                  </span>
                  <span className="text-xs text-red-600 font-medium">
                    正确率 {Math.round(wp.accuracy * 100)}%
                  </span>
                </div>
                <p className="text-sm text-gray-600">{wp.suggestion}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 下周建议 */}
      <div className={cn(
        'bg-white border border-primary-200 rounded-lg',
        compact ? 'p-3' : 'p-4'
      )}>
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-4 h-4 text-primary-500" />
          <h3 className="text-sm font-semibold text-gray-900">下周学习建议</h3>
        </div>
        <MarkdownBlock content={c.weekly_suggestion} />
      </div>
    </div>
  )
}

// ---- 主页面 ----

export function ReportPage() {
  const thisWeek = getThisWeekRange()
  const [rangeMode, setRangeMode] = useState<'this_week' | 'custom'>('this_week')
  const [customStart, setCustomStart] = useState(thisWeek.start)
  const [customEnd, setCustomEnd] = useState(thisWeek.end)

  // 生成状态
  const [generating, setGenerating] = useState(false)
  const [genStage, setGenStage] = useState('')
  const [currentReport, setCurrentReport] = useState<WeeklyReport | null>(null)

  // 历史列表
  const [history, setHistory] = useState<ReportListItem[]>([])
  const [viewingReportId, setViewingReportId] = useState<string | null>(null)
  const [viewingReport, setViewingReport] = useState<WeeklyReport | null>(null)

  // 加载历史
  useEffect(() => {
    getReportList()
      .then(setHistory)
      .catch(() => {})
  }, [])

  // 重新加载历史
  const refreshHistory = useCallback(() => {
    getReportList()
      .then(setHistory)
      .catch(() => {})
  }, [])

  // 获取实际日期范围
  const dateRange =
    rangeMode === 'this_week'
      ? thisWeek
      : { start: customStart, end: customEnd }

  // 生成报告
  const handleGenerate = async () => {
    setGenerating(true)
    setGenStage('正在分析本周学习数据...')
    setCurrentReport(null)
    // 阶段切换模拟（后端是单次 API 调用）
    const stageTimer = setTimeout(() => setGenStage('正在 AI 生成报告...'), 2000)
    try {
      const report = await generateReport({
        week_start: dateRange.start,
        week_end: dateRange.end,
      })
      clearTimeout(stageTimer)
      setCurrentReport(report)
      showToast('success', '周报已生成')
      refreshHistory()
    } catch (err: unknown) {
      clearTimeout(stageTimer)
      const msg = err instanceof Error ? err.message : '生成失败，请确认后端服务已启动'
      showToast('error', msg)
    } finally {
      setGenerating(false)
      setGenStage('')
    }
  }

  // 查看历史报告
  const handleViewHistory = async (item: ReportListItem) => {
    if (viewingReportId === item.id) {
      setViewingReportId(null)
      setViewingReport(null)
      return
    }
    setViewingReportId(item.id)
    try {
      const report = await getReport(item.id)
      setViewingReport(report)
    } catch {
      // 如果 API 不可用，从列表数据构造简略展示
      setViewingReport(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* ===== 日期选择 + 生成 ===== */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h1 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary-500" />
          学习周报
        </h1>

        {/* 日期模式 */}
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setRangeMode('this_week')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              rangeMode === 'this_week'
                ? 'bg-primary-50 text-primary-700 border border-primary-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            本周
          </button>
          <button
            onClick={() => setRangeMode('custom')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              rangeMode === 'custom'
                ? 'bg-primary-50 text-primary-700 border border-primary-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            自定义
          </button>
        </div>

        {/* 日期选择 */}
        <div className="flex items-center gap-3 mb-4">
          {rangeMode === 'this_week' ? (
            <div className="flex-1 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-700">
              {formatDateRange(thisWeek.start, thisWeek.end)}（本周）
            </div>
          ) : (
            <>
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-700 outline-none focus:border-primary-400 focus:ring-1 focus:ring-primary-400"
              />
              <span className="text-gray-400 text-sm">~</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-700 outline-none focus:border-primary-400 focus:ring-1 focus:ring-primary-400"
              />
            </>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="shrink-0 flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {genStage || '生成中...'}
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                生成
              </>
            )}
          </button>
        </div>
      </div>

      {/* ===== 当前报告 ===== */}
      {currentReport && <ReportContent report={currentReport} />}

      {/* ===== 历史报告 ===== */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-5 py-3.5 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900">
            历史报告
            {history.length > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                ({history.length})
              </span>
            )}
          </h3>
        </div>

        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileBarChart className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-sm text-gray-500">暂无历史报告</p>
            <p className="text-xs text-gray-400 mt-1">
              选择日期范围后点击"生成"创建你的第一份周报
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {history.map((item) => {
              const isExpanded = viewingReportId === item.id
              return (
                <div key={item.id}>
                  <button
                    onClick={() => handleViewHistory(item)}
                    className={cn(
                      'w-full flex items-center gap-4 px-5 py-3.5 text-left transition-colors',
                      isExpanded ? 'bg-primary-50/40' : 'hover:bg-gray-50'
                    )}
                  >
                    {/* 左侧：日期 + 副信息（标题是真正的视觉主体） */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {formatDateRange(item.week_start, item.week_end)}
                        </p>
                      </div>
                      <p className="text-xs text-gray-500 mt-1 ml-6 truncate">
                        {item.quiz_count > 0
                          ? `${item.quiz_count} 次测评 · ${relativeTime(item.generated_at)}`
                          : relativeTime(item.generated_at)}
                      </p>
                    </div>

                    {/* 中间：分数徽章 —— tone="neutral" 周报场景不用强语义色 */}
                    <ScoreBadge
                      score={item.avg_score}
                      size="md"
                      tone="neutral"
                    />

                    {/* 右侧：展开/收起箭头 */}
                    <ChevronRight
                      className={cn(
                        'w-4 h-4 text-gray-400 shrink-0 transition-transform duration-200',
                        isExpanded && 'rotate-90 text-primary-500'
                      )}
                    />
                  </button>

                  {/* 展开区域：增强视觉分割 + 灰底凸显嵌套关系 */}
                  {isExpanded && viewingReport && (
                    <div className="border-t border-gray-200 bg-gray-50/50 px-5 py-4">
                      <ReportContent report={viewingReport} compact />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
