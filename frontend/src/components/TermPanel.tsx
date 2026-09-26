import { useEffect, useState } from 'react'
import { Button, Input, Spinner } from '@fluentui/react-components'
import { api } from '../api'

/** 学期模式（开学 / 考试 / 假期）+ 配置模板 */
export default function TermPanel() {
  const [modes, setModes] = useState<any[]>([])
  const [mode, setMode] = useState('term_start')
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        const list = await api.term_modes()
        setModes(list ?? [])
        if (list?.[0]) setMode(list[0].id)
      } catch {
        /* 开发模式下忽略 */
      }
    })()
  }, [])

  const run = async (target = mode) => {
    setBusy(true)
    setMsg('')
    try {
      setResult(await api.run_term_mode(target))
    } catch (error) {
      setMsg(`检查失败：${error}`)
    } finally {
      setBusy(false)
    }
  }

  const exportReport = async () => {
    setBusy(true)
    setMsg('')
    try {
      const r = await api.export_mode_report(mode)
      setMsg(r?.message ?? '')
    } catch (error) {
      setMsg(`导出失败：${error}`)
    } finally {
      setBusy(false)
    }
  }

  const exportProfile = async () => {
    setBusy(true)
    setMsg('')
    try {
      const r = await api.export_profile(note)
      setMsg(r?.message ?? '')
    } catch (error) {
      setMsg(`导出失败：${error}`)
    } finally {
      setBusy(false)
    }
  }

  const importProfile = async () => {
    setBusy(true)
    setMsg('')
    try {
      const picked = await api.pick_profile_file()
      if (!picked?.ok) {
        setMsg(picked?.message ?? '未选择文件')
        return
      }
      const r = await api.import_profile(picked.path)
      setMsg(r?.message ?? '')
    } catch (error) {
      setMsg(`导入失败：${error}`)
    } finally {
      setBusy(false)
    }
  }

  const current = modes.find((m) => m.id === mode)
  const items: any[] = result?.items ?? []
  const problems = items.filter((i) => !i.ok)

  return (
    <>
      <div className="oc-panel">
        <div className="oc-panel-title">按学期节点检查</div>
        <div className="oc-actions" style={{ flexWrap: 'wrap' }}>
          {modes.map((m) => (
            <Button
              key={m.id}
              appearance={m.id === mode ? 'primary' : 'secondary'}
              onClick={() => {
                setMode(m.id)
                setResult(null)
                void run(m.id)
              }}
              disabled={busy}
            >
              {m.name}
            </Button>
          ))}
          <Button appearance="secondary" onClick={() => void run()} disabled={busy}>
            {busy ? '检查中…' : '重新检查'}
          </Button>
          <Button appearance="secondary" onClick={() => void exportReport()} disabled={busy}>
            导出报告到桌面
          </Button>
        </div>
        {current && (
          <div className="oc-hint" style={{ marginTop: 10 }}>
            {current.desc}
          </div>
        )}
        {msg && (
          <div className="oc-hint" style={{ marginTop: 8 }}>
            {msg}
          </div>
        )}
      </div>

      {busy && items.length === 0 && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <Spinner size="tiny" /> 正在检查…
        </div>
      )}

      {items.length > 0 && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">
            检查结果
            <span className="oc-list-sub" style={{ marginLeft: 8, fontWeight: 400 }}>
              {result.okCount}/{result.total} 项通过
              {problems.length > 0 ? ` · ${problems.length} 项待处理` : ' · 全部通过'}
            </span>
          </div>
          <div className="oc-list">
            {items.map((item) => (
              <div className="oc-list-row" key={item.key}>
                <span
                  style={{
                    width: 9,
                    height: 9,
                    borderRadius: '50%',
                    flex: '0 0 auto',
                    marginTop: 6,
                    background: item.ok ? 'var(--oc-positive)' : 'var(--oc-warning)',
                  }}
                />
                <div className="oc-list-main">
                  <div className="oc-list-title">{item.name}</div>
                  <div className="oc-list-sub">{item.detail}</div>
                  {item.suggest && <div className="oc-list-warn">{item.suggest}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="oc-panel" style={{ marginTop: 12 }}>
        <div className="oc-panel-title">配置模板（多台机器配置一致）</div>
        <div className="oc-hint" style={{ marginBottom: 10 }}>
          在这台机器上调好外观、关闭行为、安全监控、壁纸样式与机房参数后导出成
          <b> .ocbprofile </b>
          文件；其他机器导入即可套用同一套配置（不含机器专属路径与个人文件）。
        </div>
        <Input
          value={note}
          placeholder="备注（可选），例如：三年级 2 班标准机"
          onChange={(_e, data) => setNote(data.value)}
          style={{ width: '100%', maxWidth: 420 }}
        />
        <div className="oc-actions" style={{ marginTop: 10 }}>
          <Button appearance="primary" onClick={() => void exportProfile()} disabled={busy}>
            导出配置模板
          </Button>
          <Button appearance="secondary" onClick={() => void importProfile()} disabled={busy}>
            导入配置模板
          </Button>
        </div>
      </div>
    </>
  )
}
