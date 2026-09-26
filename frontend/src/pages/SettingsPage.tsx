import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Button, Switch, Spinner } from '@fluentui/react-components'
import { DesktopRegular, WeatherMoonRegular, WeatherSunnyRegular } from '@fluentui/react-icons'
import { api } from '../api'
import type { ThemeMode } from '../types'

interface Props {
  themeMode: ThemeMode
  setThemeMode: (m: ThemeMode) => void
}

const OPTIONS: { id: ThemeMode; label: string; icon: ReactNode; desc: string }[] = [
  { id: 'light', label: '浅色', icon: <WeatherSunnyRegular fontSize={16} />, desc: '明亮环境下的默认外观' },
  { id: 'dark', label: '深色', icon: <WeatherMoonRegular fontSize={16} />, desc: '低光环境，减轻眼部疲劳' },
  { id: 'system', label: '跟随系统', icon: <DesktopRegular fontSize={16} />, desc: '自动同步 Windows 的外观设置' },
]

function SwitchRow({
  label,
  desc,
  checked,
  disabled,
  onChange,
}: {
  label: string
  desc: string
  checked: boolean
  disabled?: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: '8px 0',
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 600 }}>{label}</div>
        <div className="oc-usage-sub">{desc}</div>
      </div>
      <Switch
        checked={checked}
        disabled={disabled}
        onChange={(_e, data) => onChange(data.checked)}
      />
    </div>
  )
}

export default function SettingsPage({ themeMode, setThemeMode }: Props) {
  const [autostart, setAutostart] = useState(false)
  const [openwith, setOpenwith] = useState(false)
  const [closeToTray, setCloseToTray] = useState(true)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  // ── 版本与更新 ──
  const [version, setVersion] = useState('')
  const [selfUpdate, setSelfUpdate] = useState<any>(null)
  const [components, setComponents] = useState<any[]>([])
  const [updateBusy, setUpdateBusy] = useState(true)

  useEffect(() => {
    void (async () => {
      try {
        const [a, o, c, info] = await Promise.all([
          api.get_autostart(),
          api.get_openwith_registered(),
          api.get_close_to_tray(),
          api.get_info(),
        ])
        setAutostart(a)
        setOpenwith(o)
        setCloseToTray(c)
        setVersion(info.version)
      } catch {
        // 忽略：开发模式下拿不到真实值
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const checkUpdate = async () => {
    setUpdateBusy(true)
    try {
      const [self, comps] = await Promise.all([api.check_self_update(), api.check_updates(true)])
      setSelfUpdate(self)
      setComponents(comps ?? [])
    } catch {
      setSelfUpdate({ ok: false, message: '检查失败（可能未联网）' })
      setComponents([])
    } finally {
      setUpdateBusy(false)
    }
  }

  useEffect(() => {
    void checkUpdate()
  }, [])

  const select = async (m: ThemeMode) => {
    setThemeMode(m)
    await api.set_theme(m)
  }

  const toggleAutostart = async (checked: boolean) => {
    setBusy(true)
    try {
      const ok = await api.set_autostart(checked)
      setAutostart(ok ? checked : autostart)
    } finally {
      setBusy(false)
    }
  }

  const toggleOpenwith = async (checked: boolean) => {
    setBusy(true)
    try {
      const ok = await api.set_openwith_registered(checked)
      setOpenwith(ok ? checked : openwith)
    } finally {
      setBusy(false)
    }
  }

  const toggleCloseToTray = async (checked: boolean) => {
    setBusy(true)
    try {
      const ok = await api.set_close_to_tray(checked)
      setCloseToTray(ok ? checked : closeToTray)
    } finally {
      setBusy(false)
    }
  }

  const componentUpdates = components.filter((item) => item.hasUpdate)

  return (
    <div className="oc-page">
      <div className="oc-page-header">
        <div className="oc-page-title">设置</div>
        <div className="oc-page-desc">偏好保存在程序目录下的 data/app_config.json</div>
      </div>

      <div className="oc-panel-title" style={{ fontSize: 12, opacity: 0.8 }}>
        外观
      </div>

      <div className="oc-grid oc-grid-3">
        {OPTIONS.map((o) => (
          <div
            key={o.id}
            className="oc-toolcard"
            style={{
              borderColor: themeMode === o.id ? 'var(--oc-accent)' : undefined,
              background: themeMode === o.id ? 'var(--oc-accent-soft)' : undefined,
            }}
            onClick={() => void select(o.id)}
          >
            <div className="oc-toolcard-top">
              <div className="oc-toolcard-icon">{o.icon}</div>
              <div className="oc-toolcard-head">
                <div className="oc-toolcard-name">{o.label}</div>
              </div>
            </div>
            <div className="oc-toolcard-desc">{o.desc}</div>
          </div>
        ))}
      </div>

      <div className="oc-panel-title" style={{ fontSize: 12, opacity: 0.8, marginTop: 20 }}>
        系统集成
      </div>
      <div className="oc-panel" style={{ marginBottom: 12 }}>
        {loading ? (
          <div className="oc-usage-sub">
            <Spinner size="tiny" /> 读取系统设置…
          </div>
        ) : (
          <>
            <SwitchRow
              label="开机自启"
              desc="登录 Windows 后自动在后台运行（仅当前用户）"
              checked={autostart}
              disabled={busy}
              onChange={toggleAutostart}
            />
            <div style={{ borderTop: '1px solid var(--oc-border)', margin: '4px 0' }} />
            <SwitchRow
              label="关闭时最小化到托盘"
              desc="开启：点关闭按钮只隐藏窗口，程序继续驻留托盘；关闭：点关闭直接退出程序"
              checked={closeToTray}
              disabled={busy}
              onChange={toggleCloseToTray}
            />
            <div style={{ borderTop: '1px solid var(--oc-border)', margin: '4px 0' }} />
            <SwitchRow
              label="右键「打开方式」集成"
              desc="把 OpenClass-Box 收编进文件的右键打开方式菜单（需打包为 exe 后生效）"
              checked={openwith}
              disabled={busy}
              onChange={toggleOpenwith}
            />
          </>
        )}
      </div>

      <div className="oc-panel-title" style={{ fontSize: 12, opacity: 0.8 }}>
        更新
      </div>
      <div className="oc-panel" style={{ marginBottom: 12 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12,
            padding: '4px 0',
          }}
        >
          <div>
            <div style={{ fontWeight: 600 }}>
              OpenClass-Box {version ? `v${version}` : ''}
            </div>
            <div className="oc-usage-sub">
              {updateBusy
                ? '正在检查新版本…'
                : selfUpdate?.hasUpdate
                  ? `发现新版本：${selfUpdate.latest}${selfUpdate.publishedAt ? `（${selfUpdate.publishedAt.slice(0, 10)} 发布）` : ''}`
                  : selfUpdate?.ok
                    ? '已是最新版本'
                    : (selfUpdate?.message ?? '未能获取版本信息')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button size="small" appearance="secondary" onClick={checkUpdate} disabled={updateBusy}>
              重新检查
            </Button>
            {selfUpdate?.hasUpdate && (
              <Button
                size="small"
                appearance="primary"
                onClick={() => void api.open_url(selfUpdate.url)}
              >
                前往下载
              </Button>
            )}
          </div>
        </div>

        {componentUpdates.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <div className="oc-list-sub" style={{ marginBottom: 6 }}>
              已集成组件有 {componentUpdates.length} 项可更新：
            </div>
            {componentUpdates.map((item) => (
              <div
                key={item.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '4px 0',
                }}
              >
                <span className="oc-usage-sub">
                  {item.name}：{item.current} → {item.latest}
                </span>
                <Button size="small" onClick={() => void api.open_url(item.url)}>
                  前往
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="oc-panel-title" style={{ fontSize: 12, opacity: 0.8 }}>
        工具目录
      </div>
      <Button appearance="secondary" onClick={() => void api.open_tool_dir()}>
        打开 tools 目录
      </Button>
    </div>
  )
}
