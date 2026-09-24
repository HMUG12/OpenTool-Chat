import type { ReactNode } from 'react'
import { ToolboxRegular } from '@fluentui/react-icons'

export interface NavItem {
  id: string
  label: string
  /** Fluent UI 图标组件，不使用 emoji */
  icon: ReactNode
  badge?: number
}

interface Props {
  items: NavItem[]
  activeId: string
  onSelect: (id: string) => void
  version?: string
}

export default function SideNav({ items, activeId, onSelect, version }: Props) {
  return (
    <nav className="oc-sidenav">
      <div className="oc-sidenav-brand">
        <div className="oc-sidenav-brand-icon">
          <ToolboxRegular fontSize={15} />
        </div>
        <div className="oc-sidenav-brand-name">OpenClass-Box</div>
      </div>

      {items.map((item) => (
        <button
          key={item.id}
          className={`oc-navitem${activeId === item.id ? ' active' : ''}`}
          onClick={() => onSelect(item.id)}
        >
          <span className="oc-navitem-icon">{item.icon}</span>
          <span>{item.label}</span>
          {item.badge !== undefined && (
            <span className="oc-navitem-badge">{item.badge}</span>
          )}
        </button>
      ))}

      <div className="oc-sidenav-footer">{version ? `v${version}` : ''}</div>
    </nav>
  )
}
