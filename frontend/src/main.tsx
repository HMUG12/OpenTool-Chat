import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'

const root = document.getElementById('root')
if (!root) throw new Error('未找到 #root 挂载点')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// 主应用挂载后移除启动遮罩（boot-loader 由 index.html 内联，覆盖 JS bundle 加载期）
const removeBoot = () => {
  const el = document.getElementById("boot-loader")
  if (el) {
    el.classList.add("hidden")
    setTimeout(() => el.remove(), 360)
  }
}
if (document.readyState === "complete") removeBoot()
else window.addEventListener("load", removeBoot)
