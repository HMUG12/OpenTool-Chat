import { useState } from 'react'
import { Button, Spinner } from '@fluentui/react-components'
import { api } from '../api'

export default function HealthPage() {
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  const run = async () => {
    setBusy(true)
    try {
      setResult(await api.run_health_checks())
    } catch {
      setResult(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="oc-page">
      <div className="oc-page-title">一键体检</div>
      <div className="oc-page-desc">上课前点一下，看看这台一体机有没有问题</div>

      <div className="oc-panel" style={{ textAlign: 'center', padding: '28px 16px' }}>
        <Button
          appearance="primary"
          size="large"
          onClick={run}
          disabled={busy}
          style={{ fontSize: 18, padding: '14px 48px' }}
        >
          {busy ? '正在体检…' : '开始体检'}
        </Button>
        {result && !busy && (
          <div style={{ marginTop: 18, fontSize: 22, fontWeight: 600 }}>
            {result.healthy
              ? '✅ 一切正常，可以上课'
              : `⚠️ 发现 ${result.total - result.okCount} 项需要注意`}
          </div>
        )}
      </div>

      {busy && (
        <div className="oc-empty">
          <Spinner size="small" label="检查中，请稍候…" />
        </div>
      )}

      {result && !busy && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          {result.items.map((it: any) => (
            <div
              key={it.key}
              style={{ padding: '10px 0', borderBottom: '1px solid rgba(128,128,128,0.15)' }}
            >
              <div style={{ fontSize: 16, fontWeight: 600 }}>
                {it.ok ? '✅' : '⚠️'} {it.name}
              </div>
              <div className="oc-usage-sub" style={{ marginTop: 4 }}>
                {it.detail}
              </div>
              {!it.ok && it.suggest && (
                <div style={{ marginTop: 4, color: '#e0a020' }}>建议：{it.suggest}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
