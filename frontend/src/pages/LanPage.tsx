import { useEffect, useState } from 'react'
import { Button, Input, Spinner } from '@fluentui/react-components'
import { api } from '../api'

const ACTION_GROUPS: { id: string; label: string; payload?: () => any }[] = [
  { id: 'checkup', label: '一键体检' },
  { id: 'repair', label: '一键修复' },
  { id: 'cleanup', label: '磁盘清理' },
]

function levelClass(value: number | undefined): string {
  if (value === undefined || value === null) return ''
  if (value >= 88) return 'warn'
  if (value >= 70) return 'warn'
  return ''
}

function MiniBar({ label, percent }: { label: string; percent?: number }) {
  const value = typeof percent === 'number' ? Math.max(0, Math.min(100, percent)) : null
  return (
    <div style={{ minWidth: 92 }}>
      <div className="oc-list-sub" style={{ marginBottom: 3 }}>
        {label} {value === null ? '—' : `${value}%`}
      </div>
      <div className="oc-usage-track">
        <div
          className={`oc-usage-fill ${value !== null && value >= 88 ? 'crit' : levelClass(value ?? undefined)}`}
          style={{ width: `${value ?? 0}%` }}
        />
      </div>
    </div>
  )
}

function formatTime(ts?: number): string {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    return '—'
  }
}

export default function LanPage() {
  const [status, setStatus] = useState<any>(null)
  const [nodes, setNodes] = useState<any[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(true)

  const [scanResult, setScanResult] = useState<any[]>([])
  const [scanning, setScanning] = useState(false)
  const [serverUrl, setServerUrl] = useState('')
  const [code, setCode] = useState('')
  const [messageText, setMessageText] = useState('')

  const notify = (text: string) => {
    setMsg(text)
    window.setTimeout(() => setMsg(''), 4000)
  }

  const load = async (silent = false) => {
    if (!silent) setBusy(true)
    try {
      const [s, n, e] = await Promise.all([
        api.lan_status(),
        api.lan_nodes(),
        api.lan_events(60),
      ])
      setStatus(s)
      setNodes(n ?? [])
      setEvents(e ?? [])
    } catch {
      /* 首次读取失败保持空态 */
    } finally {
      if (!silent) setBusy(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  // 学生机心跳是 5 秒，这里 3 秒拉一次保证列表"活"
  useEffect(() => {
    const timer = window.setInterval(() => void load(true), 3000)
    return () => window.clearInterval(timer)
  }, [])

  const mode = status?.mode ?? 'single'
  const server = status?.server
  const client = status?.client
  const onlineNodes = nodes.filter((node) => node.online)

  const startServer = async () => {
    const result = await api.lan_start_server(38900)
    notify(result?.message ?? '')
    await load(true)
  }

  const stopServer = async () => {
    const result = await api.lan_stop_server()
    notify(result?.message ?? '')
    await load(true)
  }

  const resetCode = async () => {
    const value = await api.lan_reset_code()
    notify(`新的配对码：${value}`)
    await load(true)
  }

  const sendAction = async (action: string, payload?: any) => {
    if (!selected.length) {
      notify('请先勾选要操作的设备')
      return
    }
    const result = await api.lan_send(selected, action, payload ?? {})
    notify(result?.message ?? '')
    await load(true)
  }

  const doScan = async () => {
    setScanning(true)
    try {
      const found = await api.lan_scan()
      setScanResult(found ?? [])
      notify(found?.length ? `发现 ${found.length} 台老师机` : '未发现老师机')
    } finally {
      setScanning(false)
    }
  }

  const join = async (url = '') => {
    const target = url || serverUrl
    if (!code.trim()) {
      notify('请填写老师机上显示的 6 位配对码')
      return
    }
    const result = await api.lan_join(target, code.trim())
    notify(result?.message ?? '')
    await load(true)
  }

  const leave = async () => {
    const result = await api.lan_leave()
    notify(result?.message ?? '')
    await load(true)
  }

  const toggleSelect = (id: string) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))
  }

  const toggleAll = () => {
    setSelected(selected.length === nodes.length ? [] : nodes.map((node) => node.id))
  }

  const removeNode = async (id: string) => {
    const result = await api.lan_remove_node(id)
    notify(result?.message ?? '')
    setSelected((prev) => prev.filter((item) => item !== id))
    await load(true)
  }

  return (
    <div className="oc-page">
      <div className="oc-page-header">
        <div>
          <div className="oc-page-title">机房管理</div>
          <div className="oc-page-desc">
            局域网内一台老师机管理所有学生机 · 无需服务器，点对点直连
          </div>
        </div>
        <div className="oc-device">
          <div className="oc-device-model">
            {mode === 'teacher' ? '老师机模式' : mode === 'student' ? '学生机模式' : '单机模式'}
          </div>
          <div className="oc-device-sub">
            {mode === 'teacher'
              ? `在线 ${server?.onlineCount ?? 0} / 共 ${server?.nodeCount ?? 0} 台`
              : mode === 'student'
                ? (client?.message ?? '')
                : '未启用机房协同'}
          </div>
        </div>
      </div>

      {/* ── 老师机面板 ── */}
      <div className="oc-panel">
        <div className="oc-panel-title">老师机（管理端）</div>
        {server?.running ? (
          <>
            <div className="oc-stats" style={{ marginTop: 8 }}>
              <div className="oc-stat">
                <div className="oc-stat-value">{server.pairingCode}</div>
                <div className="oc-stat-label">配对码（学生机输入）</div>
              </div>
              <div className="oc-stat">
                <div className="oc-stat-value">{server.onlineCount ?? 0}</div>
                <div className="oc-stat-label">在线设备</div>
              </div>
              <div className="oc-stat">
                <div className="oc-stat-value">{server.nodeCount ?? 0}</div>
                <div className="oc-stat-label">已配对数</div>
              </div>
              <div className="oc-stat">
                <div className="oc-stat-value">{server.port}</div>
                <div className="oc-stat-label">服务端口</div>
              </div>
            </div>
            <div className="oc-actions" style={{ marginTop: 12 }}>
              <Button appearance="secondary" onClick={resetCode}>
                重置配对码
              </Button>
              <Button appearance="secondary" onClick={stopServer}>
                停止服务
              </Button>
            </div>
          </>
        ) : (
          <div style={{ marginTop: 8 }}>
            <div className="oc-hint">
              启动后本机成为老师机：学生机会自动发现你（或手动填写本机 IP），
              输入配对码即可加入管理。
            </div>
            <Button appearance="primary" style={{ marginTop: 10 }} onClick={startServer}>
              启动管理服务
            </Button>
          </div>
        )}
      </div>

      {/* ── 学生机面板 ── */}
      {mode !== 'teacher' && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">学生机（加入老师机）</div>
          {client?.state === 'connected' ? (
            <>
              <div className="oc-list-sub" style={{ marginTop: 6 }}>
                已连接：{client.teacher}（{client.server}）· 节点 ID {client.nodeId}
              </div>
              <div className="oc-list-sub">最近上报：{formatTime(client.lastReport)}</div>
              <div className="oc-actions" style={{ marginTop: 10 }}>
                <Button appearance="secondary" onClick={leave}>
                  断开连接
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="oc-searchbar" style={{ marginTop: 8, marginBottom: 8 }}>
                <Button appearance="secondary" onClick={doScan} disabled={scanning}>
                  {scanning ? '搜索中…' : '搜索老师机'}
                </Button>
                {scanResult.length > 0 && (
                  <span className="oc-list-sub">发现 {scanResult.length} 台，点击即填入</span>
                )}
              </div>
              {scanResult.length > 0 && (
                <div className="oc-list" style={{ marginBottom: 8 }}>
                  {scanResult.map((item) => (
                    <div className="oc-list-row" key={item.ip}>
                      <div className="oc-list-main">
                        <div className="oc-list-title">{item.name || item.ip}</div>
                        <div className="oc-list-sub">
                          {item.ip}:{item.httpPort ?? 38900}
                        </div>
                      </div>
                      <Button
                        size="small"
                        onClick={() => {
                          setServerUrl(`http://${item.ip}:${item.httpPort ?? 38900}`)
                          void join(`http://${item.ip}:${item.httpPort ?? 38900}`)
                        }}
                      >
                        连接
                      </Button>
                    </div>
                  ))}
                </div>
              )}
              <div className="oc-searchbar">
                <Input
                  value={serverUrl}
                  onChange={(_e, data) => setServerUrl(data.value)}
                  placeholder="老师机地址（可留空：自动发现）"
                  style={{ flex: 1 }}
                />
                <Input
                  value={code}
                  onChange={(_e, data) => setCode(data.value)}
                  placeholder="6 位配对码"
                  style={{ width: 140 }}
                />
                <Button appearance="primary" onClick={() => void join()}>
                  加入
                </Button>
                {client?.enabled && (
                  <Button appearance="secondary" onClick={leave}>
                    停止
                  </Button>
                )}
              </div>
              {client?.message && (
                <div className="oc-list-sub" style={{ marginTop: 8 }}>
                  状态：{client.message}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {msg && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-list-sub">{msg}</div>
        </div>
      )}

      {/* ── 在线设备 ── */}
      {server?.running && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">
            在线设备（{onlineNodes.length} / {nodes.length}）
            <Button
              size="small"
              appearance="secondary"
              style={{ marginLeft: 10 }}
              onClick={toggleAll}
              disabled={nodes.length === 0}
            >
              {selected.length === nodes.length && nodes.length > 0 ? '取消全选' : '全选'}
            </Button>
          </div>

          {nodes.length === 0 ? (
            <div className="oc-hint" style={{ marginTop: 6 }}>
              还没有学生机加入。请让学生机打开本程序 →「机房管理」→ 填入配对码{' '}
              {server?.pairingCode ?? ''} 加入。
            </div>
          ) : (
            <div className="oc-toolgrid" style={{ marginTop: 10 }}>
              {nodes.map((node) => (
                <div
                  className="oc-toolcard"
                  key={node.id}
                  style={{
                    cursor: 'pointer',
                    borderColor: selected.includes(node.id) ? 'var(--oc-accent)' : undefined,
                    opacity: node.online ? 1 : 0.55,
                  }}
                  onClick={() => toggleSelect(node.id)}
                >
                  <div className="oc-toolcard-top">
                    <input
                      type="checkbox"
                      checked={selected.includes(node.id)}
                      onChange={() => toggleSelect(node.id)}
                      onClick={(event) => event.stopPropagation()}
                    />
                    <div className="oc-toolcard-head">
                      <div className="oc-toolcard-name">{node.name}</div>
                      <div className="oc-toolcard-meta">
                        {node.ip} · {node.online ? '在线' : `离线（${formatTime(node.lastSeen)}）`}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    <MiniBar label="CPU" percent={node.info?.cpu} />
                    <MiniBar label="内存" percent={node.info?.memory} />
                    <MiniBar label="磁盘" percent={node.info?.disk} />
                  </div>
                  <div className="oc-list-sub">
                    {node.info?.user ? `${node.info.user} · ` : ''}
                    {node.info?.model || node.info?.os || ''}
                    {node.info?.foreground ? ` · 前台：${node.info.foreground}` : ''}
                  </div>
                  <div className="oc-actions">
                    <Button
                      size="small"
                      appearance="subtle"
                      onClick={(event) => {
                        event.stopPropagation()
                        void removeNode(node.id)
                      }}
                    >
                      移除
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {nodes.length > 0 && (
            <div className="oc-actions" style={{ marginTop: 12 }}>
              {ACTION_GROUPS.map((item) => (
                <Button key={item.id} appearance="secondary" onClick={() => void sendAction(item.id)}>
                  {item.label}
                </Button>
              ))}
              <Button
                appearance="secondary"
                onClick={() => void sendAction('power', { mode: 'lock' })}
              >
                锁屏
              </Button>
              <Button
                appearance="secondary"
                onClick={() => void sendAction('power', { mode: 'restart', delay: 30 })}
              >
                重启（30 秒）
              </Button>
              <Button
                appearance="secondary"
                onClick={() => void sendAction('power', { mode: 'shutdown', delay: 30 })}
              >
                关机（30 秒）
              </Button>
            </div>
          )}

          {nodes.length > 0 && (
            <div className="oc-searchbar" style={{ marginTop: 10 }}>
              <Input
                value={messageText}
                onChange={(_e, data) => setMessageText(data.value)}
                placeholder="要在学生机弹出的消息内容"
                style={{ flex: 1 }}
              />
              <Button
                appearance="secondary"
                onClick={() => {
                  if (!messageText.trim()) {
                    notify('请先输入消息内容')
                    return
                  }
                  void sendAction('message', { text: messageText.trim() })
                }}
              >
                发送消息
              </Button>
            </div>
          )}
        </div>
      )}

      {/* ── 事件日志 ── */}
      {server?.running && (
        <div className="oc-panel" style={{ marginTop: 12 }}>
          <div className="oc-panel-title">操作日志（{events.length}）</div>
          {events.length === 0 ? (
            <div className="oc-hint">还没有操作记录。</div>
          ) : (
            <div className="oc-list oc-scroll">
              {events.map((item, index) => (
                <div className="oc-list-row" key={index}>
                  <div className="oc-list-main">
                    <div className="oc-list-title">
                      <span className={`oc-level ${item.ok ? 'safe' : 'danger'}`}>
                        {item.ok ? '成功' : '失败'}
                      </span>
                      <span style={{ marginLeft: 8 }}>
                        {item.nodeName || '系统'} · {item.action}
                      </span>
                    </div>
                    <div className="oc-list-sub">
                      {formatTime(item.ts)} · {item.detail} {item.message ? `· ${item.message}` : ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {busy && !status && (
        <div className="oc-empty">
          <Spinner size="small" label="读取机房状态…" />
        </div>
      )}
    </div>
  )
}
