import { useEffect, useState } from 'react'
import { api } from '../api'

/** 自绘标题栏（pywebview frameless 模式）+ Win11 风格窗口按钮 */
export default function TitleBar() {
  const [maximized, setMaximized] = useState(false)

  // 跟踪真实窗口状态（Win32 IsZoomed），让「最大化/还原」图标始终与实际一致
  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        setMaximized(await api.window_is_maximized())
      } catch {
        /* 忽略：非宿主环境没有该接口 */
      }
    }, 900)
    return () => window.clearInterval(timer)
  }, [])

  return (
    <div className="oc-titlebar">
      <div
        className="oc-titlebar-drag"
        onDoubleClick={() => void api.window_toggle_maximize()}
      >
        <span className="oc-titlebar-title">OpenClass-Box</span>
      </div>

      <div className="oc-titlebar-actions">
        <button
          className="oc-winbtn"
          title="最小化"
          onClick={() => void api.window_minimize()}
        >
          {'\uE921'}
        </button>
        <button
          className="oc-winbtn"
          title={maximized ? '向下还原' : '最大化'}
          onClick={() => void api.window_toggle_maximize()}
        >
          {maximized ? '\uE923' : '\uE922'}
        </button>
        <button
          className="oc-winbtn close"
          title="关闭"
          onClick={() => void api.window_close()}
        >
          {'\uE8BB'}
        </button>
      </div>
    </div>
  )
}
