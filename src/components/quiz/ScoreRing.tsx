import { useEffect, useState } from 'react'

interface ScoreRingProps {
  score: number       // 0–100
  size?: number       // 圆环直径
  strokeWidth?: number
  label?: string      // 中间文字（如 "85分"）
  sublabel?: string   // 中间小字（如 "良好"）
}

export function ScoreRing({
  score,
  size = 160,
  strokeWidth = 10,
  label,
  sublabel,
}: ScoreRingProps) {
  const [animatedScore, setAnimatedScore] = useState(0)
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (animatedScore / 100) * circumference

  // 入场动画
  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 100)
    return () => clearTimeout(timer)
  }, [score])

  // 颜色
  const getColor = () => {
    if (score >= 80) return '#16a34a'   // green-600
    if (score >= 60) return '#d97706'   // amber-600
    return '#dc2626'                     // red-600
  }

  const color = getColor()

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* 背景圆环 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#f3f4f6"
          strokeWidth={strokeWidth}
        />
        {/* 进度圆环 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.2s ease-out' }}
        />
      </svg>

      {/* 中间文字 */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-gray-900">
          {label || `${score}分`}
        </span>
        {sublabel && (
          <span className="text-xs text-gray-500 mt-0.5">{sublabel}</span>
        )}
      </div>
    </div>
  )
}
