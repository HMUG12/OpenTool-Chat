# OpenClass

Windows 桌面工具箱。收录实用小工具，并提供一套零配置的插件机制：
把一个工具文件夹放进 `tools/`，它就会出现在界面上，无需改动任何代码。

---

## 功能

| 模块 | 说明 |
|------|------|
| 系统状态 | CPU / 内存 / 存储用量、网络实时速率曲线、IP 与网关、硬件明细、网卡列表 |
| 工具箱 | 已收录工具的网格视图，支持分类筛选与关键词搜索 |
| 插件 | 列出外部工具与插件，可重新扫描或打开工具目录 |
| 设置 | 浅色 / 深色 / 跟随系统，偏好保存在程序目录 |
| 关于 | 运行环境与路径信息 |

### 系统状态页

主页展示三类实时监测：

- **硬件**：处理器型号、核心线程数、频率、内存与交换分区、磁盘分区用量、显示适配器、主板、启动时间
- **网络**：每秒下行 / 上行速率（双曲线，纵轴共享以保可比）、累计收发、网卡 IPv4/MAC/速率
- **IP**：主机名、局域网 IP、默认网关、DNS，公网 IP 需手动触发查询

> 公网 IP 是**唯一依赖网络的动作**。工具箱的主战场是离线环境，
> 因此该项设计为手动触发 + 多源回退 + 2.5 秒超时，取不到时显示「未获取到」而不是报错。

---

## 技术栈

| 层 | 选型 |
|---|---|
| 界面渲染 | WebView2（Windows 10/11 系统组件，无需打包 Chromium） |
| 前端 | React 18 + TypeScript + Vite + Fluent UI v9 |
| 宿主 | Python + `pywebview` |
| 系统监测 | `psutil` + WMI（PowerShell CIM）+ `ipconfig` |
| 打包 | PyInstaller（`--onedir`，绿色便携） |

业务逻辑在 Python 侧；工具全部以**独立进程**启动，崩溃不会拖垮主界面。

---

## 快速开始

### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

### 2. 构建前端（只需在前端有改动时执行）

```powershell
cd frontend
npm install
npm run build
```

### 3. 运行

```powershell
python main.py          # 加载 frontend/dist
python main.py --dev    # 连接 localhost:5173，配合 npm run dev 做热更新
python main.py --debug  # 开启 WebView 调试
```

### 4. 健康检查

```powershell
python scripts/smoke.py
```

不启动界面，验证路径解析、工具注册、配置读写与系统监测是否正常。

---

## 目录结构

```
OpenClass/
├── main.py                 # 入口
├── backend/
│   ├── api.py              # 前端 ⇄ Python 的边界
│   ├── main.py             # pywebview 宿主
│   └── core/
│       ├── paths.py        # 单一路径真相（便携：跟随 exe 目录）
│       ├── config.py       # 偏好持久化
│       ├── registry.py     # 工具注册表（扫描即发现）
│       ├── runner.py       # 独立进程启动器（含 UAC 提权）
│       └── monitor.py      # 硬件 / 网络 / IP 监测
├── frontend/               # React + Fluent UI
│   └── src/
│       ├── App.tsx         # 主布局与主题
│       ├── api.ts          # 后端调用封装（内置 mock，可脱离宿主预览）
│       ├── format.ts       # 数值格式化
│       ├── components/     # SideNav / TitleBar / ToolCard / UsageBar / SparkLine
│       └── pages/          # Dashboard / Tools / Plugins / Settings / About
├── tools/                  # 工具目录（详见 tools/README.md）
└── scripts/smoke.py        # 冒烟检查
```

---

## 新增一个工具

在 `tools/` 下建一个文件夹，放入 `tool.json` 与入口文件即可，
不必修改任何 Python 代码。完整契约见 [`tools/README.md`](tools/README.md)。

```json
{
  "id": "file_hash",
  "name": "文件哈希校验",
  "description": "计算文件的 MD5 / SHA1 / SHA256 / SHA512",
  "category": "file",
  "icon": "#️⃣",
  "version": "1.0.0",
  "author": "OpenClass",
  "entry": "main.py"
}
```

支持 `.exe` / `.bat` / `.ps1` / `.py`。第三方绿色软件原样拷进去也能被自动识别。

---

## 设计取舍

- **便携优先**：数据目录固定在程序所在目录，不使用 `%APPDATA%`，整个文件夹可拷进 U 盘
- **进程隔离**：工具之间、工具与主程序之间互不影响
- **离线可用**：除公网 IP 查询外无任何网络依赖
- **统一采样**：实时指标由后台线程按 1 秒间隔采集并缓存，前端只读快照

---

## 已知限制

- WebView2 运行时在部分老版本 Windows 10（如 LTSC）上可能缺失，需手动安装离线包
- WMI 查询（显卡 / 主板）首次调用约 1~2 秒，结果缓存，仅影响首屏
- 尚未提供打包脚本，绿色版需自行用 PyInstaller 以 `--onedir` 方式构建

---

## 许可证

MIT License. 见 [LICENSE](LICENSE)。
