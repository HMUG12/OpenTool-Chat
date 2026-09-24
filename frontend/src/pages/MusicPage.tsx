import { useEffect, useState } from 'react'
import { Button, Input, Spinner } from '@fluentui/react-components'
import { api } from '../api'

export default function MusicPage() {
  const [keyword, setKeyword] = useState('')
  const [platform, setPlatform] = useState('local')
  const [list, setList] = useState<any[]>([])
  const [current, setCurrent] = useState<any>(null)
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async (kw: string) => {
    setBusy(true)
    try {
      // 超时兜底：后端异常或目录巨大时也不让界面永远转圈
      const timeout = new Promise<never>((_, reject) =>
        window.setTimeout(() => reject(new Error('timeout')), 15000)
      )
      const result = await Promise.race([
        platform === 'local'
          ? api.search_music(kw)
          : api.search_music_online(kw, platform),
        timeout,
      ])
      setList(result as any[])
    } catch {
      setList([])
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void load('')
  }, [])

  const play = async (item: any) => {
    setBusy(true)
    try {
      // 在线歌曲先拉取到本地缓存，再交给播放器（本地歌曲直接用原路径）
      const path = item.path || (await api.fetch_music(item.id, item.platform || platform))
      if (!path) return
      setCurrent({ ...item, path })
      setUrl(await api.music_url(path))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="oc-page">
      <div className="oc-page-title">音乐</div>

      <div className="oc-panel">
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <Button
            appearance={platform === 'local' ? 'primary' : 'secondary'}
            size="small"
            onClick={() => setPlatform('local')}
          >
            本地
          </Button>
          <Button
            appearance={platform === 'netease' ? 'primary' : 'secondary'}
            size="small"
            onClick={() => setPlatform('netease')}
          >
            网易云
          </Button>
          <span className="oc-usage-sub" style={{ alignSelf: 'center' }}>
            {platform === 'local' ? '扫描本机音乐库' : '在线搜索并拉取到本地播放'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Input
            value={keyword}
            onChange={(_, data) => setKeyword(data.value)}
            placeholder={platform === 'local' ? '搜索本地音乐（留空列出全部）' : '搜索在线音乐'}
            style={{ flex: 1 }}
          />
          <Button appearance="primary" onClick={() => load(keyword)} disabled={busy}>
            搜索
          </Button>
        </div>
      </div>

      {busy && (
        <div className="oc-empty">
          <Spinner size="small" label="扫描中…" />
        </div>
      )}

      {!busy && list.length === 0 && <div className="oc-empty">未找到音乐文件</div>}

      {!busy && list.length > 0 && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">共 {list.length} 首</div>
          <div style={{ maxHeight: 320, overflowY: 'auto', marginTop: 8 }}>
            {list.map((m, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '6px 0',
                }}
              >
                <span>{m.name}</span>
                <Button size="small" onClick={() => play(m)}>
                  播放
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {current && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">正在播放：{current.name}</div>
          <audio src={url} controls autoPlay style={{ width: '100%', marginTop: 8 }} />
        </div>
      )}
    </div>
  )
}
