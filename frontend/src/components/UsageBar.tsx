import { usageLevel } from '../format'

interface Props {
  label: string
  percent: number
  value: string
  sub?: string
}

export default function UsageBar({ label, percent, value, sub }: Props) {
  const safe = Math.min(100, Math.max(0, percent))
  return (
    <div className="oc-usage">
      <div className="oc-usage-head">
        <span className="oc-usage-label">{label}</span>
        <span className="oc-usage-value">{value}</span>
      </div>
      <div className="oc-usage-track">
        <div className={`oc-usage-fill ${usageLevel(safe)}`} style={{ width: `${safe}%` }} />
      </div>
      {sub && <div className="oc-usage-sub">{sub}</div>}
    </div>
  )
}
