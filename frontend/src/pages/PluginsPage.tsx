import { Button, MessageBar, MessageBarBody } from '@fluentui/react-components'
import { api } from '../api'
import type { ToolSpec } from '../types'

interface Props {
  tools: ToolSpec[]
  onRefresh: () => void
}

export default function PluginsPage({ tools, onRefresh }: Props) {
  const extensions = tools.filter((t) => t.kind !== 'builtin')

  const openToolDir = async () => {
    await api.open_tool_dir()
  }

  return (
    <div className="oc-page">
      <div className="oc-page-header">
        <div className="oc-page-title">插件与外部工具</div>
        <div className="oc-page-desc">
          把任意可执行文件（含 .exe / .bat / .py）放进 tools 目录即可自动识别
        </div>
      </div>

      <MessageBar intent="info" style={{ marginBottom: 18 }}>
        <MessageBarBody>
          插件契约：每个工具一个文件夹 + 一份 <code>tool.json</code>。
          主程序通过独立进程启动工具，工具崩溃不会影响主界面。
        </MessageBarBody>
      </MessageBar>

      <div className="oc-toolbar">
        <Button appearance="primary" onClick={onRefresh}>
          重新扫描
        </Button>
        <Button appearance="secondary" onClick={openToolDir}>
          打开工具目录
        </Button>
      </div>

      {extensions.length === 0 ? (
        <div className="oc-empty">
          尚未安装任何插件。把工具文件夹放进 tools/ 目录后点击「重新扫描」
        </div>
      ) : (
        <div className="oc-toolgrid">
          {extensions.map((t) => (
            <div key={t.id} className="oc-toolcard" style={{ cursor: 'default' }}>
              <div className="oc-toolcard-top">
                <div className="oc-toolcard-icon">{t.icon}</div>
                <div className="oc-toolcard-head">
                  <div className="oc-toolcard-name">{t.name}</div>
                  <div className="oc-toolcard-meta">v{t.version}</div>
                </div>
              </div>
              <div className="oc-toolcard-desc">{t.description}</div>
              <div className="oc-toolcard-foot">
                <span className={`oc-chip ${t.kind === 'external' ? 'external' : 'plugin'}`}>
                  {t.kind === 'external' ? '外部' : '插件'}
                </span>
                {t.available ? (
                  <span className="oc-chip external">就绪</span>
                ) : (
                  <span className="oc-chip admin">{t.reason ?? '不可用'}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
