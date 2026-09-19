interface Props {
  data: number[]
  color: string
  /** 外部统一纵轴上界；多条曲线叠加时用它保证可比性 */
  max?: number
  viewWidth?: number
  viewHeight?: number
}

/**
 * 极简面积折线图。
 * 刻意不加坐标轴与网格线——监控面板需要的是趋势形状，不是图表装饰。
 */
export default function SparkLine({
  data,
  color,
  max,
  viewWidth = 300,
  viewHeight = 60,
}: Props) {
  if (!data.length) {
    return <svg className="oc-spark" viewBox={`0 0 ${viewWidth} ${viewHeight}`} />
  }

  const upper = Math.max(max ?? Math.max(...data), 1)
  const coords = data.map((value, index) => {
    const x = (index / Math.max(data.length - 1, 1)) * viewWidth
    const y = viewHeight - (Math.min(value, upper) / upper) * (viewHeight - 4) - 2
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  const areaPoints = `0,${viewHeight} ${coords.join(' ')} ${viewWidth},${viewHeight}`
  const gradientId = `spark-${color.replace(/[^a-zA-Z0-9]/g, '')}`

  return (
    <svg
      className="oc-spark"
      viewBox={`0 0 ${viewWidth} ${viewHeight}`}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#${gradientId})`} />
      <polyline
        points={coords.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.2"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
