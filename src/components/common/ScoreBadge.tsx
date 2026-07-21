import { cn } from '@/lib/utils'

// ---- 尺寸 ----
const sizeMap = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
} as const

// ---- 语义色调 ----
// 注意：分数 < 60 在"单次测评"场景下用红色合理（鼓励重试），
// 但在"周报平均分"等汇总场景下用红色反人类。
// 通过 tone="neutral" 可关闭强语义色，统一用灰色徽章。
const toneMap = {
  good: 'bg-green-50 text-green-700 ring-green-200',
  warn: 'bg-amber-50 text-amber-700 ring-amber-200',
  low: 'bg-red-50 text-red-700 ring-red-200',
  neutral: 'bg-gray-100 text-gray-700 ring-gray-200',
} as const

type Tone = keyof typeof toneMap

function getToneByScore(score: number): Tone {
  if (score >= 80) return 'good'
  if (score >= 60) return 'warn'
  return 'low'
}

interface ScoreBadgeProps {
  score: number
  size?: keyof typeof sizeMap
  /** 强制指定色调；不传则按分数自动判断 */
  tone?: Tone
  /** 是否显示"分"字单位（默认 true） */
  showUnit?: boolean
  className?: string
}

/**
 * 分数徽章 —— 用于列表项、卡片等紧凑场景的分数标识。
 *
 * 与 `ScoreRing` 的区别：
 * - `ScoreRing` 是大尺寸（≥100px）的主视觉组件，字号硬编码 text-3xl，不适合小场景
 * - `ScoreBadge` 是徽章式标识，字号小、视觉克制，可在列表/卡片里安全使用
 *
 * @example
 * <ScoreBadge score={58.3} />                      // 自动按分数着色
 * <ScoreBadge score={58.3} tone="neutral" />       // 周报场景：不用强语义色
 * <ScoreBadge score={92} size="md" showUnit={false} />
 */
export function ScoreBadge({
  score,
  size = 'sm',
  tone,
  showUnit = true,
  className,
}: ScoreBadgeProps) {
  const finalTone = tone ?? getToneByScore(score)
  return (
    <span
      className={cn(
        'inline-flex items-baseline rounded-md font-semibold ring-1 ring-inset shrink-0 tabular-nums leading-none',
        sizeMap[size],
        toneMap[finalTone],
        className
      )}
    >
      <span>{score}</span>
      {showUnit && (
        <span className="ml-0.5 font-normal opacity-70">分</span>
      )}
    </span>
  )
}
