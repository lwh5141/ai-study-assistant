import { SmartTooltip } from '@/components/common/SmartTooltip'

interface RadarDataPoint {
  label: string
  value: number // 0–1
}

interface RadarChartProps {
  data: RadarDataPoint[]
  size?: number
}

export function RadarChart({ data, size = 280 }: RadarChartProps) {
  if (data.length < 3) {
    return (
      <div className="flex items-center justify-center text-sm text-gray-400" style={{ width: size, height: size }}>
        数据不足（至少需要 3 个维度）
      </div>
    )
  }

  const cx = size / 2
  const cy = size / 2
  const radius = size * 0.36
  const levels = 4 // 4 层刻度（25%/50%/75%/100%）

  // 计算多边形顶点坐标
  const getPoint = (index: number, value: number) => {
    const angle = (Math.PI * 2 * index) / data.length - Math.PI / 2
    const r = radius * value
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    }
  }

  // 背景网格
  const gridPolygons = Array.from({ length: levels }, (_, level) => {
    const points = data
      .map((_, i) => {
        const p = getPoint(i, (level + 1) / levels)
        return `${p.x},${p.y}`
      })
      .join(' ')
    return (
      <polygon
        key={level}
        points={points}
        fill="none"
        stroke="#e5e7eb"
        strokeWidth="1"
      />
    )
  })

  // 轴线
  const axisLines = data.map((_, i) => {
    const p = getPoint(i, 1)
    return (
      <line
        key={i}
        x1={cx}
        y1={cy}
        x2={p.x}
        y2={p.y}
        stroke="#e5e7eb"
        strokeWidth="1"
      />
    )
  })

  // 数据多边形
  const dataPoints = data
    .map((d, i) => {
      const p = getPoint(i, d.value)
      return `${p.x},${p.y}`
    })
    .join(' ')

  // 数据点
  const dataDots = data.map((d, i) => {
    const p = getPoint(i, d.value)
    return <circle key={i} cx={p.x} cy={p.y} r="4" fill="#2563eb" />
  })

  // 标签（每个标签外包一个透明矩形作为 hover 命中区，用 SmartTooltip 显示完整名称）
  const truncated = (s: string) => (s.length > 6 ? s.slice(0, 6) + '...' : s)

  const labels = data.map((d, i) => {
    const p = getPoint(i, 1.15)
    const angle = (Math.PI * 2 * i) / data.length - Math.PI / 2
    let textAnchor: 'start' | 'middle' | 'end' = 'middle'
    let dx = 0

    // 根据角度调整文字位置避免压线
    if (Math.abs(Math.cos(angle)) > 0.85) {
      textAnchor = Math.cos(angle) > 0 ? 'start' : 'end'
      dx = Math.cos(angle) > 0 ? 6 : -6
    }

    // 命中矩形：以标签为中心，扩大到至少 60×20
    const hitW = 60
    const hitH = 20
    const hitX =
      textAnchor === 'start' ? p.x + dx - 4 :
      textAnchor === 'end'   ? p.x + dx - hitW + 4 :
      p.x + dx - hitW / 2
    const hitY = p.y - hitH / 2

    // 是否被截断（决定是否启用 tooltip）
    const isTruncated = d.label.length > 6
    const labelText = truncated(d.label)
    const pct = Math.round(d.value * 100)

    return (
      <g key={i}>
        <SmartTooltip
          content={
            <div>
              <div className="font-medium text-white">{d.label}</div>
              <div className="text-gray-300 mt-0.5">掌握度 {pct}%</div>
            </div>
          }
          delay={isTruncated ? 300 : 600}
        >
          {/* 透明命中矩形，扩大 hover 区域；cursor-default 避免被当作可点击 */}
          <rect
            x={hitX}
            y={hitY}
            width={hitW}
            height={hitH}
            fill="transparent"
            style={{ cursor: 'default' }}
          />
        </SmartTooltip>
        <text
          x={p.x + dx}
          y={p.y + 4}
          textAnchor={textAnchor}
          className="fill-gray-600"
          fontSize="11"
          fontFamily="system-ui, sans-serif"
          style={{ pointerEvents: 'none' }}
        >
          {labelText}
        </text>
      </g>
    )
  })

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      className="overflow-visible"
    >
      {/* 网格 */}
      {gridPolygons}
      {/* 轴线 */}
      {axisLines}
      {/* 数据区域 */}
      <polygon
        points={dataPoints}
        fill="rgba(37, 99, 235, 0.12)"
        stroke="#2563eb"
        strokeWidth="2"
      />
      {/* 数据点 */}
      {dataDots}
      {/* 标签 + tooltip 命中区 */}
      {labels}
    </svg>
  )
}
