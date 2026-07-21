import { cn } from '@/lib/utils'

interface LogoProps {
  /** 尺寸类，默认 w-6 h-6 (24px)。可传任意 Tailwind 尺寸类如 "w-8 h-8" */
  className?: string
  /** 是否显示浅蓝背景圆角块。导航栏建议 true（有视觉锚点），深色背景或需无框场景传 false */
  withBackground?: boolean
  /** 标题（用于无障碍），默认"大模型学习助手" */
  title?: string
}

/**
 * 产品 Logo —— 「神经网络节点」方案。
 *
 * 设计：3 层节点拓扑（2→3→1），象征输入→隐层→输出的神经网络结构，
 * 直接呼应「大模型学习助手」的 AI 主题。
 *
 * 主色 #2563eb (primary-600) 与项目品牌色绑定。
 * 全部为矢量 SVG，零图片依赖，任意尺寸清晰。
 *
 * @example
 * <Logo />                              // 默认 24px，带浅蓝背景
 * <Logo className="w-8 h-8" />          // 32px
 * <Logo withBackground={false} />       // 无背景（适配深色背景）
 */
export function Logo({
  className,
  withBackground = true,
  title = '大模型学习助手',
}: LogoProps) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      role="img"
      aria-label={title}
      className={cn('shrink-0', className)}
    >
      <title>{title}</title>

      {withBackground && (
        <rect width="64" height="64" rx="14" fill="#eff6ff" />
      )}

      {/* 连线层：神经网络拓扑 2→3→1 */}
      <g
        stroke="#2563eb"
        strokeWidth="1.8"
        opacity="0.45"
        fill="none"
        strokeLinecap="round"
      >
        {/* 输入层 → 隐层 */}
        <line x1="14" y1="20" x2="32" y2="14" />
        <line x1="14" y1="20" x2="32" y2="32" />
        <line x1="14" y1="20" x2="32" y2="50" />
        <line x1="14" y1="44" x2="32" y2="14" />
        <line x1="14" y1="44" x2="32" y2="32" />
        <line x1="14" y1="44" x2="32" y2="50" />
        {/* 隐层 → 输出层 */}
        <line x1="32" y1="14" x2="50" y2="32" />
        <line x1="32" y1="32" x2="50" y2="32" />
        <line x1="32" y1="50" x2="50" y2="32" />
      </g>

      {/* 节点层 */}
      <g fill="#2563eb">
        {/* 输入层 2 个 */}
        <circle cx="14" cy="20" r="3.5" />
        <circle cx="14" cy="44" r="3.5" />
        {/* 隐层 3 个 */}
        <circle cx="32" cy="14" r="3.5" />
        <circle cx="32" cy="32" r="3.5" />
        <circle cx="32" cy="50" r="3.5" />
        {/* 输出层 1 个（稍大，强调输出/答案） */}
        <circle cx="50" cy="32" r="5" />
      </g>
    </svg>
  )
}
