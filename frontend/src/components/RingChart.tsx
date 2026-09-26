import type { ReactNode } from 'react'

interface Props {
  /** 0-100 */
  percent: number
  size?: number
  stroke?: number
  color?: string
  /** 环内主数值（默认显示百分数） */
  value?: ReactNode
  /** 环内小标题 */
  label?: string
  /** 环内补充说明 */
  sub?: string
}

/**
 * 圆环进度图（纯 SVG，无第三方依赖）。
 * 用于 CPU / 内存 / 磁盘等占用率的动态可视化，数值变化时带过渡动画。
 */
export default function RingChart({
  percent,
  size = 132,
  stroke = 11,
  color = 'var(--oc-accent)',
  value,
  label,
  sub,
}: Props) {
  const safe = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - safe / 100)

  return (
    <div className="oc-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--oc-ring-track)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset .7s cubic-bezier(.22,.61,.36,1)' }}
        />
      </svg>
      <div className="oc-ring-center">
        <div className="oc-ring-value">{value ?? `${safe.toFixed(0)}%`}</div>
        {label && <div className="oc-ring-label">{label}</div>}
        {sub && <div className="oc-ring-sub">{sub}</div>}
      </div>
    </div>
  )
}
