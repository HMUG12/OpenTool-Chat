export type ToolKind = 'builtin' | 'external' | 'plugin'

/** 一个工具的完整描述。这是整个应用的心脏数据结构。 */
export interface ToolSpec {
  id: string
  name: string
  description: string
  category: string
  icon: string
  version: string
  author: string
  kind: ToolKind
  /** 相对工具目录的可执行入口 */
  entry: string
  args: string[]
  /** 是否需要管理员权限运行 */
  admin: boolean
  /** 依赖是否满足（缺少运行时依赖时置灰） */
  available: boolean
  /** 不可用原因 */
  reason?: string
  /** 未检测到时的官方下载地址（点击前往下载） */
  download?: string
  tags: string[]
}

export interface AppInfo {
  name: string
  version: string
  author: string
  description: string
  portable: boolean
  rootDir: string
  toolDir: string
  pythonVersion: string
  platform: string
}

export interface LaunchResult {
  ok: boolean
  message: string
}

export type ThemeMode = 'light' | 'dark' | 'system'

// ══════════════════════════════════════════════════════════════
// 系统监测
// ══════════════════════════════════════════════════════════════

export interface DiskInfo {
  device: string
  mountpoint: string
  fstype: string
  total: number
  used: number
  free: number
  percent: number
}

export interface GpuInfo {
  name?: string
  memoryGB?: number
  driverVersion?: string
  resolution?: string
}

export interface BoardInfo {
  manufacturer?: string
  product?: string
}

export interface HardwareInfo {
  cpu: {
    name: string
    cores: number | null
    threads: number | null
    freqMax: number | null
    freqCurrent: number | null
    arch: string
  }
  memory: { total: number; percent: number; totalGB: number }
  swap: { total: number; used: number; percent: number }
  disks: DiskInfo[]
  gpus: GpuInfo[]
  boards: BoardInfo[]
  os: {
    system: string
    release: string
    version: string
    build: string
    hostname: string
  }
  bootTime: number
}

export interface MetricsHistoryPoint {
  t: number
  cpu: number
  memory: number
  download: number
  upload: number
}

export interface Metrics {
  timestamp: number
  cpu: {
    percent: number
    perCore: number[]
    freqCurrent: number | null
    loadAvg: number[] | null
  }
  memory: { percent: number; used: number; total: number; available: number }
  network: { download: number; upload: number; totalRecv: number; totalSent: number }
  disk: { read: number; write: number }
  history: MetricsHistoryPoint[]
}

export interface NetworkInterface {
  name: string
  ipv4: { address: string; netmask: string }[]
  ipv6: string[]
  mac: string | null
  up: boolean
  speedMbps: number
  mtu: number
  bytesSent: number
  bytesRecv: number
}

export interface NetworkInfo {
  interfaces: NetworkInterface[]
  topology: {
    gateways: string[]
    dnsServers: string[]
    dhcpEnabled: boolean | null
  }
}

export interface IpInfo {
  hostname: string
  local: string | null
  loopback: string
  public: PublicIpResult
}

export interface PublicIpResult {
  ip: string | null
  source: string | null
  reachable: boolean
  queried?: boolean
}
