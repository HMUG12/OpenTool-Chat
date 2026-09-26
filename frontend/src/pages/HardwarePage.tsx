import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Button, Spinner } from '@fluentui/react-components'
import { api } from '../api'

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="oc-info-row">
      <span>{label}</span>
      <span>{value === null || value === undefined || value === '' ? '不可用' : value}</span>
    </div>
  )
}

function formatSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

function formatUptime(seconds: number): string {
  if (!seconds || seconds <= 0) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days} 天 ${hours} 小时 ${minutes} 分`
  if (hours > 0) return `${hours} 小时 ${minutes} 分`
  return `${minutes} 分钟`
}

export default function HardwarePage() {
  const [detail, setDetail] = useState<any>(null)
  const [hardware, setHardware] = useState<any>(null)
  const [metrics, setMetrics] = useState<any>(null)
  const [busy, setBusy] = useState(true)

  const load = async () => {
    setBusy(true)
    try {
      const [d, h, m] = await Promise.all([
        api.get_hardware_detail(),
        api.get_hardware(),
        api.get_metrics(),
      ])
      setDetail(d)
      setHardware(h)
      setMetrics(m)
    } catch {
      setDetail(null)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  // 实时刷新使用率与温度（硬件静态信息不重复采集）
  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        setMetrics(await api.get_metrics())
      } catch {
        /* 忽略单次采样失败 */
      }
    }, 2000)
    return () => window.clearInterval(timer)
  }, [])

  const cpu = hardware?.cpu
  const memory = hardware?.memory
  const cpuTemp = detail?.cpuTemp
  const tempSource = detail?.tempSource

  return (
    <div className="oc-page">
      <div className="oc-page-header">
        <div className="oc-page-title">硬件信息</div>
        <div className="oc-page-desc">
          本机真实硬件状态 · 数据全部实测（读不到的项显示「不可用」，不估算）
          <Button size="small" appearance="secondary" style={{ marginLeft: 10 }} onClick={load} disabled={busy}>
            重新采集
          </Button>
        </div>
      </div>

      {busy && !detail ? (
        <div className="oc-empty">
          <Spinner size="small" label="正在采集硬件信息…（首次约需数秒）" />
        </div>
      ) : (
        <>
          {/* ── CPU ── */}
          <div className="oc-panel">
            <div className="oc-panel-title">处理器（CPU）</div>
            <div className="oc-info-grid" style={{ marginTop: 8 }}>
              <div className="oc-toolcard" style={{ cursor: 'default' }}>
                <Row label="型号" value={cpu?.name} />
                <Row label="核心 / 线程" value={cpu ? `${cpu.cores ?? '—'} 核 / ${cpu.threads ?? '—'} 线程` : null} />
                <Row label="当前频率" value={metrics?.cpu?.freqCurrent ? `${Math.round(metrics.cpu.freqCurrent)} MHz` : null} />
                <Row label="最大频率" value={cpu?.freqMax ? `${Math.round(cpu.freqMax)} MHz` : null} />
                <Row label="架构" value={cpu?.arch} />
                <Row label="实时使用率" value={metrics?.cpu ? `${metrics.cpu.percent}%` : null} />
                <Row
                  label="温度"
                  value={
                    cpuTemp === null || cpuTemp === undefined
                      ? '不可用（需硬件监控驱动，见下方说明）'
                      : `${cpuTemp} ℃${tempSource ? `（来源：${tempSource}）` : ''}`
                  }
                />
              </div>
            </div>
          </div>

          {/* ── 显卡 ── */}
          <div className="oc-panel" style={{ marginTop: 12 }}>
            <div className="oc-panel-title">显卡（GPU）</div>
            <div style={{ marginTop: 8 }}>
              {(detail?.gpus ?? []).length === 0 ? (
                <div className="oc-list-sub">未读取到显卡信息</div>
              ) : (
                (detail.gpus ?? []).map((gpu: any, index: number) => (
                  <div className="oc-toolcard" style={{ cursor: 'default', marginBottom: 8 }} key={index}>
                    <Row label="型号" value={gpu.name} />
                    <Row
                      label="显存"
                      value={gpu.memoryGB ? `${gpu.memoryGB} GB` : '不可用'}
                    />
                    <Row label="驱动版本" value={gpu.driverVersion} />
                    <Row label="驱动日期" value={gpu.driverDate} />
                    <Row label="当前分辨率" value={gpu.resolution} />
                  </div>
                ))
              )}
            </div>
          </div>

          {/* ── 内存 ── */}
          <div className="oc-panel" style={{ marginTop: 12 }}>
            <div className="oc-panel-title">内存（RAM）</div>
            <div className="oc-info-grid" style={{ marginTop: 8 }}>
              <div className="oc-toolcard" style={{ cursor: 'default' }}>
                <Row label="总容量" value={memory ? formatSize(memory.total) : null} />
                <Row
                  label="已使用"
                  value={
                    metrics?.memory
                      ? `${formatSize(metrics.memory.used)}（${metrics.memory.percent}%）`
                      : null
                  }
                />
                <Row label="可用" value={metrics?.memory ? formatSize(metrics.memory.available) : null} />
                {(detail?.memModules ?? []).map((mod: any, index: number) => (
                  <Row
                    key={index}
                    label={`插槽 ${mod.slot || index + 1}`}
                    value={`${mod.capacityGB ?? '—'} GB · ${mod.speed ? mod.speed + ' MHz' : '频率未知'}${
                      mod.manufacturer ? ' · ' + mod.manufacturer : ''
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* ── 硬盘 ── */}
          <div className="oc-panel" style={{ marginTop: 12 }}>
            <div className="oc-panel-title">硬盘（存储）</div>
            <div style={{ marginTop: 8 }}>
              {(detail?.physicalDisks ?? []).length > 0 && (
                <div className="oc-list" style={{ marginBottom: 10 }}>
                  {(detail.physicalDisks ?? []).map((disk: any, index: number) => (
                    <div className="oc-list-row" key={index}>
                      <div className="oc-list-main">
                        <div className="oc-list-title">{disk.model || '未知型号'}</div>
                        <div className="oc-list-sub">
                          {disk.sizeGB ? `${disk.sizeGB} GB` : '容量未知'}
                          {disk.media && disk.media !== '' ? ` · ${disk.media}` : ''}
                          {disk.bus ? ` · ${disk.bus}` : ''}
                          {disk.health ? ` · 健康：${disk.health}` : ''}
                          {` · 温度：${disk.temperature === null || disk.temperature === undefined ? '不可用' : disk.temperature + ' ℃'}`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="oc-list">
                {(hardware?.disks ?? []).map((disk: any) => (
                  <div className="oc-list-row" key={disk.mountpoint}>
                    <div className="oc-list-main">
                      <div className="oc-list-title">{disk.mountpoint}</div>
                      <div className="oc-list-sub">
                        {disk.fstype} · {formatSize(disk.used)} / {formatSize(disk.total)}（{disk.percent}%）
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── 主板 / BIOS ── */}
          <div className="oc-panel" style={{ marginTop: 12 }}>
            <div className="oc-panel-title">主板与 BIOS</div>
            <div className="oc-info-grid" style={{ marginTop: 8 }}>
              <div className="oc-toolcard" style={{ cursor: 'default' }}>
                {(detail?.boards ?? []).map((board: any, index: number) => (
                  <Row
                    key={`b${index}`}
                    label={index === 0 ? '主板' : `主板 ${index + 1}`}
                    value={`${board.manufacturer ?? ''} ${board.product ?? ''}`.trim() || null}
                  />
                ))}
                {(detail?.bios ?? []).map((bios: any, index: number) => (
                  <Row
                    key={`s${index}`}
                    label="BIOS"
                    value={`${bios.vendor ?? ''} ${bios.version ?? ''}${bios.date ? ' · ' + bios.date : ''}`.trim() || null}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* ── 系统 ── */}
          <div className="oc-panel" style={{ marginTop: 12 }}>
            <div className="oc-panel-title">系统</div>
            <div className="oc-info-grid" style={{ marginTop: 8 }}>
              <div className="oc-toolcard" style={{ cursor: 'default' }}>
                <Row
                  label="操作系统"
                  value={hardware?.os ? `${hardware.os.system} ${hardware.os.release}（${hardware.os.build}）` : null}
                />
                <Row label="主机名" value={hardware?.os?.hostname} />
                <Row
                  label="已运行"
                  value={hardware?.bootTime ? formatUptime(Date.now() / 1000 - hardware.bootTime) : null}
                />
              </div>
            </div>
          </div>

          <div style={{ marginTop: 14, fontSize: 12, opacity: 0.55, lineHeight: 1.8 }}>
            说明：CPU / 主板温度依赖硬件监控驱动，Windows 只暴露 ACPI 热区，部分机型读不到属正常现象；
            显存取自驱动在注册表登记的真实容量（避免系统接口对 4GB 以上显存的截断）。
          </div>
        </>
      )}
    </div>
  )
}
