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
  check_self_update(): Promise<any>
  security_events(limit?: number): Promise<any[]>
  security_stats(): Promise<any>
  security_clear(): Promise<any>
  security_whitelist(): Promise<string[]>
  security_add_whitelist(domain: string): Promise<any>
  security_remove_whitelist(domain: string): Promise<any>
  security_settings(): Promise<any>
  set_security_settings(clipboard?: boolean, browser?: boolean): Promise<any>
  lan_status(): Promise<any>
  lan_scan(): Promise<any[]>
  lan_start_server(port?: number): Promise<any>
  lan_stop_server(): Promise<any>
  lan_nodes(): Promise<any[]>
  lan_events(limit?: number): Promise<any[]>
  lan_send(node_ids: string[], action: string, payload?: any): Promise<any>
  lan_remove_node(node_id: string): Promise<any>
  lan_reset_code(): Promise<string>
  lan_join(server_url?: string, code?: string): Promise<any>
  lan_leave(): Promise<any>
  search_music(keyword?: string): Promise<any[]>
  music_url(path: string): Promise<string>
  search_music_online(keyword: string, platform?: string): Promise<any[]>
  fetch_music(song_id: string, platform?: string): Promise<string>
  list_wallpapers(directory?: string): Promise<any>
  set_wallpaper(path: string, style?: string, scale?: number): Promise<any>
  random_wallpaper(directory?: string): Promise<any>
  import_wallpaper(source: string): Promise<any>
  pick_wallpaper_file(): Promise<any>
  set_dynamic_wallpaper(path: string, muted?: boolean): Promise<any>
  stop_dynamic_wallpaper(): Promise<any>
  dynamic_wallpaper_status(): Promise<any>
  current_wallpaper(): Promise<string>
  run_health_checks(): Promise<any>
  list_repairs(): Promise<any[]>
  run_repair(key: string): Promise<any>
  export_report(): Promise<any>
  analyze_cleanup(): Promise<any>
  run_cleanup(keys: string[]): Promise<any>
  run_netdiag(): Promise<any>
  list_packages(directory?: string): Promise<any>
  install_package(path: string): Promise<any>
  list_restore_points(): Promise<any>
  create_restore_point(description?: string): Promise<any>
  export_diagnostics(): Promise<any>
  list_processes(limit?: number): Promise<any>
  kill_process(pid: number): Promise<any>
  list_services(limit?: number): Promise<any>
  list_startup(): Promise<any>

  // ── 系统监测（主页数据源） ──
  get_hardware(): Promise<HardwareInfo>
  get_hardware_detail(quick?: boolean): Promise<any>
  get_metrics(): Promise<Metrics>
  get_network(): Promise<NetworkInfo>
  get_ip(): Promise<IpInfo>
  query_public_ip(): Promise<PublicIpResult>
  window_minimize(): Promise<void>
  window_toggle_maximize(): Promise<void>
  window_is_maximized(): Promise<boolean>
  window_close(): Promise<void>
  window_start_drag(): Promise<void>

  // ── 系统集成（托盘 / 自启 / 右键打开方式 / 关闭行为） ──
  get_autostart(): Promise<boolean>
  set_autostart(enabled: boolean): Promise<boolean>
  get_openwith_registered(): Promise<boolean>
  set_openwith_registered(enabled: boolean): Promise<boolean>
  get_close_to_tray(): Promise<boolean>
  get_data_dir(): Promise<string>
  set_close_to_tray(enabled: boolean): Promise<boolean>
}

// ════════════════════════════════════════════════════════════
// 开发模式 mock：没有 pywebview 时也能在浏览器里预览 UI
// ════════════════════════════════════════════════════════════

// 开发预览模式下没有任何工具数据（工具列表来自本地后端扫描）

// 开发预览模式下的空数据结构（刻意不编造任何硬件/网络信息）
const EMPTY_HARDWARE: HardwareInfo = {
  cpu: { name: '', cores: 0, threads: 0, freqMax: 0, freqCurrent: 0, arch: '' },
  memory: { total: 0, percent: 0, totalGB: 0 },
  swap: { total: 0, used: 0, percent: 0 },
  disks: [],
  gpus: [],
  boards: [],
  os: { system: '', release: '', version: '', build: '', hostname: '' },
  bootTime: 0,
}

const EMPTY_NETWORK: NetworkInfo = {
  interfaces: [],
  topology: { gateways: [], dnsServers: [], dhcpEnabled: false },
}

const MOCK_API: OcApi = {
  async get_info() {
    return {
      name: 'OpenClass-Box（开发预览）',
      version: '-',
      author: 'HMUG12',
      description: '当前为浏览器预览模式，未连接本地后端，因此不展示任何数据',
      portable: true,
      rootDir: '-',
      toolDir: '-',
      pythonVersion: '-',
      platform: '-',
    }
  },
  async list_tools() { return [] },
  async launch_tool() {
    return { ok: false, message: '开发预览模式：无法启动工具，请在桌面端使用' }
  },
  async get_theme() { return 'dark' },
  async set_theme() { return true },
  async open_url(url) { window.open(url, '_blank'); return true },
  async open_tool_dir() { return false },
  async reveal_tool() { return false },
  async refresh_tools() { return 0 },
  async check_url(url) { return { url, host: '', score: 0, level: 'safe', reasons: ['开发模式：未执行真实检测'] } },
  async url_alerts() { return [] },
  async check_updates() { return [] },
  async check_self_update() {
    return { ok: false, current: '-', latest: '', hasUpdate: false, url: '', publishedAt: '', message: '开发预览模式' }
  },
  async security_events() { return [] },
  async security_stats() { return { total: 0, today: 0, riskTotal: 0, riskToday: 0, whitelistCount: 0 } },
  async security_clear() { return { ok: true, message: '开发预览模式' } },
  async security_whitelist() { return [] },
  async security_add_whitelist() { return { ok: false, message: '开发预览模式' } },
  async security_remove_whitelist() { return { ok: true, message: '开发预览模式' } },
  async security_settings() { return { clipboard: true, browser: true } },
  async set_security_settings() { return { ok: true, settings: { clipboard: true, browser: true } } },
  async lan_status() {
    return {
      mode: 'single',
      server: { running: false, port: 38900, pairingCode: '------', nodeCount: 0, onlineCount: 0 },
      client: { enabled: false, state: 'idle', message: '开发预览模式' },
    }
  },
  async lan_scan() { return [] },
  async lan_start_server() { return { ok: false, message: '开发预览模式：无法启动服务' } },
  async lan_stop_server() { return { ok: true, message: '开发预览模式' } },
  async lan_nodes() { return [] },
  async lan_events() { return [] },
  async lan_send() { return { ok: false, message: '开发预览模式：无法下发指令' } },
  async lan_remove_node() { return { ok: false, message: '开发预览模式' } },
  async lan_reset_code() { return '------' },
  async lan_join() { return { ok: false, message: '开发预览模式：无法加入' } },
  async lan_leave() { return { ok: true, message: '开发预览模式' } },
  async search_music() { return [] },
  async music_url(path) { return path },
  async search_music_online() { return [] },
  async fetch_music() { return '' },
  async list_wallpapers() { return { items: [], importedDir: '' } },
  async set_wallpaper() { return { ok: false, message: '开发预览模式：无法设置壁纸' } },
  async random_wallpaper() { return { ok: false, message: '' } },
  async import_wallpaper() { return { ok: false, path: '', message: '开发预览模式：无法导入' } },
  async pick_wallpaper_file() { return { ok: false, path: '', message: '开发预览模式：无法打开文件选择框' } },
  async set_dynamic_wallpaper() { return { ok: false, message: '开发预览模式：无法设置动态壁纸' } },
  async stop_dynamic_wallpaper() { return { ok: true, message: '' } },
  async dynamic_wallpaper_status() { return { running: false, path: '', hasMpv: false } },
  async current_wallpaper() { return '' },
  async run_health_checks() { return { items: [], okCount: 0, total: 0, healthy: false } },
  async list_repairs() { return [] },
  async run_repair() { return { ok: false, message: '开发预览模式：无法执行修复', restart: false } },
  async export_report() { return { ok: false, path: '', content: '开发预览模式：无法导出报告' } },
  async analyze_cleanup() { return { items: [], total: 0 } },
  async run_cleanup() { return { ok: false, freed: 0, details: ['开发预览模式：无法执行清理'] } },
  async run_netdiag() { return { items: [], okCount: 0, total: 0, healthy: false } },
  async list_packages() { return { ok: true, dir: '-', items: [], message: '开发预览模式：无数据' } },
  async install_package() { return { ok: false, message: '开发预览模式：无法安装' } },
  async list_restore_points() { return { ok: true, points: [], message: '开发预览模式：无数据' } },
  async create_restore_point() { return { ok: false, message: '开发预览模式：无法创建还原点' } },
  async export_diagnostics() { return { ok: false, path: '', size: 0, parts: [], message: '开发预览模式：无法生成诊断包' } },
  async list_processes() { return { items: [], total: 0 } },
  async kill_process() { return { ok: false, message: '开发预览模式：无法结束进程' } },
  async list_services() { return { items: [], total: 0 } },
  async list_startup() { return { items: [], total: 0 } },
  async get_hardware() { return EMPTY_HARDWARE },
  async get_hardware_detail() {
    return {
      gpus: [],
      boards: [],
      bios: [],
      memModules: [],
      physicalDisks: [],
      cpuTemp: null,
      tempSource: '',
      fullReady: true,
    }
  },
  async get_metrics() {
    return {
      timestamp: Date.now(),
      cpu: { percent: 0, perCore: [], freqCurrent: 0, loadAvg: null },
      memory: { percent: 0, used: 0, total: 0, available: 0 },
      network: { download: 0, upload: 0, totalRecv: 0, totalSent: 0 },
      disk: { read: 0, write: 0 },
      history: [],
    }
  },
  async get_network() { return EMPTY_NETWORK },
  async get_ip() {
    return {
      hostname: '',
      local: '',
      loopback: '127.0.0.1',
      public: { ip: null, source: null, reachable: false, queried: false },
    }
  },
  async query_public_ip() {
    return { ip: null, source: null, reachable: false }
  },
  async window_minimize() {},
  async window_toggle_maximize() {},
  async window_is_maximized() { return false },
  async window_close() { window.close() },
  async window_start_drag() {},
  async get_autostart() { return false },
  async set_autostart() { return true },
  async get_openwith_registered() { return false },
  async set_openwith_registered() { return false },
  async get_close_to_tray() { return true },
  async get_data_dir() { return '-' },
  async set_close_to_tray() { return true },
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
