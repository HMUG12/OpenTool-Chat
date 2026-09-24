import { useEffect, useState } from 'react'
import { Button, Spinner } from '@fluentui/react-components'
import { api } from '../api'

export default function UpdatePage() {
  const [items, setItems] = useState<any[]>([])
  const [busy, setBusy] = useState(true)

  const load = async () => {
    setBusy(true)
    try {
      setItems(await api.check_updates(true))
    } catch {
      setItems([])
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const updates = items.filter((i) => i.hasUpdate)

  return (
    <div className="oc-page">
      <div className="oc-page-title">更新</div>

      <div className="oc-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            {busy
              ? '正在检查…'
              : updates.length
                ? `有 ${updates.length} 个组件可更新`
                : '全部为最新版本'}
          </span>
          <Button size="small" onClick={load} disabled={busy}>
            重新检查
          </Button>
        </div>
      </div>

      {busy && (
        <div className="oc-empty">
          <Spinner size="small" label="检查中…" />
        </div>
      )}

      {!busy && items.length === 0 && (
        <div className="oc-empty">未能获取版本信息（可能未联网）</div>
      )}

      {!busy && items.length > 0 && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">组件版本</div>
          <div style={{ marginTop: 8 }}>
            {items.map((it) => (
              <div
                key={it.id}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}
              >
                <span>
                  {it.name}：{it.current} → {it.latest}
                  {it.hasUpdate ? '（有更新）' : ''}
                </span>
                <Button size="small" onClick={() => void api.open_url(it.url)}>
                  前往
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
