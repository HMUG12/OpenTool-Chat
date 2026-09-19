import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from '@fluentui/react-components'
import UsageBar from '../components/UsageBar'
import SparkLine from '../components/SparkLine'
import { api } from '../api'
import { formatBytes, formatDateTime, formatFrequency, formatRate, formatUptime } from '../format'
import type { HardwareInfo, IpInfo, Metrics, NetworkInfo, PublicIpResult } from '../types'

const DOWN_COLOR = '#0f6cbd'
const UP_COLOR = '#0e700e'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </>
  )
}

export default function DashboardPage() {
  const [hardware, setHardware] = useState<HardwareInfo | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [network, setNetwork] = useState<NetworkInfo | null>(null)
  const [ip, setIp] = useState<IpInfo | null>(null)
  const [publicIp, setPublicIp] = useState<PublicIpResult | null>(null)
  const [querying, setQuerying] = useState(false)

  // 静态信息与网络拓扑：加载一次即可
  useEffect(() => {
    void (async () => {
      const [hw, net, ipInfo] = await Promise.all([
        api.get_hardware(),
        api.get_network(),
        api.get_ip(),
      ])
      setHardware(hw)
      setNetwork(net)
      setIp(ipInfo)
    })()
  }, [])

  // 实时指标：1 秒轮询读取后端采样快照
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const snapshot = await api.get_metrics()
        if (alive) setMetrics(snapshot)
      } catch {
        // 采样失败保持上一次数据，不影响展示
      }
    }
    void tick()
    const timer = window.setInterval(tick, 1000)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [])

  const queryPublicIp = useCallback(async () => {
    setQuerying(true)
    try {
      setPublicIp(await api.query_public_ip())
    } finally {
      setQuerying(false)
    }
  }, [])

  const down = formatRate(metrics?.network.download ?? 0)
  const up = formatRate(metrics?.network.upload ?? 0)
  const history = metrics?.history ?? []
  const axisMax = Math.max(...history.map((p) => Math.max(p.download, p.upload)), 1)

  const primaryDisk = hardware?.disks.find((d) => d.percent !== undefined) ?? hardware?.disks[0]
  const uptime = hardware ? Date.now() / 1000 - hardware.bootTime : 0

  if (!hardware || !metrics) {
    return (
      <div className="oc-page">
        <div className="oc-empty">正在采集系统状态…</div>
      </div>
    )
  }

  return (
    <div className="oc-page">
      <div className="oc-page-header">
        <div className="oc-page-title">系统状态</div>
        <div className="oc-page-desc">
          {hardware.os.system} {hardware.os.release}
          {hardware.os.build ? ` · 内部版本 ${hardware.os.build}` : ''} · 已运行 {formatUptime(uptime)}
        </div>
      </div>

      {/* ── 核心资源 ── */}
      <div className="oc-grid oc-grid-3" style={{ marginBottom: 12 }}>
        <div className="oc-panel">
          <div className="oc-panel-title">处理器</div>
          <UsageBar
            label="使用率"
            percent={metrics.cpu.percent}
            value={`${metrics.cpu.percent.toFixed(1)}%`}
            sub={`${hardware.cpu.threads ?? '-'} 线程 · ${formatFrequency(metrics.cpu.freqCurrent)}`}
          />
        </div>

        <div className="oc-panel">
          <div className="oc-panel-title">内存</div>
          <UsageBar
            label="已用"
            percent={metrics.memory.percent}
            value={`${metrics.memory.percent.toFixed(1)}%`}
            sub={`${formatBytes(metrics.memory.used)} / ${formatBytes(metrics.memory.total)}`}
          />
        </div>

        <div className="oc-panel">
          <div className="oc-panel-title">存储</div>
          {primaryDisk ? (
            <UsageBar
              label={primaryDisk.device}
              percent={primaryDisk.percent}
              value={`${primaryDisk.percent.toFixed(1)}%`}
              sub={`${formatBytes(primaryDisk.used)} / ${formatBytes(primaryDisk.total)} · ${primaryDisk.fstype}`}
            />
          ) : (
            <div className="oc-usage-sub">未检测到磁盘分区</div>
          )}
        </div>
      </div>

      {/* ── 网络实时 + IP ── */}
      <div className="oc-grid oc-grid-2" style={{ marginBottom: 12 }}>
        <div className="oc-panel">
          <div className="oc-panel-title">网络实时速率</div>
          <div className="oc-rate">
            <div className="oc-rate-item">
              <span className="oc-rate-label">
                <span className="oc-dot" style={{ background: DOWN_COLOR }} /> 下行
              </span>
              <span className="oc-rate-value">
                {down.value}
                <span className="oc-rate-unit">{down.unit}</span>
              </span>
            </div>
            <div className="oc-rate-item">
              <span className="oc-rate-label">
                <span className="oc-dot" style={{ background: UP_COLOR }} /> 上行
              </span>
              <span className="oc-rate-value">
                {up.value}
                <span className="oc-rate-unit">{up.unit}</span>
              </span>
            </div>
          </div>

          <div style={{ position: 'relative', height: 60 }}>
            <div style={{ position: 'absolute', inset: 0 }}>
              <SparkLine data={history.map((p) => p.download)} color={DOWN_COLOR} max={axisMax} />
            </div>
            <div style={{ position: 'absolute', inset: 0 }}>
              <SparkLine data={history.map((p) => p.upload)} color={UP_COLOR} max={axisMax} />
            </div>
          </div>

          <div className="oc-usage-sub" style={{ marginTop: 6 }}>
            累计 接收 {formatBytes(metrics.network.totalRecv)} / 发送 {formatBytes(metrics.network.totalSent)}
          </div>
        </div>

        <div className="oc-panel">
          <div className="oc-panel-title">IP 地址</div>
          <dl className="oc-kv">
            <Row label="主机名">{ip?.hostname ?? hardware.os.hostname}</Row>
            <Row label="局域网 IP">
              <span className="oc-mono">{ip?.local ?? '-'}</span>
            </Row>
            <Row label="默认网关">
              <span className="oc-mono">{network?.topology.gateways[0] ?? '-'}</span>
            </Row>
            <Row label="DNS">
              <span className="oc-mono">{network?.topology.dnsServers.join(' / ') || '-'}</span>
            </Row>
            <Row label="公网 IP">
              {publicIp ? (
                publicIp.reachable ? (
                  <span className="oc-mono">{publicIp.ip}</span>
                ) : (
                  <span style={{ opacity: 0.6 }}>未获取到（离线或全部源超时）</span>
                )
              ) : (
                <span style={{ opacity: 0.6 }}>未查询</span>
              )}
            </Row>
          </dl>

          <Button
            size="small"
            appearance="secondary"
            disabled={querying}
            onClick={() => void queryPublicIp()}
            style={{ marginTop: 10 }}
          >
            {querying ? '查询中…' : publicIp?.queried === false || publicIp === null ? '查询公网 IP' : '重新查询'}
          </Button>

          {publicIp?.reachable && publicIp.source && (
            <div className="oc-usage-sub" style={{ marginTop: 6 }}>
              数据来源：{publicIp.source}
            </div>
          )}
        </div>
      </div>

      {/* ── 硬件明细 ── */}
      <div className="oc-grid oc-grid-2" style={{ marginBottom: 12 }}>
        <div className="oc-panel">
          <div className="oc-panel-title">处理器与主板</div>
          <dl className="oc-kv">
            <Row label="型号">{hardware.cpu.name}</Row>
            <Row label="核心 / 线程">
              {hardware.cpu.cores ?? '-'}C / {hardware.cpu.threads ?? '-'}T
            </Row>
            <Row label="基准频率">{formatFrequency(hardware.cpu.freqMax)}</Row>
            <Row label="当前频率">{formatFrequency(metrics.cpu.freqCurrent)}</Row>
            <Row label="架构">{hardware.cpu.arch}</Row>
            <Row label="主板">
              {hardware.boards[0]
                ? `${hardware.boards[0].manufacturer ?? ''} ${hardware.boards[0].product ?? ''}`.trim() || '-'
                : '-'}
            </Row>
            <Row label="启动时间">{formatDateTime(hardware.bootTime)}</Row>
          </dl>
        </div>

        <div className="oc-panel">
          <div className="oc-panel-title">显示适配器</div>
          {hardware.gpus.length === 0 ? (
            <div className="oc-usage-sub">未检测到</div>
          ) : (
            <dl className="oc-kv">
              {hardware.gpus.map((gpu, index) => (
                <Row key={`${gpu.name}-${index}`} label={index === 0 ? '设备' : ''}>
                  <div>{gpu.name || '未知'}</div>
                  <div className="oc-usage-sub">
                    {gpu.memoryGB ? `显存 ${gpu.memoryGB} GB` : ''}
                    {gpu.driverVersion ? ` · 驱动 ${gpu.driverVersion}` : ''}
                  </div>
                </Row>
              ))}
            </dl>
          )}
        </div>
      </div>

      {/* ── 磁盘分区 ── */}
      {hardware.disks.length > 0 && (
        <div className="oc-panel" style={{ marginBottom: 12 }}>
          <div className="oc-panel-title">磁盘分区</div>
          <div className="oc-grid oc-grid-2">
            {hardware.disks.map((disk) => (
              <UsageBar
                key={disk.device}
                label={`${disk.device}  ${disk.mountpoint}`}
                percent={disk.percent}
                value={`${disk.percent.toFixed(1)}%`}
                sub={`${formatBytes(disk.used)} / ${formatBytes(disk.total)} · ${disk.fstype}`}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── 网卡 ── */}
      {network && (
        <div className="oc-panel">
          <div className="oc-panel-title">网络接口</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ textAlign: 'left', opacity: 0.6 }}>
                  <th style={{ padding: '4px 8px 6px 0', fontWeight: 500 }}>名称</th>
                  <th style={{ padding: '4px 8px 6px', fontWeight: 500 }}>IPv4</th>
                  <th style={{ padding: '4px 8px 6px', fontWeight: 500 }}>MAC</th>
                  <th style={{ padding: '4px 8px 6px', fontWeight: 500 }}>速率</th>
                  <th style={{ padding: '4px 8px 6px', fontWeight: 500 }}>接收 / 发送</th>
                  <th style={{ padding: '4px 8px 6px', fontWeight: 500 }}>状态</th>
                </tr>
              </thead>
              <tbody>
                {network.interfaces.map((iface) => (
                  <tr key={iface.name} style={{ borderTop: '1px solid var(--oc-border)' }}>
                    <td style={{ padding: '5px 8px 5px 0' }}>{iface.name}</td>
                    <td style={{ padding: '5px 8px' }} className="oc-mono">
                      {iface.ipv4.map((a) => a.address).join(', ') || '-'}
                    </td>
                    <td style={{ padding: '5px 8px' }} className="oc-mono">
                      {iface.mac || '-'}
                    </td>
                    <td style={{ padding: '5px 8px' }} className="oc-mono">
                      {iface.speedMbps ? `${iface.speedMbps} Mbps` : '-'}
                    </td>
                    <td style={{ padding: '5px 8px' }} className="oc-mono">
                      {formatBytes(iface.bytesRecv)} / {formatBytes(iface.bytesSent)}
                    </td>
                    <td style={{ padding: '5px 8px' }}>
                      <span className={`oc-chip ${iface.up ? 'external' : ''}`}>
                        {iface.up ? '已连接' : '断开'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
