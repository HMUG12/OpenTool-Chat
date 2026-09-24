"""
网址安全检测 —— OpenClass-Box 原生实现。

规则设计参考 VirusDetector（MIT）公开的评分思路，这里用 Python 重写：
  - 域名仿冒（品牌词 + 形近/typosquat）      最高 +60
  - 域名注册时间过新（RDAP）                 最高 +60
  - 页面缺少 ICP 备案号                      +30
  - 跨域压缩包 / 可执行下载链接              最高 +40
  - IP 直接访问 / 非常规端口                 +30 / +15
  - 老域名                                   -20（减分）
阈值：>=80 提示确认，>=100 高危。

联网查询（页面抓取 / RDAP）全部带超时并复用系统代理，失败即跳过对应规则，
绝不因断网误报，也不会拖慢调用方。
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from .updater import _system_proxy

_TIMEOUT = 6.0
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OpenClass-Box"}

# 高频品牌词（用于仿冒检测，可继续补充）
BRANDS = [
    "google", "microsoft", "apple", "amazon", "facebook", "paypal",
    "alipay", "taobao", "tmall", "jd", "qq", "wechat", "weixin",
    "baidu", "bilibili", "zhihu", "sina", "sohu", "163", "126",
    "icbc", "ccb", "abchina", "bankcomm", "alibaba", "huawei",
    "xiaomi", "lenovo", "dell", "adobe", "oracle", "nvidia",
]

# 常见形近/替换手法
LOOKALIKE = {"0": "o", "1": "l", "3": "e", "5": "s", "8": "b", "$": "s", "vv": "w", "rn": "m"}


def _norm_domain(domain: str) -> str:
    d = unicodedata.normalize("NFKC", domain.lower().split(":")[0])
    if d.startswith("www."):
        d = d[4:]
    for k, v in LOOKALIKE.items():
        d = d.replace(k, v)
    return d


def registrable_domain(domain: str) -> str:
    """取可注册域名（去掉子域，兼顾 com.cn 这类双后缀）。"""
    parts = _norm_domain(domain).split(".")
    if len(parts) <= 2:
        return ".".join(parts)
    double = {"com.cn", "net.cn", "org.cn", "gov.cn", "co.jp", "com.hk", "co.uk", "com.tw"}
    if ".".join(parts[-2:]) in double and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def spoof_score(domain: str) -> tuple[int, list[str]]:
    """域名仿冒检测。"""
    name = registrable_domain(domain).split(".")[0]
    score, reasons = 0, []
    for brand in BRANDS:
        # 官网豁免：可注册主名就是品牌本身（baidu.com / google.com），不算仿冒
        if name == brand:
            return 0, []
        if brand in name:
            # 品牌词之外还附加了其它词（-login / -secure 等），更像仿冒
            score = max(score, 60 if len(name) > len(brand) + 2 else 45)
            reasons.append(f"域名包含品牌词「{brand}」但非官方域名")
            break
        if abs(len(name) - len(brand)) <= 2 and _levenshtein(name, brand) <= 2:
            score = max(score, 60)
            reasons.append(f"域名与品牌「{brand}」高度相似（疑似仿冒）")
            break
    if name.count("-") >= 2 or len(re.findall(r"\d", name)) >= 3:
        score = max(score, 25)
        reasons.append("域名含异常连字符或数字组合")
    return score, reasons


def _open(url: str, timeout: float = _TIMEOUT):
    proxies = _system_proxy()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(proxies) if proxies else None
    )
    return opener.open(urllib.request.Request(url, headers=_HEADERS), timeout=timeout)


def _fetch_page(url: str) -> str:
    try:
        with _open(url) as resp:
            return resp.read(200_000).decode("utf-8", "ignore")
    except (OSError, urllib.error.URLError, ValueError):
        return ""


def _has_icp(html: str) -> bool:
    return bool(re.search(r"(ICP\s*备|京ICP|粤ICP|沪ICP|浙ICP|苏ICP|鲁ICP|蜀ICP|ICP证)", html, re.I))


def _cross_origin_downloads(html: str, host: str) -> int:
    hits = 0
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+\.(?:zip|rar|7z|exe|msi|apk))["\']', html, re.I):
        link = m.group(1)
        if link.startswith("http") and host not in link:
            hits += 1
    return hits


def domain_age_days(domain: str) -> int | None:
    """通过 RDAP 查询域名注册天数；失败返回 None。"""
    try:
        with _open(f"https://rdap.org/domain/{domain}") as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for event in data.get("events", []):
            if event.get("eventAction") == "registration":
                date = str(event.get("eventDate") or "")[:10]
                if date:
                    stamp = time.mktime(time.strptime(date, "%Y-%m-%d"))
                    return int((time.time() - stamp) / 86400)
    except (OSError, urllib.error.URLError, ValueError):
        return None
    return None


def check_url(url: str, fetch_page: bool = True) -> dict[str, Any]:
    """给网址打分。返回 score / level(safe|warn|danger) / reasons。"""
    target = url if "://" in url else f"http://{url}"
    try:
        parsed = urlparse(target)
    except ValueError:
        return {"url": url, "score": 0, "level": "safe", "reasons": ["网址无法解析"]}

    host = parsed.hostname or ""
    if not host:
        return {"url": url, "score": 0, "level": "safe", "reasons": ["网址缺少主机名"]}

    score, reasons = 0, []

    # 1) 域名仿冒（IP 地址没有“品牌”概念，跳过仿冒比对）
    is_ip = bool(re.fullmatch(r"[\d.]+", host))
    sub, sub_reasons = (0, []) if is_ip else spoof_score(host)
    score += sub
    reasons += sub_reasons

    # 2) IP 访问 / 非常规端口
    if is_ip:
        score += 30
        reasons.append("使用 IP 地址访问而非域名")
    if parsed.port not in (None, 80, 443):
        score += 15
        reasons.append(f"使用非常规端口 {parsed.port}")

    # 3) 页面类规则
    html = ""
    if fetch_page:
        html = _fetch_page(target)
        if html:
            if not _has_icp(html):
                score += 30
                reasons.append("页面未发现 ICP 备案号")
            downloads = _cross_origin_downloads(html, host)
            if downloads:
                score += min(40, 20 + downloads * 5)
                reasons.append(f"存在 {downloads} 个跨域压缩包/可执行下载链接")
        else:
            reasons.append("（页面抓取失败，已跳过页面类规则）")
            # 域名已高度可疑时，不能因为抓不到页面就判为安全
            if sub >= 60:
                score += 25
                reasons.append("域名高度可疑且页面不可达（无法完成页面校验）")

    # 4) 域名年龄
    age = domain_age_days(registrable_domain(host))
    if age is not None:
        if age < 30:
            score += 60
            reasons.append(f"域名注册仅 {age} 天（新域名高风险）")
        elif age > 730:
            score -= 20
            reasons.append(f"域名已注册 {age // 365} 年（可信度加分）")

    score = max(0, score)
    level = "danger" if score >= 100 else ("warn" if score >= 80 else "safe")
    return {"url": url, "host": host, "score": score, "level": level, "reasons": reasons}
