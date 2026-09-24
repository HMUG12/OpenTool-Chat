import type {
  AppInfo,
  HardwareInfo,
  IpInfo,
  LaunchResult,
  Metrics,
  NetworkInfo,
  PublicIpResult,
  ThemeMode,
  ToolSpec,
} from './types'

/**
 * 后端暴露给前端的方法集合。
 * pywebview 会把 Python 对象挂到 window.pywebview.api 上，
 * 每个方法调用返回一个 Promise。
 */
export interface OcApi {
  get_info(): Promise<AppInfo>
  list_tools(): Promise<ToolSpec[]>
  launch_tool(id: string): Promise<LaunchResult>
  get_theme(): Promise<ThemeMode>
  set_theme(mode: ThemeMode): Promise<boolean>
  open_url(url: string): Promise<boolean>
  open_tool_dir(): Promise<boolean>
  reveal_tool(id: string): Promise<boolean>
  refresh_tools(): Promise<number>
  check_url(url: string): Promise<any>
  url_alerts(): Promise<any[]>
  check_updates(force?: boolean): Promise<any[]>
  search_music(keyword?: string): Promise<any[]>
  music_url(path: string): Promise<string>
  search_music_online(keyword: string, platform?: string): Promise<any[]>
  fetch_music(song_id: string, platform?: string): Promise<string>
  list_wallpapers(directory?: string): Promise<any[]>
  set_wallpaper(path: string): Promise<boolean>
  random_wallpaper(directory?: string): Promise<any>

  // ── 系统监测（主页数据源） ──
  get_hardware(): Promise<HardwareInfo>
  get_metrics(): Promise<Metrics>
  get_network(): Promise<NetworkInfo>
  get_ip(): Promise<IpInfo>
  query_public_ip(): Promise<PublicIpResult>
  window_minimize(): Promise<void>
  window_toggle_maximize(): Promise<void>
  window_close(): Promise<void>
  window_start_drag(): Promise<void>

  // ── 系统集成（托盘 / 自启 / 右键打开方式） ──
  get_autostart(): Promise<boolean>
  set_autostart(enabled: boolean): Promise<boolean>
  get_openwith_registered(): Promise<boolean>
  set_openwith_registered(enabled: boolean): Promise<boolean>
}

// ════════════════════════════════════════════════════════════
// 开发模式 mock：没有 pywebview 时也能在浏览器里预览 UI
// ════════════════════════════════════════════════════════════

const MOCK_TOOLS: ToolSpec[] = [
  {
    id: 'random_picker', name: '随机点名', category: 'classroom',
    description: '老虎机动效滚动抽取，支持排除已点名单',
    icon: '🎰', version: '1.0.0', author: 'OpenClass', kind: 'builtin',
    entry: 'tools/random_picker', args: [], admin: false, available: true,
    tags: ['课堂', '演示'],
  },
  {
    id: 'pdf_merge', name: 'PDF 合并', category: 'document',
    description: '把多个 PDF 按顺序合并成一个文件',
    icon: '📄', version: '1.2.0', author: 'OpenClass', kind: 'plugin',
    entry: 'tools/pdf_merge', args: [], admin: false, available: true,
    tags: ['文档', '批处理'],
  },
  {
    id: 'batch_rename', name: '批量重命名', category: 'file',
    description: '按规则批量重命名文件，支持正则与序号',
    icon: '🔤', version: '0.9.1', author: 'OpenClass', kind: 'plugin',
    entry: 'tools/batch_rename', args: [], admin: false, available: true,
    tags: ['文件', '批处理'],
  },
  {
    id: 'image_compress', name: '图片压缩', category: 'media',
    description: '批量压缩图片体积，支持质量与尺寸设定',
    icon: '🖼️', version: '1.0.3', author: 'OpenClass', kind: 'plugin',
    entry: 'tools/image_compress', args: [], admin: false, available: true,
    tags: ['图片'],
  },
  {
    id: 'file_hash', name: '文件校验', category: 'file',
    description: '计算 MD5 / SHA1 / SHA256 并比对',
    icon: '#️⃣', version: '1.0.0', author: 'OpenClass', kind: 'plugin',
    entry: 'tools/file_hash', args: [], admin: false, available: true,
    tags: ['文件', '校验'],
  },
  {
    id: 'diskgenius', name: 'DiskGenius', category: 'external',
    description: '第三方磁盘分区工具（需自行放入 tools 目录）',
    icon: '💽', version: '-', author: '第三方', kind: 'external',
    entry: 'tools/diskgenius/DG.exe', args: [], admin: true, available: false,
    reason: '未检测到可执行文件', tags: ['磁盘'],
  },
]

// ── 监测数据的 mock：开发模式下让曲线真实波动，便于观察 UI ──

function mockHistory(count = 60) {
  const now = Date.now()
  return Array.from({ length: count }, (_, i) => ({
    t: now - (count - i) * 1000,
    cpu: 8 + Math.sin(i / 5) * 6 + Math.random() * 14,
    memory: 46 + Math.sin(i / 12) * 2 + Math.random() * 2,
    download: Math.max(0, Math.sin(i / 4) * 320000 + Math.random() * 90000),
    upload: Math.max(0, Math.abs(Math.cos(i / 6)) * 60000 + Math.random() * 20000),
  }))
}

const MOCK_HARDWARE: HardwareInfo = {
  cpu: {
    name: 'Intel(R) Core(TM) i7-12700H @ 2.30GHz',
    cores: 14,
    threads: 20,
    freqMax: 4600,
    freqCurrent: 2688,
    arch: 'AMD64',
  },
  memory: { total: 34359738368, percent: 47.4, totalGB: 32 },
  swap: { total: 8589934592, used: 2147483648, percent: 25 },
  disks: [
    { device: 'C:', mountpoint: 'C:\\', fstype: 'NTFS', total: 512110190592, used: 320444825600, free: 191665364992, percent: 62.6 },
    { device: 'D:', mountpoint: 'D:\\', fstype: 'NTFS', total: 1000202039296, used: 512110190592, free: 488091848704, percent: 51.2 },
  ],
  gpus: [
    { name: 'NVIDIA GeForce RTX 3060 Laptop GPU', memoryGB: 6, driverVersion: '31.0.15.3623' },
    { name: 'Intel(R) Iris(R) Xe Graphics', memoryGB: 1, driverVersion: '31.0.101.4032' },
  ],
  boards: [{ manufacturer: 'Dell Inc.', product: '0J8H2K' }],
  os: { system: 'Windows', release: '11', version: '10.0.26100', build: '26100', hostname: 'DESKTOP-MOCK' },
  bootTime: Date.now() / 1000 - 3 * 3600 - 42 * 60,
}

const MOCK_NETWORK: NetworkInfo = {
  interfaces: [
    { name: 'Ethernet', ipv4: [{ address: '192.168.1.12', netmask: '255.255.255.0' }], ipv6: [], mac: 'A4-BB-6D-1C-2E-90', up: true, speedMbps: 1000, mtu: 1500, bytesSent: 1024000, bytesRecv: 20480000 },
    { name: 'WLAN', ipv4: [{ address: '192.168.1.31', netmask: '255.255.255.0' }], ipv6: [], mac: '7C-B2-7D-9A-11-03', up: true, speedMbps: 866, mtu: 1500, bytesSent: 512000, bytesRecv: 8192000 },
    { name: 'Loopback', ipv4: [{ address: '127.0.0.1', netmask: '255.0.0.0' }], ipv6: ['::1'], mac: null, up: true, speedMbps: 1073, mtu: 1500, bytesSent: 0, bytesRecv: 0 },
  ],
  topology: { gateways: ['192.168.1.1'], dnsServers: ['223.5.5.5', '114.114.114.114'], dhcpEnabled: true },
}

const MOCK_API: OcApi = {
  async get_info() {
    return {
      name: 'OpenClass-Box', version: '0.1.2', author: 'OpenClass-Box Contributors',
      description: '开源实用工具箱', portable: true,
      rootDir: 'E:/OpenClass', toolDir: 'E:/OpenClass/tools',
      pythonVersion: '3.13.7', platform: 'Windows',
    }
  },
  async list_tools() { return MOCK_TOOLS },
  async launch_tool(id) {
    return { ok: true, message: `已启动工具：${id}（开发模式模拟）` }
  },
  async get_theme() { return 'dark' },
  async set_theme() { return true },
  async open_url(url) { window.open(url, '_blank'); return true },
  async open_tool_dir() { return true },
  async reveal_tool() { return true },
  async refresh_tools() { return MOCK_TOOLS.length },
  async check_url(url) { return { url, host: '', score: 0, level: 'safe', reasons: ['开发模式：未执行真实检测'] } },
  async url_alerts() { return [] },
  async check_updates() { return [] },
  async search_music() { return [] },
  async music_url(path) { return path },
  async search_music_online() { return [] },
  async fetch_music() { return '' },
  async list_wallpapers() { return [] },
  async set_wallpaper() { return false },
  async random_wallpaper() { return { ok: false, message: '' } },
  async get_hardware() { return MOCK_HARDWARE },
  async get_metrics() {
    const history = mockHistory()
    const last = history[history.length - 1]
    return {
      timestamp: Date.now(),
      cpu: {
        percent: last.cpu,
        perCore: Array.from({ length: 20 }, () => 5 + Math.random() * 40),
        freqCurrent: MOCK_HARDWARE.cpu.freqCurrent,
        loadAvg: null,
      },
      memory: {
        percent: last.memory,
        used: MOCK_HARDWARE.memory.total * (last.memory / 100),
        total: MOCK_HARDWARE.memory.total,
        available: MOCK_HARDWARE.memory.total * (1 - last.memory / 100),
      },
      network: { download: last.download, upload: last.upload, totalRecv: 20480000, totalSent: 1024000 },
      disk: { read: 24000, write: 8000 },
      history,
    }
  },
  async get_network() { return MOCK_NETWORK },
  async get_ip() {
    return {
      hostname: MOCK_HARDWARE.os.hostname,
      local: '192.168.1.12',
      loopback: '127.0.0.1',
      public: { ip: null, source: null, reachable: false, queried: false },
    }
  },
  async query_public_ip() {
    await new Promise((r) => setTimeout(r, 600))
    return { ip: '203.0.113.42', source: 'api.ipify.org', reachable: true }
  },
  async window_minimize() {},
  async window_toggle_maximize() {},
  async window_close() { window.close() },
  async window_start_drag() {},
  async get_autostart() { return false },
  async set_autostart() { return true },
  async get_openwith_registered() { return false },
  async set_openwith_registered() { return false },
}

/**
 * pywebview 的 API 是**异步注入**的：在 window.pywebviewready（或
 * window.pywebview.ready）resolve 之前，window.pywebview.api 还不存在。
 * 因此绝不能用 `?? MOCK_API` 在模块加载时一次性决定——那样会永远卡在 mock，
 * 导致主页显示假数据。这里用 Proxy：每次方法调用都实时解析当前可用的 API，
 * 宿主就绪后自然切换到真实实现；无宿主时（纯前端预览）才回退 MOCK。
 */
function resolveApi(): OcApi {
  const w = window as unknown as { pywebview?: { api?: OcApi } }
  return w.pywebview?.api ?? MOCK_API
}

export const api: OcApi = new Proxy({} as OcApi, {
  get(_target, prop: string | symbol) {
    const current = resolveApi()
    const value = (current as unknown as Record<string | symbol, unknown>)[prop]
    if (typeof value === 'function') {
      return (value as (...args: unknown[]) => unknown).bind(current)
    }
    return value
  },
})

/** 是否运行在 pywebview 宿主中（决定要不要显示窗口控制按钮等） */
export const isNative =
  typeof window !== 'undefined' &&
  (window as unknown as { pywebview?: unknown }).pywebview !== undefined
