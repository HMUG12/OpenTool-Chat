import { useEffect, useState } from 'react'
import { Button, Input, Spinner } from '@fluentui/react-components'
import { api } from '../api'

export default function WallpaperPage() {
  const [dir, setDir] = useState('')
  const [list, setList] = useState<any[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = async () => {
    setBusy(true)
    try {
      setList(await api.list_wallpapers(dir))
    } catch {
      setList([])
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const apply = async (path: string) => {
    const ok = await api.set_wallpaper(path)
    setMsg(ok ? '壁纸已更换' : '设置失败')
    window.setTimeout(() => setMsg(''), 2500)
  }

  const random = async () => {
    const result = await api.random_wallpaper(dir)
    setMsg(result?.message ?? '')
    window.setTimeout(() => setMsg(''), 2500)
  }

  return (
    <div className="oc-page">
      <div className="oc-page-title">壁纸</div>

      <div className="oc-panel">
        <div style={{ display: 'flex', gap: 8 }}>
          <Input
            value={dir}
            onChange={(_, data) => setDir(data.value)}
            placeholder="图片目录（留空使用「图片」文件夹）"
            style={{ flex: 1 }}
          />
          <Button appearance="primary" onClick={load} disabled={busy}>
            扫描
          </Button>
          <Button appearance="secondary" onClick={random} disabled={busy}>
            随机换一张
          </Button>
        </div>
        {msg && (
          <div className="oc-usage-sub" style={{ marginTop: 8 }}>
            {msg}
          </div>
        )}
      </div>

      {busy && (
        <div className="oc-empty">
          <Spinner size="small" label="扫描中…" />
        </div>
      )}

      {!busy && list.length === 0 && <div className="oc-empty">没有找到图片</div>}

      {!busy && list.length > 0 && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">共 {list.length} 张</div>
          <div style={{ maxHeight: 320, overflowY: 'auto', marginTop: 8 }}>
            {list.map((m, i) => (
              <div
                key={i}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}
              >
                <span>{m.name}</span>
                <Button size="small" onClick={() => apply(m.path)}>
                  设为壁纸
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
