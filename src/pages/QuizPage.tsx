import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Play,
  Clock,
  ChevronLeft,
  ChevronRight,
  Flag,
  Check,
  X,
  ChevronDown,
  FileText,
  AlertCircle,
  Trash2,
  Loader2,
} from 'lucide-react'
import { ScoreRing } from '@/components/quiz/ScoreRing'
import { showToast } from '@/components/common/Toast'
import {
  getDocuments,
  generateQuiz,
  submitQuiz,
  getQuizResult,
  getQuizHistory,
  deleteQuiz,
  clearQuizHistory,
} from '@/api/client'
import type {
  Document,
  Quiz,
  QuizQuestion,
  QuizResult,
  QuizHistoryItem,
} from '@/types/api'

// ---- 类型 ----

type QuizPhase = 'idle' | 'answering' | 'result'

interface UserAnswer {
  question_id: string
  answer: string
}

// ---- 常量 ----

const QUESTION_COUNTS = [5, 8, 10, 15]

const TYPE_LABELS: Record<string, string> = {
  choice: '选择题',
  true_false: '判断题',
  short_answer: '简答题',
}

// ---- 计时器 Hook ----

function useTimer() {
  const [seconds, setSeconds] = useState(0)
  const [running, setRunning] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval>>()

  const start = useCallback(() => {
    setRunning(true)
  }, [])

  const stop = useCallback(() => {
    setRunning(false)
    if (timerRef.current) clearInterval(timerRef.current)
  }, [])

  const reset = useCallback(() => {
    stop()
    setSeconds(0)
  }, [stop])

  const setElapsed = useCallback((s: number) => {
    setSeconds(s)
  }, [])

  useEffect(() => {
    if (running) {
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [running])

  const format = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
  }

  return { seconds, running, start, stop, reset, setElapsed, format }
}

// ---- 子组件 ----

function PreQuizCard({
  documents,
  selectedDocId,
  onDocChange,
  questionCount,
  onCountChange,
  onStart,
  generating,
}: {
  documents: Document[]
  selectedDocId: string
  onDocChange: (id: string) => void
  questionCount: number
  onCountChange: (n: number) => void
  onStart: () => void
  generating: boolean
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-8 max-w-lg mx-auto">
      <div className="text-center mb-6">
        <div className="w-14 h-14 rounded-2xl bg-primary-50 flex items-center justify-center mx-auto mb-3">
          <FileText className="w-7 h-7 text-primary-500" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">开始测评</h2>
        <p className="text-sm text-gray-500 mt-1">
          选择资料范围与题目数量，系统将自动生成测评题
        </p>
      </div>

      <div className="space-y-4">
        {/* 资料选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            选择资料
          </label>
          <select
            value={selectedDocId}
            onChange={(e) => onDocChange(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-700 outline-none focus:border-primary-400 focus:ring-1 focus:ring-primary-400"
          >
            <option value="">全部资料</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}
              </option>
            ))}
          </select>
        </div>

        {/* 题数选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            题目数量
          </label>
          <div className="grid grid-cols-4 gap-2">
            {QUESTION_COUNTS.map((n) => (
              <button
                key={n}
                onClick={() => onCountChange(n)}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  questionCount === n
                    ? 'border-primary-300 bg-primary-50 text-primary-700'
                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                }`}
              >
                {n} 题
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={onStart}
        disabled={generating}
        className="mt-6 w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 transition-colors"
      >
        <Play className="w-4 h-4" />
        {generating ? '正在生成题目...' : '开始测评'}
      </button>
    </div>
  )
}

function QuestionCard({
  question,
  index,
  total,
  userAnswer,
  onAnswer,
}: {
  question: QuizQuestion
  index: number
  total: number
  userAnswer: string
  onAnswer: (answer: string) => void
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      {/* 题型标签 + 题号 */}
      <div className="flex items-center gap-2 mb-4">
        <span className="inline-block rounded bg-primary-50 text-primary-700 px-2.5 py-0.5 text-xs font-medium">
          {TYPE_LABELS[question.type] || question.type}
        </span>
        <span className="text-xs text-gray-400">
          第 {index + 1} / {total} 题
        </span>
      </div>

      {/* 题目内容 */}
      <p className="text-sm text-gray-900 leading-relaxed mb-5">
        {question.content}
      </p>

      {/* 选择题选项 */}
      {question.type === 'choice' && question.options && (
        <div className="space-y-2">
          {question.options.map((opt) => (
            <button
              key={opt.key}
              onClick={() => onAnswer(opt.key)}
              className={`w-full text-left flex items-center gap-3 rounded-lg border px-4 py-3 text-sm transition-colors ${
                userAnswer === opt.key
                  ? 'border-amber-300 bg-amber-50 text-amber-900'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
              }`}
            >
              <span
                className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${
                  userAnswer === opt.key
                    ? 'bg-amber-200 text-amber-800'
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                {opt.key}
              </span>
              {opt.text}
            </button>
          ))}
        </div>
      )}

      {/* 判断题选项 */}
      {question.type === 'true_false' && (
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: 'true', label: '正确', icon: Check },
            { key: 'false', label: '错误', icon: X },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => onAnswer(key)}
              className={`flex items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors ${
                userAnswer === key
                  ? 'border-amber-300 bg-amber-50 text-amber-900'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon
                className={`w-4 h-4 ${
                  userAnswer === key ? 'text-amber-600' : 'text-gray-400'
                }`}
              />
              {label}
            </button>
          ))}
        </div>
      )}

      {/* 简答题 */}
      {question.type === 'short_answer' && (
        <textarea
          value={userAnswer}
          onChange={(e) => onAnswer(e.target.value)}
          placeholder="请输入你的回答..."
          rows={4}
          className="w-full resize-none rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700 placeholder-gray-400 outline-none focus:border-primary-400 focus:ring-1 focus:ring-primary-400"
        />
      )}
    </div>
  )
}

function QuestionResultCard({
  question,
  detail,
  index,
}: {
  question: QuizQuestion
  detail: QuizResult['details'][number]
  index: number
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xs text-gray-400 shrink-0">#{index + 1}</span>
          <span
            className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
              detail.is_correct
                ? 'bg-green-100 text-green-600'
                : 'bg-red-100 text-red-600'
            }`}
          >
            {detail.is_correct ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <X className="w-3.5 h-3.5" />
            )}
          </span>
          <span className="text-sm text-gray-900 truncate">{question.content}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-gray-400">
            {TYPE_LABELS[question.type]}
          </span>
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 space-y-3 pt-3">
          {/* 正确答案 */}
          <div>
            <span className="text-xs text-gray-400">正确答案</span>
            <p className="text-sm text-green-700 font-medium mt-0.5">
              {detail.correct_answer}
            </p>
          </div>

          {/* 用户答案 */}
          <div>
            <span className="text-xs text-gray-400">你的答案</span>
            <p
              className={`text-sm font-medium mt-0.5 ${
                detail.is_correct ? 'text-green-700' : 'text-red-700'
              }`}
            >
              {detail.user_answer || '未作答'}
            </p>
          </div>

          {/* AI 点评 */}
          {detail.explanation && (
            <div>
              <span className="text-xs text-gray-400">解析</span>
              <p className="text-sm text-gray-600 mt-0.5 leading-relaxed">
                {detail.explanation}
              </p>
            </div>
          )}

          {/* 来源 */}
          {detail.source_document && (
            <p className="text-xs text-gray-400">
              来源：《{detail.source_document}》第{detail.source_page}页
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ---- 确认弹窗（用于删除单条/清空全部） ----

interface ConfirmConfig {
  title: string
  description: React.ReactNode
  confirmText?: string
  onConfirm: () => void
}

function ConfirmDialog({
  open,
  config,
  onCancel,
}: {
  open: boolean
  config: ConfirmConfig | null
  onCancel: () => void
}) {
  if (!open || !config) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-in fade-in duration-150"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-5 animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-base font-semibold text-gray-900 mb-2">
          {config.title}
        </h3>
        <div className="text-sm text-gray-600 mb-4 leading-relaxed">
          {config.description}
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={() => {
              config.onConfirm()
              onCancel()
            }}
            className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
          >
            {config.confirmText || '确认删除'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- 历史测评列表（可复用，含删除/清空全部） ----

function HistoryList({
  history,
  currentQuizId,
  onDeleteOne,
  onClearAll,
  emptyHint,
}: {
  history: QuizHistoryItem[]
  /** 当前正在进行的 quiz_id（禁止删除自身） */
  currentQuizId?: string
  onDeleteOne: (item: QuizHistoryItem) => void
  onClearAll: () => void
  emptyHint?: string
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">
          历史测评
          {history.length > 0 && (
            <span className="ml-2 text-xs font-normal text-gray-400">
              ({history.length})
            </span>
          )}
        </h3>
        {history.length > 0 && (
          <button
            onClick={onClearAll}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-600 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            清空全部
          </button>
        )}
      </div>
      {history.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-gray-400">
          {emptyHint || '暂无历史记录'}
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {history.map((item) => {
            const isCurrent = item.quiz_id === currentQuizId
            return (
              <div
                key={item.quiz_id}
                className="flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors group"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-900 truncate max-w-[280px]">
                    {item.title}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {item.question_count} 题 ·{' '}
                    {new Date(item.created_at).toLocaleDateString('zh-CN')}
                    {item.status !== 'submitted' && (
                      <span className="ml-2 text-amber-600">未完成</span>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {item.status === 'submitted' && item.score !== undefined ? (
                    <>
                      <span
                        className={`text-sm font-semibold ${
                          item.score >= 80
                            ? 'text-green-600'
                            : item.score >= 60
                              ? 'text-amber-600'
                              : 'text-red-600'
                        }`}
                      >
                        {item.score} 分
                      </span>
                      <span className="text-xs text-gray-400">
                        {Math.round(item.accuracy! * 100)}%
                      </span>
                    </>
                  ) : (
                    <span className="text-xs text-gray-400">未完成</span>
                  )}
                  <button
                    onClick={() => onDeleteOne(item)}
                    disabled={isCurrent}
                    title={isCurrent ? '当前测评不可删除' : '删除该记录'}
                    className="p-1 text-gray-300 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---- 主页面 ----

const QUIZ_STATE_KEY = 'ai_study_quiz_state'

interface QuizState {
  phase: QuizPhase
  quiz: Quiz | null
  currentIndex: number
  userAnswers: UserAnswer[]
  elapsedSeconds: number
  result: QuizResult | null
}

function loadQuizState(): QuizState | null {
  try {
    const raw = localStorage.getItem(QUIZ_STATE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as QuizState
  } catch {
    return null
  }
}

function saveQuizState(state: QuizState) {
  try {
    localStorage.setItem(QUIZ_STATE_KEY, JSON.stringify(state))
  } catch { /* quota exceeded, ignore */ }
}

function clearQuizState() {
  localStorage.removeItem(QUIZ_STATE_KEY)
}

export function QuizPage() {
  const [phase, setPhase] = useState<QuizPhase>('idle')

  // 开始前状态
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocId, setSelectedDocId] = useState('')
  const [questionCount, setQuestionCount] = useState(10)
  const [generating, setGenerating] = useState(false)

  // 答题状态
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [userAnswers, setUserAnswers] = useState<UserAnswer[]>([])
  const [submitting, setSubmitting] = useState(false)
  const timer = useTimer()

  // 结果状态
  const [result, setResult] = useState<QuizResult | null>(null)
  const [history, setHistory] = useState<QuizHistoryItem[]>([])

  // 结果展开状态
  const [showResultDetail, setShowResultDetail] = useState(false)
  const [restored, setRestored] = useState(false)

  // 删除/清空相关
  const [confirmConfig, setConfirmConfig] = useState<ConfirmConfig | null>(null)
  const [deleting, setDeleting] = useState(false)

  // ---- 页面恢复：从 localStorage 恢复答题状态 ----
  useEffect(() => {
    const saved = loadQuizState()
    if (!saved || !saved.quiz) {
      setRestored(true)
      return
    }

    // 验证保存的 session 有效（quiz_id 不为空且有题目）
    if (!saved.quiz.questions || saved.quiz.questions.length === 0) {
      clearQuizState()
      setRestored(true)
      return
    }

    setPhase(saved.phase)
    setQuiz(saved.quiz)
    setCurrentIndex(saved.currentIndex)
    setUserAnswers(saved.userAnswers)
    setResult(saved.result)

    // 恢复计时器
    if (saved.elapsedSeconds > 0) {
      timer.setElapsed(saved.elapsedSeconds)
      if (saved.phase === 'answering') {
        timer.start()
      }
    }

    setRestored(true)
  }, [])

  // ---- 同步状态到 localStorage ----
  useEffect(() => {
    if (!restored) return  // 还没恢复完，不覆盖
    if (phase === 'idle') {
      clearQuizState()
      return
    }

    saveQuizState({
      phase,
      quiz,
      currentIndex,
      userAnswers,
      elapsedSeconds: timer.seconds,
      result,
    })
  }, [phase, quiz, currentIndex, userAnswers, timer.seconds, result, restored])

  // ---- 页面卸载时保存 ----
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (phase !== 'idle' && quiz) {
        saveQuizState({
          phase,
          quiz,
          currentIndex,
          userAnswers,
          elapsedSeconds: timer.seconds,
          result,
        })
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [phase, quiz, currentIndex, userAnswers, timer.seconds, result])

  // 加载资料列表
  useEffect(() => {
    getDocuments({ page_size: 100 })
      .then((d) => setDocuments(d.items.filter((doc) => doc.status === 'ready')))
      .catch(() => {})
  }, [])

  // 加载历史（idle 和 result 阶段都需要）
  const reloadHistory = useCallback(() => {
    getQuizHistory({ page_size: 50 })
      .then((d) => setHistory(d.items))
      .catch(() => {})
  }, [])

  useEffect(() => {
    // idle 或 result 阶段都加载历史
    if (phase === 'idle' || phase === 'result') {
      reloadHistory()
    }
  }, [phase, reloadHistory])

  // ---- 删除单条 ----
  const handleDeleteOne = useCallback((item: QuizHistoryItem) => {
    const scoreText = item.status === 'submitted' && item.score !== undefined
      ? ` · 得分 ${item.score} 分`
      : ''
    setConfirmConfig({
      title: '确认删除该测评记录？',
      description: (
        <div className="space-y-2">
          <div>
            <span className="text-gray-400">标题：</span>
            <span className="text-gray-900 font-medium">{item.title}</span>
          </div>
          <div>
            <span className="text-gray-400">信息：</span>
            <span className="text-gray-900">
              {item.question_count} 题 · {new Date(item.created_at).toLocaleDateString('zh-CN')}
              {scoreText}
            </span>
          </div>
          <div className="text-xs text-gray-500 pt-2 border-t border-gray-100">
            删除后将同时清除：题目内容、答题记录
            {item.status === 'submitted' && '、相关知识点统计（会回退）'}
            。此操作不可撤销。
          </div>
        </div>
      ),
      onConfirm: async () => {
        setDeleting(true)
        try {
          await deleteQuiz(item.quiz_id)
          showToast('success', '已删除')
          // 如果删除的是当前 result 对应的 quiz，回到 idle
          if (phase === 'result' && quiz?.quiz_id === item.quiz_id) {
            clearQuizState()
            timer.reset()
            setQuiz(null)
            setResult(null)
            setPhase('idle')
          } else {
            reloadHistory()
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : '删除失败'
          showToast('error', msg)
        } finally {
          setDeleting(false)
        }
      },
    })
  }, [phase, quiz, timer, reloadHistory])

  // ---- 清空全部 ----
  const handleClearAll = useCallback(() => {
    if (history.length === 0) return
    setConfirmConfig({
      title: '确认清空全部测评记录？',
      description: (
        <div className="space-y-2">
          <div>
            即将删除 <span className="text-red-600 font-medium">{history.length}</span> 条测评记录，
            包括所有题目内容、答题记录和已提交测评对应的知识点统计回退。
          </div>
          <div className="text-xs text-gray-500 pt-2 border-t border-gray-100">
            此操作不可撤销，请谨慎确认。
          </div>
        </div>
      ),
      confirmText: '确认清空',
      onConfirm: async () => {
        setDeleting(true)
        try {
          const r = await clearQuizHistory()
          showToast('success', `已清空 ${r.deleted_count} 条记录`)
          // 如果当前在 result 阶段，回到 idle
          if (phase === 'result') {
            clearQuizState()
            timer.reset()
            setQuiz(null)
            setResult(null)
            setPhase('idle')
          } else {
            reloadHistory()
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : '清空失败'
          showToast('error', msg)
        } finally {
          setDeleting(false)
        }
      },
    })
  }, [history.length, phase, timer, reloadHistory])

  // ---- 开始测评 ----
  const handleStart = async () => {
    setGenerating(true)
    try {
      const q = await generateQuiz({
        question_count: questionCount,
        document_ids: selectedDocId ? [selectedDocId] : undefined,
        question_types: ['choice', 'true_false', 'short_answer'],
      })

      if (!q.questions || q.questions.length === 0) {
        showToast('error', '未能生成题目，请确保已上传资料并完成解析')
        setGenerating(false)
        return
      }

      // 初始化答案数组（清空题目中的 correct_answer 和 explanation —— 前端防护）
      const sanitizedQuestions = q.questions.map((q) => ({
        ...q,
        correct_answer: undefined,
        explanation: undefined,
      }))

      setQuiz({ ...q, questions: sanitizedQuestions })
      setUserAnswers(
        sanitizedQuestions.map((q) => ({
          question_id: q.question_id,
          answer: '',
        })),
      )
      setCurrentIndex(0)
      setResult(null)
      setGenerating(false)
      timer.reset()
      timer.start()
      setPhase('answering')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '生成失败'
      showToast('error', msg)
      setGenerating(false)
    }
  }

  // ---- 答题交互 ----
  const handleAnswer = (answer: string) => {
    if (!quiz) return
    setUserAnswers((prev) =>
      prev.map((a, i) =>
        i === currentIndex ? { ...a, answer } : a,
      ),
    )
  }

  const goToQuestion = (index: number) => {
    if (index >= 0 && quiz && index < quiz.questions.length) {
      setCurrentIndex(index)
    }
  }

  // ---- 提交测评 ----
  const handleSubmit = async () => {
    if (!quiz) return
    const unanswered = userAnswers.filter((a) => !a.answer).length
    if (unanswered > 0) {
      const confirmed = window.confirm(
        `还有 ${unanswered} 道题未作答，确定提交吗？`,
      )
      if (!confirmed) return
    }

    setSubmitting(true)
    timer.stop()

    try {
      const r = await submitQuiz(quiz.quiz_id, { answers: userAnswers })
      setResult(r)
      clearQuizState()
      setPhase('result')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '提交失败'
      showToast('error', msg)
    } finally {
      setSubmitting(false)
    }
  }

  // ---- 放弃测评 ----
  const handleAbandon = () => {
    const confirmed = window.confirm('确定放弃本次测评吗？已作答内容将不会保存。')
    if (confirmed) {
      clearQuizState()
      timer.reset()
      setQuiz(null)
      setResult(null)
      setPhase('idle')
    }
  }

  // ---- 重新开始 ----
  const handleRestart = () => {
    clearQuizState()
    timer.reset()
    setQuiz(null)
    setResult(null)
    setPhase('idle')
  }

  // ---- 获取成绩等级 ----
  const getGradeLabel = (score: number) => {
    if (score >= 90) return '优秀'
    if (score >= 80) return '良好'
    if (score >= 60) return '及格'
    return '需加强'
  }

  const currentQuestion = quiz?.questions[currentIndex]

  // ============================================
  // RENDER: 开始前
  // ============================================
  if (phase === 'idle') {
    return (
      <>
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 animate-page-in space-y-6">
          <PreQuizCard
            documents={documents}
            selectedDocId={selectedDocId}
            onDocChange={setSelectedDocId}
            questionCount={questionCount}
            onCountChange={setQuestionCount}
            onStart={handleStart}
            generating={generating}
          />
          <HistoryList
            history={history}
            onDeleteOne={handleDeleteOne}
            onClearAll={handleClearAll}
            emptyHint="完成测评后，历史记录会显示在这里"
          />
        </div>
        <ConfirmDialog
          open={confirmConfig !== null}
          config={confirmConfig}
          onCancel={() => setConfirmConfig(null)}
        />
        {deleting && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 pointer-events-none">
            <div className="bg-white rounded-lg px-4 py-3 flex items-center gap-2 shadow-lg">
              <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
              <span className="text-sm text-gray-700">处理中…</span>
            </div>
          </div>
        )}
      </>
    )
  }

  // ============================================
  // RENDER: 答题中
  // ============================================
  if (phase === 'answering' && quiz && currentQuestion) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        {/* 顶部进度条 */}
        <div className="bg-white border border-gray-200 rounded-lg px-5 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              第 {currentIndex + 1} / {quiz.questions.length} 题
            </span>
            <div className="flex items-center gap-1.5 text-sm text-gray-500">
              <Clock className="w-4 h-4" />
              {timer.format(timer.seconds)}
            </div>
          </div>
          {/* 进度条 */}
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 rounded-full transition-all duration-300"
              style={{
                width: `${((currentIndex + 1) / quiz.questions.length) * 100}%`,
              }}
            />
          </div>
          {/* 题号导航 */}
          <div className="flex flex-wrap gap-1.5 mt-3">
            {quiz.questions.map((_, i) => (
              <button
                key={i}
                onClick={() => goToQuestion(i)}
                className={`w-8 h-8 rounded-md text-xs font-medium transition-colors ${
                  i === currentIndex
                    ? 'bg-primary-600 text-white'
                    : userAnswers[i]?.answer
                      ? 'bg-primary-50 text-primary-700 border border-primary-200'
                      : 'bg-gray-50 text-gray-400 border border-gray-200 hover:border-gray-300'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>

        {/* 题目卡片 */}
        <QuestionCard
          question={currentQuestion}
          index={currentIndex}
          total={quiz.questions.length}
          userAnswer={userAnswers[currentIndex]?.answer || ''}
          onAnswer={handleAnswer}
        />

        {/* 导航按钮 */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => goToQuestion(currentIndex - 1)}
            disabled={currentIndex === 0}
            className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            上一题
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleAbandon}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-500 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <Flag className="w-4 h-4" />
              放弃
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? '提交中...' : '提交'}
            </button>
          </div>

          <button
            onClick={() => goToQuestion(currentIndex + 1)}
            disabled={currentIndex === quiz.questions.length - 1}
            className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            下一题
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  // ============================================
  // RENDER: 结果页
  // ============================================
  if (phase === 'result' && result && quiz) {
    const correctCount = result.correct_count
    const wrongCount = result.total_count - result.correct_count

    return (
      <>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* 分数圆环 + 统计 */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex flex-col items-center">
            <ScoreRing
              score={result.total_score}
              label={`${result.total_score}分`}
              sublabel={getGradeLabel(result.total_score)}
              size={180}
            />
            <div className="grid grid-cols-3 gap-4 sm:gap-6 mt-6 w-full max-w-md">
              <div className="text-center">
                <p className="text-2xl font-semibold text-green-600">
                  {correctCount}
                </p>
                <p className="text-xs text-gray-500">答对</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold text-red-500">
                  {wrongCount}
                </p>
                <p className="text-xs text-gray-500">答错</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold text-gray-700">
                  {timer.format(timer.seconds)}
                </p>
                <p className="text-xs text-gray-500">总用时</p>
              </div>
            </div>

            <button
              onClick={handleRestart}
              className="mt-6 flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              <Play className="w-4 h-4" />
              再来一次
            </button>
          </div>
        </div>

        {/* 逐题详情（折叠） */}
        <div className="bg-white border border-gray-200 rounded-lg">
          <button
            onClick={() => setShowResultDetail(!showResultDetail)}
            className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors rounded-lg"
          >
            <span className="text-sm font-semibold text-gray-900">
              答题详情
            </span>
            {showResultDetail ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {showResultDetail && (
            <div className="px-5 pb-4 space-y-2">
              {quiz.questions.map((q, i) => {
                const detail = result.details.find(
                  (d) => d.question_id === q.question_id,
                )
                if (!detail) return null
                return (
                  <QuestionResultCard
                    key={q.question_id}
                    question={q}
                    detail={detail}
                    index={i}
                  />
                )
              })}
            </div>
          )}
        </div>

        {/* 薄弱知识点 */}
        {result.weak_points && result.weak_points.length > 0 && (
          <div className="bg-white border border-red-200 rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm font-semibold text-gray-900">
                薄弱知识点
              </span>
            </div>
            <div className="space-y-2">
              {result.weak_points.map((wp, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between border border-red-100 bg-red-50/30 rounded-lg px-4 py-2.5"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {wp.knowledge_point}
                    </p>
                    <p className="text-xs text-gray-500">{wp.document}</p>
                  </div>
                  <span className="text-xs text-red-600 font-medium">
                    错 {wp.error_count} 题
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 历史测评记录（含删除/清空全部） */}
        <HistoryList
          history={history}
          currentQuizId={quiz?.quiz_id}
          onDeleteOne={handleDeleteOne}
          onClearAll={handleClearAll}
        />
      </div>
      <ConfirmDialog
        open={confirmConfig !== null}
        config={confirmConfig}
        onCancel={() => setConfirmConfig(null)}
      />
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 pointer-events-none">
          <div className="bg-white rounded-lg px-4 py-3 flex items-center gap-2 shadow-lg">
            <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
            <span className="text-sm text-gray-700">处理中…</span>
          </div>
        </div>
      )}
    </>
  )
  }

  // 兜底
  return null
}
