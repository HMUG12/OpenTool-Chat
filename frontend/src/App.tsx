import { useCallback, useEffect, useState } from 'react'
import {
  FluentProvider,
  webLightTheme,
  webDarkTheme,
  MessageBar,
  MessageBarBody,
  Spinner,
} from '@fluentui/react-components'
import {
  GaugeRegular,
  InfoRegular,
  MusicNote1Regular,
  PuzzlePieceRegular,
  SettingsRegular,
  ShieldRegular,
  ToolboxRegular,
} from '@fluentui/react-icons'
import { api } from './api'
import type { ThemeMode, ToolSpec } from './types'
import TitleBar from './components/TitleBar'
import SideNav, { type NavItem } from './components/SideNav'
import DashboardPage from './pages/DashboardPage'
import ToolsPage from './pages/ToolsPage'
import PluginsPage from './pages/PluginsPage'
import SettingsPage from './pages/SettingsPage'
import AboutPage from './pages/AboutPage'
import SecurityPage from './pages/SecurityPage'
import MusicPage from './pages/MusicPage'
import UpdatePage from './pages/UpdatePage'
import WallpaperPage from './pages/WallpaperPage'
import HealthPage from './pages/HealthPage'
import MaintenancePage from './pages/MaintenancePage'
import DiagnosticsPage from './pages/DiagnosticsPage'

type PageId = 'health' | 'maintenance' | 'diagnostics' | 'dashboard' | 'music' | 'wallpaper' | 'tools' | 'plugins' | 'security' | 'update' | 'settings' | 'about'

interface Toast {
  ok: boolean
  message: string
}

export default function App() {
  const [themeMode, setThemeMode] = useState<ThemeMode>('system')
  const [systemDark, setSystemDark] = useState(true)
  const [page, setPage] = useState<PageId>('dashboard')
  const [tools, setTools] = useState<ToolSpec[]>([])
  const [category, setCategory] = useState('all')
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<Toast | null>(null)
  const [version, setVersion] = useState('')

  // ── 初始加载 ──
  useEffect(() => {
    void (async () => {
      try {
        const [saved, list, info] = await Promise.all([
          api.get_theme(),
          api.list_tools(),
          api.get_info(),
        ])
        if (saved) setThemeMode(saved)
        setTools(list)
        setVersion(info.version)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  // ── 跟随系统 ──
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const sync = () => setSystemDark(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])

  const isDark = themeMode === 'system' ? systemDark : themeMode === 'dark'

  const refresh = useCallback(async () => {
    await api.refresh_tools()
    const list = await api.list_tools()
    setTools(list)
    setToast({ ok: true, message: `扫描完成，共 ${list.length} 个工具` })
    window.setTimeout(() => setToast(null), 2200)
  }, [])

  // 静默刷新：不弹提示；仅在列表确有变化时才更新 state，避免无谓重渲染
  const silentRefresh = useCallback(async () => {
    try {
      await api.refresh_tools()
      const list = await api.list_tools()
      setTools((prev) => (JSON.stringify(prev) === JSON.stringify(list) ? prev : list))
    } catch {
      /* 后台扫描失败时静默忽略，不影响使用 */
    }
  }, [])

  // 进入「工具箱 / 插件」页时自动刷新一次
  useEffect(() => {
    if (page === 'tools' || page === 'plugins') {
      void silentRefresh()
    }
  }, [page, silentRefresh])

  // 运行期间定期自动扫描，增删工具无需手动点「重新扫描」
  useEffect(() => {
    const timer = window.setInterval(() => void silentRefresh(), 30000)
    return () => window.clearInterval(timer)
  }, [silentRefresh])

  // 网址风险告警：复制到的网址被判定可疑/高危时顶部提示（不拦截任何操作）
  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        const list = await api.url_alerts()
        if (list?.length) {
          const top = list[0]
          setToast({
            ok: false,
            message: `⚠️ 检测到可疑网址（${top.score} 分）：${top.url} — ${top.reasons?.[0] ?? ''}`,
          })
          window.setTimeout(() => setToast(null), 8000)
        }
      } catch {
        /* 拉取告警失败时忽略 */
      }
    }, 5000)
    return () => window.clearInterval(timer)
  }, [])

  const launch = useCallback(async (tool: ToolSpec) => {
    const result = await api.launch_tool(tool.id)
    setToast(result)
    window.setTimeout(() => setToast(null), result.ok ? 2600 : 5000)
  }, [])

  const navItems: NavItem[] = [
    { id: 'health', label: '一键体检', icon: <ShieldRegular fontSize={16} /> },
    { id: 'maintenance', label: '维护', icon: <ToolboxRegular fontSize={16} /> },
    { id: 'diagnostics', label: '诊断', icon: <GaugeRegular fontSize={16} /> },
    { id: 'dashboard', label: '系统状态', icon: <GaugeRegular fontSize={16} /> },
    { id: 'music', label: '音乐', icon: <MusicNote1Regular fontSize={16} /> },
    { id: 'wallpaper', label: '壁纸', icon: <SettingsRegular fontSize={16} /> },
    { id: 'tools', label: '工具箱', icon: <ToolboxRegular fontSize={16} />, badge: tools.length },
    { id: 'plugins', label: '插件', icon: <PuzzlePieceRegular fontSize={16} /> },
    { id: 'security', label: '安全', icon: <ShieldRegular fontSize={16} /> },
    { id: 'update', label: '更新', icon: <SettingsRegular fontSize={16} /> },
    { id: 'settings', label: '设置', icon: <SettingsRegular fontSize={16} /> },
    { id: 'about', label: '关于', icon: <InfoRegular fontSize={16} /> },
  ]

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <DashboardPage />
      case 'health':
        return <HealthPage />
      case 'maintenance':
        return <MaintenancePage />
      case 'diagnostics':
        return <DiagnosticsPage />
      case 'tools':
        return (
          <ToolsPage
            tools={tools}
            category={category}
            setCategory={setCategory}
            onLaunch={launch}
          />
        )
      case 'plugins':
        return <PluginsPage tools={tools} onRefresh={refresh} />
      case 'security':
        return <SecurityPage />
      case 'music':
        return <MusicPage />
      case 'wallpaper':
        return <WallpaperPage />
      case 'update':
        return <UpdatePage />
      case 'settings':
        return <SettingsPage themeMode={themeMode} setThemeMode={setThemeMode} />
      case 'about':
        return <AboutPage toolCount={tools.length} />
      default:
        return null
    }
  }

  return (
    <FluentProvider theme={isDark ? webDarkTheme : webLightTheme} className="oc-root">
      <TitleBar />
      <div className="oc-body">
        <SideNav
          items={navItems}
          activeId={page}
          onSelect={(id) => setPage(id as PageId)}
          version={version}
        />

        <div className="oc-content">
          {toast && (
            <div style={{ padding: '8px 24px 0', flexShrink: 0 }}>
              <MessageBar intent={toast.ok ? 'success' : 'error'}>
                <MessageBarBody>{toast.message}</MessageBarBody>
              </MessageBar>
            </div>
          )}

          {loading ? (
            <div className="oc-empty">
              <Spinner size="medium" label="正在加载…" />
            </div>
          ) : (
            renderPage()
          )}
        </div>
      </div>
    </FluentProvider>
  )
}
