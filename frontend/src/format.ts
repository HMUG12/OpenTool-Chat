/** 字节单位换算与格式化。所有对外展示的数值都在这里统一口径。 */

const UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

export function formatBytes(bytes: number, digits = 1): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '-'
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(value >= 100 || unit === 0 ? 0 : digits)} ${UNITS[unit]}`
}

/** 速率输入单位为 字节/秒 */
export function formatRate(bytesPerSecond: number): { value: string; unit: string } {
  if (!Number.isFinite(bytesPerSecond) || bytesPerSecond < 0) {
    return { value: '-', unit: '' }
  }
  const bits = bytesPerSecond * 8
  if (bits >= 1_000_000_000) return { value: (bits / 1_000_000_000).toFixed(2), unit: 'Gbps' }
  if (bits >= 1_000_000) return { value: (bits / 1_000_000).toFixed(2), unit: 'Mbps' }
  if (bits >= 1_000) return { value: (bits / 1_000).toFixed(1), unit: 'Kbps' }
  return { value: bits.toFixed(0), unit: 'bps' }
}

export function formatUptime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '-'
  const total = Math.floor(seconds)
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60

  const parts: string[] = []
  if (days) parts.push(`${days} 天`)
  if (hours) parts.push(`${hours} 小时`)
  if (minutes && parts.length < 2) parts.push(`${minutes} 分钟`)
  if (!parts.length) parts.push(`${rest} 秒`)
  return parts.join(' ')
}

export function formatFrequency(mhz: number | null | undefined): string {
  if (!mhz) return '-'
  return mhz >= 1000 ? `${(mhz / 1000).toFixed(2)} GHz` : `${mhz.toFixed(0)} MHz`
}

export function formatDateTime(timestampSeconds: number): string {
  if (!timestampSeconds) return '-'
  return new Date(timestampSeconds * 1000).toLocaleString('zh-CN', { hour12: false })
}

/** 根据百分比返回语义级别，用于用量条配色 */
export function usageLevel(percent: number): '' | 'warn' | 'crit' {
  if (percent >= 90) return 'crit'
  if (percent >= 75) return 'warn'
  return ''
}
