"""
冒烟检查 —— 不启动 GUI，验证后端核心是否健康。

用法：
    python scripts/smoke.py

覆盖：路径解析、工具注册扫描、工具元数据完整性、配置读写。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows 控制台默认使用 GBK，无法编码 emoji / 变体选择符，强制切到 UTF-8
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

from backend.api import Api  # noqa: E402
from backend.core import paths  # noqa: E402
from backend.core.monitor import monitor  # noqa: E402
from backend.core.registry import tool_registry as registry  # noqa: E402


def section(title: str) -> None:
    print(f"\n── {title} ──")


def main() -> int:
    failures: list[str] = []

    print("OpenClass 冒烟检查")
    print("=" * 56)

    # 1) 路径
    section("路径")
    print(f"  程序根目录 : {paths.app_root()}")
    print(f"  工具目录   : {paths.tools_dir()}")
    print(f"  配置目录   : {paths.config_dir()}")
    print(f"  前端产物   : {paths.frontend_index()}")
    if not paths.tools_dir().is_dir():
        failures.append("工具目录不存在")

    frontend_exists = paths.frontend_index().is_file()
    print(f"  前端已构建 : {'是' if frontend_exists else '否（需 npm run build）'}")

    # 2) 工具扫描
    section("工具注册")
    api = Api()
    tools = api.list_tools()
    if not tools:
        failures.append("未发现任何工具（检查 tools/ 目录）")
    for t in tools:
        flag = "✓" if t["available"] else f"✗ {t['reason']}"
        print(f"  [{t['kind']:>8}] {t['icon']} {t['name']:<16} v{t['version']:<8} {flag}")
        if not t["id"] or not t["name"]:
            failures.append(f"工具元数据不完整：{t}")

    # 3) 入口可达性
    section("入口可达性")
    for spec in registry.list():
        exists = spec.entry_path.exists()
        print(f"  {'✓' if exists else '✗'} {spec.name}: {spec.entry_path}")
        if spec.available and not exists:
            failures.append(f"工具标记为可用但入口缺失：{spec.id}")

    # 4) 配置读写
    section("配置读写")
    original = api.get_theme()
    ok = api.set_theme("dark")
    restored = api.get_theme()
    api.set_theme("dark" if original == "light" else "light")
    print(f"  原始主题   : {original}")
    print(f"  写入 dark  : {'成功' if ok else '失败'} → {restored}")
    if not ok or restored != "dark":
        failures.append("主题写入未生效")
    if api.set_theme("bogus"):
        failures.append("非法主题值被接受")

    # 5) 元信息
    section("应用信息")
    for key, value in api.get_info().items():
        print(f"  {key:<14}: {value}")

    # 6) 系统监测
    section("系统监测")
    try:
        monitor.start()
        for _ in range(25):  # 等待至少产出 2 个采样点
            if len(monitor.metrics().get("history", [])) >= 2:
                break
            time.sleep(0.1)

        m = monitor.metrics()
        print(f"  CPU 使用率   : {m['cpu']['percent']:.1f}%  ({len(m['cpu']['perCore'])} 线程)")
        print(f"  内存         : {m['memory']['percent']:.1f}%  "
              f"({m['memory']['used'] / 1024**3:.1f} / {m['memory']['total'] / 1024**3:.1f} GB)")
        print(f"  网络下行/上行: {m['network']['download'] / 1024:.1f} / "
              f"{m['network']['upload'] / 1024:.1f} KB/s")
        print(f"  采样点数     : {len(m['history'])}")
        if not m["history"]:
            failures.append("未产出任何采样点")

        hw = monitor.hardware()
        print(f"  CPU 型号     : {hw['cpu']['name']}")
        print(f"  核心/线程    : {hw['cpu']['cores']}C / {hw['cpu']['threads']}T")
        print(f"  内存总量     : {hw['memory']['totalGB']} GB")
        print(f"  磁盘分区     : {len(hw['disks'])} 个")
        for d in hw["disks"]:
            print(f"      {d['device']:<8} {d['percent']:>5.1f}%  "
                  f"{d['used'] / 1024**3:>7.1f} / {d['total'] / 1024**3:.1f} GB  [{d['fstype']}]")
        print(f"  显卡         : {len(hw['gpus'])} 个")
        for g in hw["gpus"]:
            print(f"      {g.get('name', '未知')}")
        if not hw["cpu"]["name"]:
            failures.append("未能读取 CPU 型号")

        net = monitor.network()
        active = [i for i in net["interfaces"] if i["up"] and i["ipv4"]]
        print(f"  网络接口     : {len(net['interfaces'])} 个（活动 {len(active)} 个）")
        for i in active:
            addr = i["ipv4"][0]["address"]
            print(f"      {i['name']:<28} {addr:<16} {i['speedMbps']} Mbps")
        print(f"  默认网关     : {net['topology']['gateways'] or '未解析到'}")

        ipinfo = monitor.ip()
        print(f"  主机名       : {ipinfo['hostname']}")
        print(f"  局域网 IP    : {ipinfo['local']}")
        if not ipinfo["local"]:
            failures.append("未能获取局域网 IP")

        monitor.stop()
    except Exception as exc:  # 监测异常不应让整个 smoke 崩掉
        failures.append(f"系统监测模块异常：{exc}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 56)
    if failures:
        print(f"✗ {len(failures)} 项检查未通过：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("✓ 全部检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
