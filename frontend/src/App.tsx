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
  PuzzlePieceRegular,
  SettingsRegular,
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

type PageId = 'dashboard' | 'tools' | 'plugins' | 'settings' | 'about'

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
    const list = await api.list_tools()
    setTools(list)
    setToast({ ok: true, message: `扫描完成，共 ${list.length} 个工具` })
    window.setTimeout(() => setToast(null), 2200)
  }, [])

  const launch = useCallback(async (tool: ToolSpec) => {
    const result = await api.launch_tool(tool.id)
    setToast(result)
    window.setTimeout(() => setToast(null), result.ok ? 2600 : 5000)
  }, [])

  const navItems: NavItem[] = [
    { id: 'dashboard', label: '系统状态', icon: <GaugeRegular fontSize={16} /> },
    { id: 'tools', label: '工具箱', icon: <ToolboxRegular fontSize={16} />, badge: tools.length },
    { id: 'plugins', label: '插件', icon: <PuzzlePieceRegular fontSize={16} /> },
    { id: 'settings', label: '设置', icon: <SettingsRegular fontSize={16} /> },
    { id: 'about', label: '关于', icon: <InfoRegular fontSize={16} /> },
  ]

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <DashboardPage />
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
