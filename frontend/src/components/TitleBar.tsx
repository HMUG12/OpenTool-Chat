import { api } from '../api'

/** 自绘标题栏（pywebview frameless 模式）+ Win11 风格窗口按钮 */
export default function TitleBar() {
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
          title="最大化"
          onClick={() => void api.window_toggle_maximize()}
        >
          {'\uE922'}
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
