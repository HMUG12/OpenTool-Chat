import type { ToolSpec } from '../types'

interface Props {
  tool: ToolSpec
  onLaunch: (tool: ToolSpec) => void
}

const KIND_LABEL: Record<ToolSpec['kind'], { text: string; cls: string }> = {
  builtin: { text: '内置', cls: '' },
  plugin: { text: '插件', cls: 'plugin' },
  external: { text: '外部', cls: 'external' },
}

export default function ToolCard({ tool, onLaunch }: Props) {
  const kind = KIND_LABEL[tool.kind]
  const disabled = !tool.available

  const handleClick = () => {
    if (disabled) return
    onLaunch(tool)
  }

  return (
    <div
      className={`oc-toolcard${disabled ? ' disabled' : ''}`}
      onClick={handleClick}
      title={disabled ? tool.reason : `启动 ${tool.name}`}
    >
      <div className="oc-toolcard-top">
        <div className="oc-toolcard-icon">{tool.icon}</div>
        <div className="oc-toolcard-head">
          <div className="oc-toolcard-name">{tool.name}</div>
          <div className="oc-toolcard-meta">v{tool.version} · {tool.author}</div>
        </div>
      </div>

      <div className="oc-toolcard-desc">{tool.description}</div>

      <div className="oc-toolcard-foot">
        <span className={`oc-chip ${kind.cls}`}>{kind.text}</span>
        {tool.admin && <span className="oc-chip admin">需管理员</span>}
        {disabled && <span className="oc-chip admin">不可用</span>}
        {tool.tags.slice(0, 2).map((t) => (
          <span key={t} className="oc-chip">
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
