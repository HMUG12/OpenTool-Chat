import { useEffect, useState } from 'react'
import { Button, Input, Textarea, Spinner } from '@fluentui/react-components'
import { api } from '../api'

/** 兼容性知识库：与本机相关的已知问题 + 检索 + 上报 + 累积 */
export default function KbPanel() {
  const [stats, setStats] = useState<any>(null)
  const [matched, setMatched] = useState<any[]>([])
  const [env, setEnv] = useState<any>(null)
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState<any[] | null>(null)
  const [busy, setBusy] = useState(true)
  const [msg, setMsg] = useState('')
  const [openId, setOpenId] = useState('')

  const [desc, setDesc] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', symptom: '', cause: '', solution: '', tags: '' })

  const load = async () => {
    setBusy(true)
    try {
      const [s, m] = await Promise.all([api.kb_stats(), api.kb_match()])
      setStats(s)
      setMatched(m?.items ?? [])
      setEnv(m?.environment ?? null)
    } catch {
      setMatched([])
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const doSearch = async () => {
    setBusy(true)
    setMsg('')
    try {
      setResults(await api.kb_search(keyword))
    } catch {
      setResults([])
    } finally {
      setBusy(false)
    }
  }

  const report = async () => {
    if (!desc.trim()) {
      setMsg('请先用一句话描述问题（例如：投影偶尔黑屏）')
      return
    }
    setBusy(true)
    try {
      const result = await api.kb_export_issue(desc, '课堂问题')
      setMsg(result?.message ?? '')
    } catch (error) {
      setMsg(`导出失败：${error}`)
    } finally {
      setBusy(false)
    }
  }

  const addEntry = async () => {
    if (!form.title.trim()) {
      setMsg('标题不能为空')
      return
    }
    setBusy(true)
    try {
      const result = await api.kb_add(
        form.title,
        form.symptom,
        form.cause,
        form.solution,
        '其他',
        form.tags
      )
      setMsg(result?.message ?? '')
      if (result?.ok) {
        setForm({ title: '', symptom: '', cause: '', solution: '', tags: '' })
        setShowForm(false)
        await load()
      }
    } finally {
      setBusy(false)
    }
  }

  const renderList = (list: any[]) => (
    <div className="oc-list">
      {list.map((entry) => (
        <div className="oc-list-row" key={entry.id}>
          <div className="oc-list-main">
            <div className="oc-list-title">
              <span className="oc-level safe" style={{ marginRight: 8 }}>
                {entry.category || '其他'}
              </span>
              {entry.title}
            </div>
            {(entry.reasons ?? []).length > 0 && (
              <div className="oc-list-sub">与本机相关：{entry.reasons.join('、')}</div>
            )}
            <button
              className="oc-linklike"
              onClick={() => setOpenId(openId === entry.id ? '' : entry.id)}
            >
              {openId === entry.id ? '收起' : '查看症状 / 原因 / 处理办法'}
            </button>
            {openId === entry.id && (
              <div className="oc-hint" style={{ marginTop: 6 }}>
                <b>症状：</b>
                {entry.symptom || '—'}
                <br />
                <b>原因：</b>
                {entry.cause || '—'}
                <br />
                <b>处理：</b>
                {entry.solution || '—'}
                <br />
                <span style={{ opacity: 0.6 }}>
                  来源：{entry.source || '—'}
                  {entry.origin === 'local' ? ' · 本机累积' : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )

  return (
    <>
      <div className="oc-panel">
        <div className="oc-panel-title">
          已知问题（与本机相关）
          <span className="oc-list-sub" style={{ marginLeft: 8, fontWeight: 400 }}>
            知识库 {stats?.version ?? '—'} · 内置 {stats?.builtin ?? 0} 条 · 本地累积{' '}
            {stats?.local ?? 0} 条
          </span>
        </div>
        {env && (
          <div className="oc-hint" style={{ marginBottom: 8 }}>
            本机环境：{env.os} · 已装教学软件 {(env.apps ?? []).length} 个 · 触摸
            {env.flags?.touch ? '支持' : '未检测到'} · 无线投屏
            {env.flags?.wireless ? '支持' : '不支持'} · 还原保护
            {env.flags?.restoreGuard ? '有' : '无'}
          </div>
        )}
        {busy && matched.length === 0 ? (
          <div className="oc-hint">
            <Spinner size="tiny" /> 正在匹配本机环境…
          </div>
        ) : matched.length === 0 ? (
          <div className="oc-hint">
            暂未匹配到与这台机器直接相关的条目。可以用下面的搜索框按关键词查找
            （如「投屏」「触摸」「卡顿」）。
          </div>
        ) : (
          renderList(matched)
        )}
      </div>

      <div className="oc-panel" style={{ marginTop: 12 }}>
        <div className="oc-panel-title">按关键词查</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Input
            value={keyword}
            placeholder="例如：投屏 / 触摸 / 没声音 / 闪退"
            onChange={(_e, data) => setKeyword(data.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void doSearch()
            }}
            style={{ flex: 1 }}
          />
          <Button appearance="secondary" onClick={() => void doSearch()} disabled={busy}>
            搜索
          </Button>
          {results !== null && (
            <Button
              appearance="transparent"
              onClick={() => {
                setResults(null)
                setKeyword('')
              }}
            >
              清除
            </Button>
          )}
        </div>
        {results !== null &&
          (results.length === 0 ? (
            <div className="oc-hint" style={{ marginTop: 8 }}>
              没有找到相关条目。如果这个问题你确认过原因和处理办法，可以记到下面，
              以后所有机器都能用到。
            </div>
          ) : (
            <div style={{ marginTop: 8 }}>{renderList(results)}</div>
          ))}
      </div>

      <div className="oc-panel" style={{ marginTop: 12 }}>
        <div className="oc-panel-title">上报问题 / 记录经验</div>
        <div className="oc-hint" style={{ marginBottom: 8 }}>
          上报会导出一个个人的问题报告（只包含系统版本、已装软件等环境信息，不含课件与个人文件），
          可以发给维护者或贴到群里；记录经验则会存进本机知识库，之后可导出分享给别人。
        </div>
        <Textarea
          value={desc}
          placeholder="一句话描述遇到的问题，例如：希沃白板打开课件后闪退"
          onChange={(_e, data) => setDesc(data.value)}
          resize="vertical"
        />
        <div className="oc-actions" style={{ marginTop: 8 }}>
          <Button appearance="primary" onClick={() => void report()} disabled={busy}>
            导出问题报告
          </Button>
          <Button appearance="secondary" onClick={() => setShowForm(!showForm)} disabled={busy}>
            {showForm ? '收起经验表单' : '记录一条经验'}
          </Button>
        </div>

        {showForm && (
          <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
            <Input
              placeholder="标题（必填），例如：OPS 升级 BIOS 后触摸需重新校准"
              value={form.title}
              onChange={(_e, d) => setForm({ ...form, title: d.value })}
            />
            <Input
              placeholder="症状：什么现象"
              value={form.symptom}
              onChange={(_e, d) => setForm({ ...form, symptom: d.value })}
            />
            <Input
              placeholder="原因：为什么"
              value={form.cause}
              onChange={(_e, d) => setForm({ ...form, cause: d.value })}
            />
            <Input
              placeholder="处理办法"
              value={form.solution}
              onChange={(_e, d) => setForm({ ...form, solution: d.value })}
            />
            <Input
              placeholder="标签，逗号分隔（如：触摸, 校准）"
              value={form.tags}
              onChange={(_e, d) => setForm({ ...form, tags: d.value })}
            />
            <div>
              <Button appearance="primary" onClick={() => void addEntry()} disabled={busy}>
                存进知识库
              </Button>
            </div>
          </div>
        )}

        {msg && (
          <div className="oc-hint" style={{ marginTop: 8 }}>
            {msg}
          </div>
        )}
      </div>
    </>
  )
}
