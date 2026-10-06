"""抓取基座：带磁盘缓存、gzip 解码、多编码回退、按域名限速。"""
import gzip
import hashlib
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE, exist_ok=True)

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_lock = threading.Lock()
_last_hit = {}


def _cache_path(url):
    return os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".bin")


def _throttle(host, gap=0.4):
    """同一域名两次请求之间至少间隔 gap 秒。"""
    with _lock:
        now = time.time()
        wait = _last_hit.get(host, 0) + gap - now
        _last_hit[host] = now + max(wait, 0)
    if wait > 0:
        time.sleep(wait)


def fetch(url, timeout=12, gap=0.2, retries=1, force=False):
    """返回 (status, html_or_'')；status 为 'ok' | 'http:NNN' | 'err:...'。

    若 rendered/ 下已有 Playwright 渲染结果，优先用它（JS 渲染站点）。
    """
    rendered = os.path.join(os.path.dirname(CACHE), "rendered",
                            hashlib.sha1(url.encode()).hexdigest() + ".html")
    if os.path.exists(rendered):
        with open(rendered, encoding="utf-8") as fh:
            return "ok", fh.read()

    path = _cache_path(url)
    if not force and os.path.exists(path):
        with open(path, "rb") as fh:
            status = fh.readline().decode("utf-8", "ignore").strip()
            return status, fh.read().decode("utf-8", "ignore")

    host = urllib.parse.urlparse(url).netloc
    last_err = ""
    for attempt in range(retries + 1):
        _throttle(host, gap)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                html = _decode(raw)
                _store(path, "ok", html)
                return "ok", html
        except urllib.error.HTTPError as exc:
            last_err = "http:%s" % exc.code
            if exc.code in (403, 404, 410):
                break
        except Exception as exc:  # noqa: BLE001 - 网络异常统一降级
            last_err = "err:%s" % type(exc).__name__
        time.sleep(0.8 * (attempt + 1))
    html = ""
    _store(path, last_err, html)
    return last_err, html


def _store(path, status, html):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(status + "\n" + html)
    os.replace(tmp, path)


def _decode(raw):
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:  # noqa: BLE001
            continue
    return raw.decode("utf-8", "ignore")


TAG_RE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")


def to_text(html):
    html = TAG_RE.sub(" ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|li|tr|h\d|section)>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = (html.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    lines = [re.sub(r"[ \t\u3000]+", " ", ln).strip() for ln in html.split("\n")]
    return [ln for ln in lines if ln]


def anchors(html, base):
    out = []
    for match in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html):
        attrs, inner = match.group(1), match.group(2)
        href = re.search(r'href\s*=\s*["\']([^"\']*)["\']', attrs)
        if not href:
            continue
        text = re.sub(r"\s+", "", re.sub(r"(?s)<[^>]+>", "", inner))
        out.append((text, urllib.parse.urljoin(base, href.group(1).strip())))
    return out
