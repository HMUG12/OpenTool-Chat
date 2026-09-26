import { useMemo, useState } from 'react'
import { Button, Spinner } from '@fluentui/react-components'
import { api } from '../api'
import type { AppInfo } from '../types'

export default function AboutPage({ toolCount }: { toolCount: number }) {
  const [info, setInfo] = useState<AppInfo | null>(null)

  useMemo(() => {
    void api.get_info().then(setInfo)
  }, [])

  const rows: [string, string][] = info
    ? [
        ['版本', info.version],
        ['作者', info.author],
        ['运行环境', `Python ${info.pythonVersion} · ${info.platform}`],
        ['便携模式', info.portable ? '是（跟随程序目录）' : '否'],
        ['程序根目录', info.rootDir],
        ['工具目录', info.toolDir],
        ['已收录工具', `${toolCount} 个`],
      ]
    : []

  return (
    <div className="oc-page">
      <div className="oc-page-header">
        <div className="oc-page-title">关于 OpenClass-Box</div>
        <div className="oc-page-desc">{info?.description ?? '开源实用工具箱'}</div>
      </div>

      {!info ? (
        <div className="oc-empty">
          <Spinner size="small" label="读取中…" />
        </div>
      ) : (
        <>
          <div className="oc-info-grid">
            <div className="oc-toolcard" style={{ cursor: 'default' }}>
              {rows.map(([k, v]) => (
                <div className="oc-info-row" key={k}>
                  <span>{k}</span>
                  <span>{v}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 22, display: 'flex', gap: 10 }}>
            <Button
              appearance="primary"
              onClick={() => void api.open_url('https://github.com/HMUG12/OpenClass-Box')}
            >
              项目仓库
            </Button>
            <Button
              appearance="secondary"
              onClick={() => void api.open_url('https://github.com/HMUG12/OpenClass-Box/releases')}
            >
              版本发布
            </Button>
            <Button
              appearance="secondary"
              onClick={() => void api.open_url('https://hypomux.com/')}
            >
              UI 设计参考
            </Button>
          </div>

          {/* ── 赞助支持 ── */}
          <div className="oc-panel" style={{ marginTop: 20 }}>
            <div className="oc-panel-title">赞助支持</div>
            <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <img
                src="./reward.png"
                alt="赞助码"
                style={{
                  width: 196,
                  borderRadius: 10,
                  border: '1px solid var(--oc-border)',
                  background: '#fff',
                  padding: 6,
                }}
                onError={(event) => {
                  // 未随包携带赞助码时优雅隐藏，只保留文字说明
                  ;(event.currentTarget as HTMLImageElement).style.display = 'none'
                }}
              />
              <div style={{ flex: 1, minWidth: 220 }}>
                <div style={{ fontSize: 15, fontWeight: 650, marginBottom: 8 }}>
                  如果软件不错，欢迎赞助
                </div>
                <div className="oc-hint">
                  赞助完全自愿，不影响任何功能，也不提供额外特权。
                  你的支持会用于持续开发、更多机型的适配测试，
                  以及后续正式代码签名证书的费用。
                </div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 22, fontSize: 12, opacity: 0.5, lineHeight: 1.7 }}>
            交流群（QQ）：1124622970
            <br />
            本项目基于 MIT 协议开源。
            <br />
            界面设计语言参考 Windows 11 Fluent Design 规范独立实现，未使用任何第三方专有资产。
          </div>

          <div style={{ marginTop: 18, fontSize: 12, opacity: 0.5, lineHeight: 1.8 }}>
            <b>免责声明</b>
            <br />
            本软件为开源工具集合，按「现状」提供，不附带任何明示或暗示的担保。使用本软件
            所产生的任何直接或间接后果（包括但不限于数据丢失、系统异常、与第三方软件冲突）
            由使用者自行承担。网址安全检测、音乐搜索等功能仅作辅助参考，不构成安全承诺或
            版权授权；请遵守所在地区法律法规及各平台服务条款，仅将本软件用于合法用途。
          </div>
        </>
      )}
    </div>
  )
}
