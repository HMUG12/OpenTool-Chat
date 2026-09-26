import { useEffect, useState } from 'react'
import { Button, Input, Spinner } from '@fluentui/react-components'
import { api } from '../api'

function formatSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

export default function MaintenancePage() {
  const [cleanItems, setCleanItems] = useState<any[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [cleanBusy, setCleanBusy] = useState(false)
  const [cleanMsg, setCleanMsg] = useState('')

  const [diag, setDiag] = useState<any>(null)
  const [diagBusy, setDiagBusy] = useState(false)

  const [pkgDir, setPkgDir] = useState('')
  const [packages, setPackages] = useState<any[]>([])
  const [pkgMsg, setPkgMsg] = useState('')

  const [points, setPoints] = useState<any[]>([])
  const [pointMsg, setPointMsg] = useState('')
  const [pointBusy, setPointBusy] = useState(false)

  const loadCleanup = async () => {
    try {
      const result = await api.analyze_cleanup()
      const items = result?.items ?? []
      setCleanItems(items)
      setSelected(
        items.filter((i: any) => i.exists && i.size > 0).map((i: any) => i.key)
      )
    } catch {
      setCleanItems([])
    }
  }

  const loadPackages = async (dir = '') => {
    try {
      const result = await api.list_packages(dir)
      setPackages(result?.items ?? [])
      setPkgMsg(result?.message ?? '')
    } catch {
      setPackages([])
    }
  }

  const loadPoints = async () => {
    try {
      const result = await api.list_restore_points()
      setPoints(result?.points ?? [])
      setPointMsg(result?.message ?? '')
    } catch {
      setPoints([])
    }
  }

  useEffect(() => {
    void loadCleanup()
    void loadPackages()
    void loadPoints()
  }, [])

  const toggle = (key: string) => {
    setSelected((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    )
  }

  const clean = async () => {
    if (!selected.length) return
    setCleanBusy(true)
    setCleanMsg('')
    try {
      const result = await api.run_cleanup(selected)
      setCleanMsg(
        `${(result?.details ?? []).join('；')}（共释放 ${formatSize(result?.freed ?? 0)}）`
      )
      await loadCleanup()
    } catch {
      setCleanMsg('清理失败，请稍后重试')
    } finally {
      setCleanBusy(false)
    }
  }

  const diagnose = async () => {
    setDiagBusy(true)
    try {
      setDiag(await api.run_netdiag())
    } catch {
      setDiag(null)
    } finally {
      setDiagBusy(false)
    }
  }

  const install = async (path: string) => {
    const result = await api.install_package(path)
    setPkgMsg(result?.message ?? '')
  }

  const createPoint = async () => {
    setPointBusy(true)
    setPointMsg('')
    try {
      const result = await api.create_restore_point()
      setPointMsg(result?.message ?? '')
      await loadPoints()
    } catch {
      setPointMsg('创建失败，请稍后重试')
    } finally {
      setPointBusy(false)
    }
  }

  return (
    <div className="oc-page">
      <div className="oc-page-header">
        <div className="oc-page-title">维护</div>
        <div className="oc-page-desc">清理磁盘垃圾、排查网络问题（所有数据均为本机实时统计）</div>
      </div>

      {/* ── 磁盘清理 ── */}
      <div className="oc-panel">
        <div className="oc-panel-title">磁盘清理</div>
        {cleanItems.length === 0 ? (
          <div className="oc-list-sub" style={{ marginTop: 8 }}>
            正在统计…
          </div>
        ) : (
          <>
            <div className="oc-list">
              {cleanItems.map((item) => (
                <div className="oc-list-row" key={item.key}>
                  <div className="oc-list-main">
                    <div className="oc-list-title">
                      <input
                        type="checkbox"
                        checked={selected.includes(item.key)}
                        onChange={() => toggle(item.key)}
                        disabled={!item.exists}
                        style={{ marginRight: 8 }}
                      />
                      {item.name}
                    </div>
                    <div className="oc-list-sub">{item.desc}</div>
                  </div>
                  <div className="oc-list-sub" style={{ whiteSpace: 'nowrap' }}>
                    {item.exists ? formatSize(item.size) : '无'}
                  </div>
                </div>
              ))}
            </div>
            <div className="oc-actions" style={{ marginTop: 12 }}>
              <Button appearance="primary" onClick={clean} disabled={cleanBusy || !selected.length}>
                {cleanBusy ? '正在清理…' : `立即清理（已选 ${selected.length} 项）`}
              </Button>
              <Button appearance="secondary" onClick={loadCleanup} disabled={cleanBusy}>
                重新统计
              </Button>
            </div>
            {cleanMsg && (
              <div className="oc-list-sub" style={{ marginTop: 8 }}>
                {cleanMsg}
              </div>
            )}
          </>
        )}
      </div>

      {/* ── 网络诊断 ── */}
      <div className="oc-panel" style={{ marginTop: 12 }}>
        <div className="oc-panel-title">网络诊断</div>
        <div className="oc-list-sub" style={{ marginBottom: 10 }}>
          断网时依次检查：本机地址 → 局域网 → 域名解析 → 外网
        </div>
        <div className="oc-actions">
          <Button appearance="primary" onClick={diagnose} disabled={diagBusy}>
            {diagBusy ? '诊断中…' : '开始诊断'}
          </Button>
          {diag && !diagBusy && (
            <span className="oc-list-sub">
              {diag.healthy ? '✅ 网络一切正常' : `⚠️ ${diag.total - diag.okCount} 项未通过`}
            </span>
          )}
        </div>

        {diagBusy && (
          <div style={{ marginTop: 12 }}>
            <Spinner size="tiny" label="正在检查网络，请稍候…" />
          </div>
        )}

        {diag && !diagBusy && (
          <div className="oc-list" style={{ marginTop: 10 }}>
            {diag.items.map((item: any) => (
              <div className="oc-list-row" key={item.name}>
                <div className="oc-list-main">
                  <div className="oc-list-title">
                    {item.ok ? '✅' : '❌'} {item.name}
                  </div>
                  <div className="oc-list-sub">{item.detail}</div>
                  {!item.ok && item.suggest && (
                    <div className="oc-list-warn">建议：{item.suggest}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 离线软件目录 ── */}
      <div className="oc-panel" style={{ marginTop: 12 }}>
        <div className="oc-panel-title">离线软件目录</div>
        <div className="oc-list-sub" style={{ marginBottom: 10 }}>
          把常用软件的安装包放进程序目录下的 software 文件夹，这里会自动列出来，点一下就装
        </div>
        <div className="oc-searchbar">
          <Input
            value={pkgDir}
            onChange={(_, data) => setPkgDir(data.value)}
            placeholder="软件目录（留空使用默认 software 文件夹）"
            style={{ flex: 1 }}
          />
          <Button appearance="secondary" onClick={() => loadPackages(pkgDir)}>
            刷新
          </Button>
        </div>
        {packages.length === 0 ? (
          <div className="oc-list-sub" style={{ marginTop: 10 }}>
            {pkgMsg || '目录中暂无安装包'}
          </div>
        ) : (
          <div className="oc-list oc-scroll">
            {packages.map((pkg) => (
              <div className="oc-list-row" key={pkg.path}>
                <div className="oc-list-main">
                  <div className="oc-list-title">{pkg.name}</div>
                  <div className="oc-list-sub">{formatSize(pkg.size)}</div>
                </div>
                <Button size="small" onClick={() => install(pkg.path)}>
                  安装
                </Button>
              </div>
            ))}
          </div>
        )}
        {pkgMsg && packages.length > 0 && (
          <div className="oc-list-sub" style={{ marginTop: 8 }}>
            {pkgMsg}
          </div>
        )}
      </div>

      {/* ── 系统还原点 ── */}
      <div className="oc-panel" style={{ marginTop: 12 }}>
        <div className="oc-panel-title">系统还原点</div>
        <div className="oc-list-sub" style={{ marginBottom: 10 }}>
          装软件或改设置前先建一个还原点，出问题可以回滚。Windows 默认 24 小时内只允许创建一个，这是系统限制
        </div>
        <div className="oc-actions">
          <Button appearance="primary" onClick={createPoint} disabled={pointBusy}>
            {pointBusy ? '正在请求…' : '创建还原点'}
          </Button>
          <Button appearance="secondary" onClick={loadPoints} disabled={pointBusy}>
            刷新列表
          </Button>
        </div>
        {pointMsg && (
          <div className="oc-list-sub" style={{ marginTop: 8 }}>
            {pointMsg}
          </div>
        )}
        {points.length > 0 && (
          <div className="oc-list oc-scroll">
            {points.map((pt: any, index: number) => (
              <div className="oc-list-row" key={index}>
                <div className="oc-list-main">
                  <div className="oc-list-title">{pt.Description || '（无描述）'}</div>
                  <div className="oc-list-sub">{String(pt.CreationTime ?? '')}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
