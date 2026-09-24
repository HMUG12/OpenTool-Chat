import { useState } from 'react'
import { Button, Input, Spinner } from '@fluentui/react-components'
import { api } from '../api'

const LEVEL_TEXT: Record<string, string> = {
  safe: '安全',
  warn: '可疑',
  danger: '高危',
}

export default function SecurityPage() {
  const [url, setUrl] = useState('')
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  const check = async () => {
    const target = url.trim()
    if (!target) return
    setBusy(true)
    try {
      setResult(await api.check_url(target))
    } catch {
      setResult({ url: target, score: 0, level: 'safe', reasons: ['检测失败，请稍后重试'] })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="oc-page">
      <div className="oc-page-title">网址安全检测</div>

      <div className="oc-panel">
        <div style={{ display: 'flex', gap: 8 }}>
          <Input
            value={url}
            onChange={(_, data) => setUrl(data.value)}
            placeholder="输入或粘贴要检测的网址"
            style={{ flex: 1 }}
          />
          <Button appearance="primary" onClick={check} disabled={busy || !url.trim()}>
            检测
          </Button>
        </div>
        <div className="oc-usage-sub" style={{ marginTop: 8 }}>
          复制网址时会自动检测，发现风险仅在顶部提示，不会拦截你的任何操作。
        </div>
      </div>

      {busy && (
        <div className="oc-empty">
          <Spinner size="small" label="正在检测…" />
        </div>
      )}

      {result && !busy && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">
            检测结果：{result.score} 分 · {LEVEL_TEXT[result.level] ?? result.level}
          </div>
          {result.reasons?.length ? (
            <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
              {result.reasons.map((r: string, i: number) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : (
            <div className="oc-usage-sub">未发现风险特征</div>
          )}
        </div>
      )}
    </div>
  )
}
