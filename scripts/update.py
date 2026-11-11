#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 配置自动聚合脚本
- 从 config/sources.json 读源列表
- 主线+备用多地址尝试，自动中文域名 punycode
- 校验为合法 TVBox 配置（含 sites/spiders/lives）
- 自动修复 ext 字符串 -> 对象（FongMi 新版要求）
- 每个源存 output/<id>.json
- 聚合 output/config.json（单仓，FongMi 直接填这个）
- 状态写回 README
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT, "config", "sources.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
# 单源干净副本放子目录，避免把 output 根目录弄得像垃圾场
SOURCES_DIR = os.path.join(OUTPUT_DIR, "_sources")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SOURCES_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0"
# 直播源（央视+卫视）探测最慢：卫视要逐个真抓 TS 分片，境外机房还常超时。
# 所以直播改成每周刷新一次，其余日子沿用现有的 cctv_live.txt，只更新点播。
# 环境变量 REFRESH_LIVE=1 才真正重抓；工作流在周一（北京时间）自动设 1。
REFRESH_LIVE = os.environ.get("REFRESH_LIVE", "1").strip() == "1"

TIMEOUT = 15
MAX_RETRIES = 2
SITE_PROBE_TIMEOUT = 6      # 单次探测超时（境外机房到国内 CDN 慢，4 秒会误杀）
SITE_PROBE_WORKERS = 24     # 并发探测线程数
UNKNOWN_MAX = 220           # 探测超时但保留的站点上限

TVBOX_KEYS = ("sites", "spiders", "lives", "store", "exts", "parses", "flags")


def idn_encode(url):
    p = urllib.parse.urlsplit(url)
    host = p.hostname or ""
    try:
        host = host.encode("idna").decode("ascii")
    except Exception:
        pass
    netloc = f"{host}:{p.port}" if p.port else host
    return urllib.parse.urlunsplit((p.scheme, netloc, p.path, p.query, p.fragment))


def parse_json(text):
    text = text.lstrip("﻿").strip()
    lines = [ln for ln in text.split("\n") if not ln.lstrip().startswith("//")]
    text = "\n".join(lines)
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        try:
            obj, _ = json.JSONDecoder(strict=False).raw_decode(text)
            return obj
        except Exception:
            raise


def fix_ext_strings(data):
    """把站点里 ext 是字符串的修成对象（FongMi 新版要求）。"""
    fixed = 0
    if not isinstance(data, dict):
        return data, fixed
    for s in data.get("sites", []) or []:
        if not isinstance(s, dict):
            continue
        ext = s.get("ext")
        if isinstance(ext, str):
            try:
                s["ext"] = json.loads(ext)
                fixed += 1
            except Exception:
                s.pop("ext", None)
                fixed += 1
    # parses 也可能有 ext
    for p in data.get("parses", []) or []:
        if isinstance(p, dict) and isinstance(p.get("ext"), str):
            try:
                p["ext"] = json.loads(p["ext"])
                fixed += 1
            except Exception:
                p.pop("ext", None)
    return data, fixed


# FongMi 的 Bean 里这些字段是 int，字符串会导致 Gson 抛
# "Expected an int but was STRING at path $.sites[x].playerType" 之类，整份配置解析失败
INT_FIELDS = (
    "type", "playerType", "searchable", "quickSearch", "filterable",
    "indexs", "timeout", "level", "sort", "style", "flag",
)

# FongMi 要求 ext 必须是 JSON 对象，不能是字符串
DICT_FIELDS = ("ext",)


def _to_int(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        t = v.strip()
        if not t:
            return None
        try:
            return int(float(t))
        except Exception:
            return None
    return None


def _to_dict(v):
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        t = v.strip()
        if not t or t in ("null", "None"):
            return None
        try:
            o = json.loads(t)
            return o if isinstance(o, dict) else None
        except Exception:
            return None
    return None


def normalize_types(data):
    """把整份配置的字段类型强制规范化，消除不同源合并后产生的类型混合。

    这是 FongMi 能成功解析配置的前提：Gson 是严格类型绑定，同一字段在
    同一次反序列化里出现 int 和 str 两种形态就会整体抛异常，表现为
    界面上"配置取得失败"。
    """
    if not isinstance(data, dict):
        return data
    fixed = 0
    for field in ("sites", "lives", "parses"):
        items = data.get(field)
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            # 数值字段：能转就转，转不了直接删掉（保留 null/错误值没有意义且会崩）
            for k in INT_FIELDS:
                if k not in it:
                    continue
                v = it[k]
                if isinstance(v, int) and not isinstance(v, bool):
                    continue
                iv = _to_int(v)
                if iv is None:
                    it.pop(k, None)
                else:
                    it[k] = iv
                fixed += 1
            # ext 必须是对象
            for k in DICT_FIELDS:
                if k not in it:
                    continue
                if isinstance(it[k], dict):
                    continue
                dv = _to_dict(it[k])
                if dv is None:
                    it.pop(k, None)
                else:
                    it[k] = dv
                fixed += 1
            # 清掉 null 值
            for k in list(it.keys()):
                if it[k] is None:
                    it.pop(k, None)
    return data


def check_type_conflicts(data):
    """质量门：检查同一列表字段里是否有同名 key 存在多种类型。
    返回 [(field, key, {类型: 数量})]，非空表示这份配置会让 FongMi 崩。
    """
    import collections
    conflicts = []
    for field in ("sites", "lives", "parses", "doh", "rules"):
        items = data.get(field) or []
        if not isinstance(items, list) or not items:
            continue
        m = collections.defaultdict(collections.Counter)
        for it in items:
            if not isinstance(it, dict):
                continue
            for k, v in it.items():
                m[k][type(v).__name__] += 1
        for k, c in m.items():
            if len(c) > 1:
                conflicts.append((field, k, dict(c)))
    return conflicts


def is_valid(data):
    if not isinstance(data, dict):
        return False
    return any(k in data for k in TVBOX_KEYS)


def fetch(url):
    target = idn_encode(url)
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(
                target,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"},
                timeout=TIMEOUT,
                allow_redirects=True,
            )
            r.raise_for_status()
            data = parse_json(r.text)
            if not is_valid(data):
                raise ValueError("不是 TVBox 配置（缺 sites/spiders/lives）")
            return data
        except Exception as e:
            last = e
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
    raise last


# ============ 央视直播（央视官网官方 CDN 直连） ============
# 来源是 tv.cctv.com 直播页实际加载的 m3u8，属于央视自己对外公开的播放地址，
# 不依赖任何第三方搬运站，只要央视还在播就一直有效。
# 央视按频道把流量分发到三套云 CDN（腾讯云 / 火山引擎 / 百度云），
# 每个频道在哪套上可用会变，所以逐频道遍历三套，取第一个能出 TS 分片的。
CCTV_CHANNELS = [
    ("CCTV-1 综合", "cctv1"),
    ("CCTV-2 财经", "cctv2"),
    ("CCTV-3 综艺", "cctv3"),
    ("CCTV-4 中文国际", "cctv4"),
    ("CCTV-5 体育", "cctv5"),
    ("CCTV-5+ 体育赛事", "cctv5plus"),
    ("CCTV-6 电影", "cctv6"),
    ("CCTV-7 国防军事", "cctv7"),
    ("CCTV-8 电视剧", "cctv8"),
    ("CCTV-9 纪录", "cctv9"),
    ("CCTV-10 科教", "cctv10"),
    ("CCTV-11 戏曲", "cctv11"),
    ("CCTV-12 社会与法", "cctv12"),
    ("CCTV-13 新闻", "cctv13"),
    ("CCTV-14 少儿", "cctv14"),
    ("CCTV-15 音乐", "cctv15"),
    ("CCTV-16 奥林匹克", "cctv16"),
    ("CCTV-17 农业农村", "cctv17"),
    ("CCTV-4K 超高清", "cctv4k"),
]
CCTV_CDN = [
    "https://ldocctvwbcdtxy.liveplay.myqcloud.com/ldocctvwbcd/cdrmld{ch}_1_td.m3u8",
    "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmld{ch}_1/index.m3u8?BR=td",
    "https://ldcctvwbcdbd.a.bdydns.com/ldcctvwbcd/cdrmld{ch}_1/index.m3u8?BR=td",
]
INTL_PROBE_TIMEOUT = 6.0
INTL_PROBE_WORKERS = 10
CCTV_MIN_CHANNELS = 5         # 少于这个数就认为本次探测失败，保留旧文件


def parse_m3u(text):
    """从 m3u 文本里抽出 (频道名, 地址) 列表。"""
    out = []
    name = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            m = re.search(r",\s*(.+)$", line)
            name = m.group(1).strip() if m else None
        elif line.startswith("#"):
            continue
        elif name:
            out.append((name, line))
            name = None
    return out


def _url_alive(url):
    """探测直播地址是否可达，返回 (ok, 延迟ms)。"""
    t0 = time.time()
    try:
        r = requests.head(url, timeout=INTL_PROBE_TIMEOUT, allow_redirects=True,
                          headers={"User-Agent": USER_AGENT})
        if r.status_code < 400:
            return True, int((time.time() - t0) * 1000)
        if r.status_code in (403, 405, 501):
            r2 = requests.get(url, timeout=INTL_PROBE_TIMEOUT, stream=True,
                              allow_redirects=True, headers={"User-Agent": USER_AGENT})
            ok = r2.status_code < 400
            r2.close()
            return ok, int((time.time() - t0) * 1000)
        return False, 99999
    except Exception:
        return False, 99999


# ============ 卫视频道（运营商 IPTV 公网转播） ============
# 省级卫视几乎都不在官网提供公开 m3u8（湖南卫视域名已出售、浙江/江苏/东方/
# 北京/广东/深圳官网实测都拿不到），芒果TV 等自家 APP 的流带签名+DRM，
# 无法生成静态地址。这里改用各省广电授权传输的 IPTV 公网转播地址，
# 同样是官方播出的节目内容，但线路会变，所以每天重新拉、重新测。
SAT_FEEDS = [
    "https://raw.githubusercontent.com/Supprise0901/TVBox_live/main/live.txt",
    "https://raw.githubusercontent.com/Supprise0901/TVBox_live/main/live_ipv4.txt",
]
SAT_KEEP = re.compile(r"^[\u4e00-\u9fa5（）()]{2,10}卫视$|^[\u4e00-\u9fa5]{2,6}卫视$|"
                      r"^(湖南|浙江|江苏|东方|北京|广东|深圳|安徽|山东|湖北|河南|河北|"
                      r"天津|重庆|四川|贵州|云南|广西|江西|福建|吉林|辽宁|黑龙江|"
                      r"山西|陕西|甘肃|青海|宁夏|内蒙古|新疆|西藏|海南|东南|南方|三沙|延边|兵团)卫视$")
SAT_TARGET = 40   # 最多保留多少个卫视
SAT_LINES_PER_CH = 3   # 每个卫视台最多保留几条备用线路


def _sat_ok(url, timeout=6):
    """卫视线路验证：必须真抓到一个 TS 分片才算能播（只查清单文本会大量假阳性）。"""
    ok, ms, n, why = _cctv_stream_ok(url, timeout=timeout)
    return ok, ms


def build_satellite_live():
    """抓卫视 IPTV 转播地址，逐条验证可播，按延迟排序返回 (名称, url, ms) 列表。"""
    from concurrent.futures import ThreadPoolExecutor

    raw = []
    for feed in SAT_FEEDS:
        try:
            r = requests.get(feed, timeout=20, headers={"User-Agent": USER_AGENT},
                             verify=False)
            if r.status_code != 200:
                continue
            for line in r.text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",", 1)
                if len(parts) != 2:
                    continue
                name, url = parts[0].strip(), parts[1].strip()
                if not url.startswith("http"):
                    continue
                if not SAT_KEEP.match(name):
                    continue
                raw.append((name, url))
        except Exception as e:
            print("[sat] 源异常: %s" % e)

    # 同名频道多条线路，全部拿去测，取最快的
    by_name = {}
    for n, u in raw:
        by_name.setdefault(n, []).append(u)

    def _probe(pair):
        """一个台测它所有的候选地址，把能播的按延迟排好留最多 3 条。"""
        n, urls = pair
        good = []
        for u in urls:
            ok, ms = _sat_ok(u)
            if ok:
                good.append((ms, u))
        if not good:
            return None
        good.sort()
        return (n, good[:SAT_LINES_PER_CH])

    with ThreadPoolExecutor(max_workers=20) as ex:
        got = [x for x in ex.map(_probe, list(by_name.items())) if x]

    # 按每个台最快的那条排台序，选中前 SAT_TARGET 个台
    got.sort(key=lambda x: x[1][0][0])
    got = got[:SAT_TARGET]

    out = []
    for n, lines in got:
        for ms, u in lines:
            out.append((n, u, ms))

    print("[sat] 卫视 %d 个台 / %d 条线路（源里共 %d 个不同卫视）"
          % (len(got), len(out), len(by_name)))
    return out


def _cctv_join(base, rel):
    """清单里的相对地址解析：根路径(/x.ts)要保留域名，否则按目录拼。"""
    from urllib.parse import urlparse
    if rel.startswith("http"):
        return rel
    p = urlparse(base)
    if rel.startswith("/"):
        return p.scheme + "://" + p.netloc + rel
    return base.rsplit("/", 1)[0] + "/" + rel


def _cctv_first(text, base, want):
    for ln in text.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and want in ln:
            return _cctv_join(base, ln)
    return None


def _cctv_stream_ok(url, timeout=8):
    """真抓第一个 TS 分片，确认不是空壳清单。返回 (ok, 延迟ms, 分片字节, 原因)。"""
    t0 = time.time()
    H = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, timeout=timeout, headers=H, verify=False)
        if r.status_code != 200:
            return False, 99999, 0, "m3u8 HTTP %d" % r.status_code
        if "#EXTM3U" not in r.text:
            return False, 99999, 0, "不是m3u8"

        ts = _cctv_first(r.text, url, ".ts")
        if not ts:
            # master 清单，跟一层
            sub = _cctv_first(r.text, url, ".m3u8")
            if not sub:
                return False, 99999, 0, "清单无内容"
            r2 = requests.get(sub, timeout=timeout, headers=H, verify=False)
            if r2.status_code != 200:
                return False, 99999, 0, "子清单 HTTP %d" % r2.status_code
            ts = _cctv_first(r2.text, sub, ".ts")
            if not ts:
                return False, 99999, 0, "子清单无ts"

        tr = requests.get(ts, timeout=timeout + 4, headers=H, verify=False, stream=True)
        code = tr.status_code
        if code != 200:
            tr.close()
            return False, 99999, 0, "ts HTTP %d" % code
        got = 0
        for c in tr.iter_content(8192):
            got = len(c)
            break
        tr.close()
        if got < 1000:
            return False, 99999, 0, "ts过小 %d字节" % got
        return True, int((time.time() - t0) * 1000), int(tr.headers.get("Content-Length") or got), "ok"
    except Exception as e:
        return False, 99999, 0, type(e).__name__


def build_cctv_live():
    """逐个央视频道遍历三套官方 CDN，挑出真正能播的地址，生成 FongMi 直播 txt。"""
    from concurrent.futures import ThreadPoolExecutor

    def _probe_one(item):
        name, code = item
        why = ""
        urls = []          # 这个频道所有能播的线路，越多越稳
        for cdn in CCTV_CDN:
            url = cdn.format(ch=code)
            ok, ms, n, why = _cctv_stream_ok(url)
            if ok:
                urls.append((url, ms))
        if urls:
            return ("hit", name, code, urls, 0)
        # 三套全挂且是 404/403 → 该频道有版权限制，别写死链进去
        if "404" in why or "403" in why:
            return ("dead", name, code, [], 0)
        return ("miss", name, code, [], 0)

    with ThreadPoolExecutor(max_workers=INTL_PROBE_WORKERS) as ex:
        res = list(ex.map(_probe_one, CCTV_CHANNELS))

    hits = [x for x in res if x[0] == "hit"]
    print("[cctv] 官网实测通过 %d/%d 个频道" % (len(hits), len(CCTV_CHANNELS)))

    # 通过数太少 → 央视整体异常或运行环境网络问题，保留旧文件不覆盖
    if len(hits) < CCTV_MIN_CHANNELS:
        print("[cctv] 可用频道过少，本次跳过，保留上一次的 cctv_live.txt")
        return None

    # 通过了足够多，说明整体网络正常，个别没测通的按固定地址兜底
    # （GitHub Actions 跑在境外，部分国内 CDN 探测会失败，但国内手机能连）
    picked = []
    for kind, name, code, urls, _ in res:
        if kind == "hit":
            for u, ms in urls:
                picked.append((name, u, ms, 1))
        elif kind == "dead":
            print("[cctv] %s 三套均 404/403（版权限制），跳过" % name)
        else:
            print("[cctv] %s 网络抖动未测通，用固定地址兜底" % name)
            picked.append((name, CCTV_CDN[0].format(ch=code), 0, 0))

    def _order(x):
        m = re.search(r"CCTV-(\d+)", x[0])
        return int(m.group(1)) if m else 99

    picked.sort(key=_order)

    # 同一个台写多行 → FongMi 会合并成同一频道的多条线路，前一条挂了自动换下一条
    lines = ["央视频道,#genre#"]
    for name, url, ms, n in picked:
        lines.append(name + "," + url)

    # 卫视：官网不给公开流，用运营商 IPTV 公网转播地址补齐
    sats = build_satellite_live()
    if sats:
        lines.append("卫视频道,#genre#")
        for sn, su, sms in sats:
            lines.append(sn + "," + su)

    cctv_channels = len(set(x[0] for x in picked))
    sat_channels = len(set(x[0] for x in (sats or [])))
    kept = cctv_channels + sat_channels

    path = os.path.join(OUTPUT_DIR, "cctv_live.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("[cctv] 写入 cctv_live.txt：%d 个频道" % kept)
    print("[cctv] 最快 5 个：%s" % [(x[0], x[2]) for x in picked[:5]])

    globals()["_CCTV_PROFILE"] = (cctv_channels, sat_channels, (picked[0][0], picked[0][2]))

    return {
        "name": "央视直播",
        "url": "https://lsx9988.github.io/my-tvbox-cfg/output/cctv_live.txt",
        "group": "央视",
    }


def _live_alive(url):
    """直播源活性探测：HEAD 3 秒，4xx 直接判死，5xx 重试一次。"""
    try:
        r = requests.head(url, timeout=3, allow_redirects=True,
                          headers={"User-Agent": USER_AGENT})
        if r.status_code < 400:
            return True
        if r.status_code in (405, 501, 403):
            r2 = requests.get(url, timeout=3, stream=True, allow_redirects=True,
                              headers={"User-Agent": USER_AGENT})
            ok = r2.status_code < 400
            r2.close()
            return ok
        return False
    except Exception:
        return False


def _probe_err_kind(e):
    """区分「域名没了（真死）」和「连不上但可能是网络位置问题（不确定）」。

    GitHub Actions 跑在境外，国内站点大量 ConnectTimeout / SSL 报错，
    这类不能当死链删，否则线上站数永远比本地少一截（本地 438 → 线上 404）。
    只有解析不到域名（NXDOMAIN）才算真死。
    """
    txt = (str(e) or "").lower()
    if ("nameresolution" in txt or "name or service not known" in txt
            or "nodename nor servname" in txt or "getaddrinfo failed" in txt):
        return "dead"
    return "unknown"


def _site_alive(api, timeout=None):
    """点播 API 活性探测，返回 ("ok"/"unknown"/"dead", 延迟毫秒)。

    ok      = 真连上（HTTP < 400），参与速度排序
    unknown = 超时/SSL/连接重置/5xx，可能是网络位置问题，保留但排到最后
    dead    = 明确 404/410 或域名解析失败，直接删
    """
    timeout = timeout or SITE_PROBE_TIMEOUT
    t0 = time.time()
    try:
        r = requests.head(api, timeout=timeout, allow_redirects=True,
                          headers={"User-Agent": USER_AGENT})
        dt = int((time.time() - t0) * 1000)
        if r.status_code < 400:
            return "ok", dt
        if r.status_code in (403, 405, 501):
            t0 = time.time()
            r2 = requests.get(api, timeout=timeout, stream=True, allow_redirects=True,
                              headers={"User-Agent": USER_AGENT})
            dt = int((time.time() - t0) * 1000)
            code = r2.status_code
            r2.close()
            if code < 400:
                return "ok", dt
            if code in (403, 429):
                return "unknown", 99999
            return "dead", 99999
        if r.status_code in (400, 404, 410, 451):
            return "dead", 99999
        return "unknown", 99999
    except Exception as e:
        return _probe_err_kind(e), 99999


# 网盘点播关键词：用户不用网盘资源，自动剔除
PAN_KWS = (
    "网盘", "云盘", "盘搜", "盘se", "盘迷", "爱盘", "全盘", "我的盘",
    "115", "夸克", "quark", "alist", "mypan", "pansou", "panse",
    "阿里云盘", "百度网盘", "uc网盘",
)


def is_pan_site(s):
    text = ((s.get("name") or "") + " " + (s.get("key") or "")).lower()
    return any(k.lower() in text for k in PAN_KWS)


def clean_sites(sites, probe=True):
    """清洗点播站点：剔网盘、剔引流站、剔直播站、分级探测、按响应延迟排序。

    探测三档（境外跑 Actions 时是关键）：
      ok      → 真连上，按毫秒数升序排最前
      unknown → 超时/SSL/连接重置/5xx，可能是网络位置问题，保留但排到最后（上限 UNKNOWN_MAX）
      dead    → HTTP 404/410 或域名解析失败，直接删
    """
    direct = []    # (latency, idx, site)
    unknown = []   # (idx, site)
    others = []    # JS 爬虫类（无 http api，无法探测）
    dropped_pan = []
    dropped_junk = []
    dropped_dead = []
    dropped_live = []

    # 引流/配置站：直接删除，不是真点播
    JUNK_KWS = ("配置", "免费分享", "更新日期", "公告", "导航",
                "微信", "公众号", "加群", "下载APP", "下载app",
                "配置中心", "破解", "会员", "VIP", "vip")

    # 直播类站点：只按明确的直播字样剔除，不要用平台名（哔哩/企鹅也有正经影视点播）
    LIVE_KWS = ("直播", "live", "kman", "310", "看球", "轮播")

    def _is_junk(s):
        text = ((s.get("name") or "") + " " + (s.get("key") or "")).lower()
        return any(k.lower() in text for k in JUNK_KWS)

    def _is_live(s):
        text = ((s.get("name") or "") + " " + (s.get("key") or "")).lower()
        return any(k.lower() in text for k in LIVE_KWS)

    probe_list = []
    for s in sites or []:
        if not isinstance(s, dict):
            continue
        name = s.get("name", "?")
        api = (s.get("api") or "").strip()
        stype = s.get("type", 0)
        if is_pan_site(s):
            dropped_pan.append(name)
            continue
        if _is_junk(s):
            dropped_junk.append(name)
            continue
        if _is_live(s):
            dropped_live.append(name)
            continue
        if probe and stype == 1 and api.startswith("http"):
            probe_list.append((len(probe_list), s))
        else:
            others.append(s)

    # 并发探测：串行 400+ 站 × 6 秒会跑成十几分钟
    if probe_list:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=SITE_PROBE_WORKERS) as ex:
            results = list(ex.map(
                lambda it: (it[0], it[1], _site_alive((it[1].get("api") or "").strip())),
                probe_list))
        for idx, s, (state, dt) in results:
            if state == "ok":
                direct.append((dt, idx, s))
            elif state == "unknown":
                unknown.append((idx, s))
            else:
                dropped_dead.append(s.get("name", "?"))

    direct.sort(key=lambda x: (x[0], x[1]))
    unknown.sort(key=lambda x: x[0])
    if len(unknown) > UNKNOWN_MAX:
        dropped_dead.extend([s.get("name", "?") for _, s in unknown[UNKNOWN_MAX:]])
        unknown = unknown[:UNKNOWN_MAX]

    out = []
    speed_data = []  # (name, latency) 给 README 用，只记真测通的
    for dt, _idx, s in direct:
        out.append(s)
        speed_data.append((s.get("name", "?"), dt))
    for _idx, s in unknown:
        out.append(s)
    out.extend(others)

    print("   探测结果：可达 %d / 无法确认 %d / 判定失效 %d"
          % (len(direct), len(unknown), len(dropped_dead)))
    if direct:
        print(f"   最快 5 个：{[(s.get('name'), dt) for dt, _i, s in direct[:5]]}")
    for n in dropped_pan[:20]:
        print(f"   - 网盘: {n}")
    for n in dropped_dead[:20]:
        print(f"   - 死链: {n}")
    for n in dropped_live[:20]:
        print(f"   - 直播类: {n}")
    return out, speed_data


def clean_lives(lives, probe=True):
    """清洗直播列表：丢掉相对路径、本地代理、空 url、垃圾条目，按 url 去重，活性探测。"""
    out = []
    seen = set()
    dropped = []
    for item in lives or []:
        if not isinstance(item, dict):
            dropped.append(("非dict", str(item)[:60]))
            continue
        name = (item.get("name") or "").strip()
        url = (item.get("url") or "").strip()
        if not url:
            dropped.append(("空url", name))
            continue
        if url.startswith("./") or url.startswith("../"):
            dropped.append(("相对路径", name))
            continue
        if "127.0.0.1" in url or "localhost" in url or url == "yqk":
            dropped.append(("本地代理/特殊类型", name))
            continue
        if name in ("?", ""):
            dropped.append(("无名", url))
            continue
        if url in seen:
            dropped.append(("重复", name))
            continue
        # 活性探测：我们自己的国际频道跳过（它是我们生成的，必然通）
        if probe and "lsx9988" not in url:
            if not _live_alive(url):
                dropped.append(("活性探测失败", name))
                continue
        seen.add(url)
        out.append(item)
    # 把"国际频道"排第一
    out.sort(key=lambda x: 0 if x.get("name") == "国际频道" else 1)
    print(f"[lives] 清洗：{len(lives)} -> {len(out)}（丢 {len(dropped)}）")
    for reason, n in dropped:
        print(f"   - {reason}: {n}")
    return out


def build_elder_config(merged):
    """长辈版配置：只保留最快的 20 个直连 API 站 + 国内直播，去掉 JS 爬虫和国际频道。"""
    elder = {}
    # 顶层字段继承
    for k in ("spider", "wallpaper", "logo", "warningText"):
        if k in merged:
            elder[k] = merged[k]
    elder["warningText"] = "长辈版：只保留最稳定的站和国内直播"
    # 前 20 个直连 API（clean_sites 已按延迟排好序，type=1 的在前）
    sites = merged.get("sites", [])
    direct = [s for s in sites if s.get("type") == 1]
    elder["sites"] = direct[:20]
    # 国内直播：去掉国际频道
    lives = [x for x in merged.get("lives", [])
             if isinstance(x, dict) and x.get("name") != "国际频道"]
    elder["lives"] = lives
    elder["parses"] = merged.get("parses", [])[:5]  # 只留前 5 个解析
    path = os.path.join(OUTPUT_DIR, "elder.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(elder, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[elder] 长辈版：{len(elder['sites'])} 站，{len(elder['lives'])} 直播 -> output/elder.json")
    return elder


def build_new_releases(merged, top_n=5):
    """从最快的几个直连 API 抓最新上线影片，汇总成 new.json。"""
    sites = merged.get("sites", [])
    direct = [s for s in sites if s.get("type") == 1 and (s.get("api") or "").startswith("http")]
    movies = []
    seen = set()
    for s in direct[:top_n]:
        api = s["api"]
        sep = "&" if "?" in api else "?"
        url = f"{api}{sep}ac=list"
        try:
            r = requests.get(url, timeout=6, headers={"User-Agent": USER_AGENT})
            if r.status_code >= 400:
                continue
            data = r.json()
            for item in (data.get("list") or [])[:10]:
                name = (item.get("vod_name") or item.get("name") or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                t = item.get("vod_time") or ""
                year = t[:4] if len(t) >= 4 else ""
                movies.append({
                    "name": name,
                    "year": year,
                    "type": item.get("type_name", ""),
                    "remark": item.get("vod_remarks", ""),
                    "time": t,
                    "from": s.get("name", ""),
                })
        except Exception:
            continue
    movies.sort(key=lambda x: x.get("year", ""), reverse=True)
    path = os.path.join(OUTPUT_DIR, "new.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "movies": movies[:50]},
                  f, ensure_ascii=False, indent=2)
    print(f"[new] 最新上线 {len(movies)} 部 -> output/new.json")
    return movies


def merge(fetched):
    """fetched: [(id, name, data)]"""
    if not fetched:
        return None
    _, _, base = fetched[0]
    merged = {}
    skip = {"sites", "lives", "parses", "doh", "rules", "flags", "exts", "ads"}
    for k, v in base.items():
        if k not in skip:
            merged[k] = v
    merged["warningText"] = (
        f"由 {len(fetched)} 个公开源自动聚合，每日更新，仅供学习交流"
    )

    seen = set()
    sites = []
    for sid, _name, data in fetched:
        for s in data.get("sites", []) or []:
            if not isinstance(s, dict):
                continue
            key = s.get("key") or s.get("name") or json.dumps(s, ensure_ascii=False, sort_keys=True)
            new_key = key
            if key in seen:
                new_key = f"{sid}_{key}"
            if new_key in seen:
                continue
            seen.add(new_key)
            if new_key != key:
                s = dict(s)
                s["key"] = new_key
            sites.append(s)
    merged["sites"] = sites

    # lives 一律不合并：只保留脚本自己抓的官方直播源（央视 + 卫视）
    merged["lives"] = []
    for field in ("parses", "doh", "rules", "flags"):
        seen2 = set()
        out = []
        for _sid, _name, data in fetched:
            for item in data.get(field, []) or []:
                ident = None
                if isinstance(item, dict):
                    ident = item.get("name") or item.get("url") or json.dumps(item, ensure_ascii=False, sort_keys=True)
                else:
                    ident = str(item)
                if ident in seen2:
                    continue
                seen2.add(ident)
                out.append(item)
        merged[field] = out
    return merged


def main():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    updated_at = now.strftime("%Y-%m-%d %H:%M:%S")

    fetched = []
    status = []
    for src in cfg["sources"]:
        sid = src["id"]
        name = src["name"]
        data = None
        used_url = None
        err = None
        for url in src["urls"]:
            try:
                print(f"[{sid}] 尝试 {url} ...")
                data = fetch(url)
                used_url = url
                break
            except Exception as e:
                err = str(e)
                print(f"  失败: {e}")
                time.sleep(1)
        if data is None:
            # 尝试用上次成功的缓存
            cache_path = os.path.join(OUTPUT_DIR, f"{sid}.json")
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    status.append({"id": sid, "name": name, "ok": True, "cached": True, "error": None})
                    fetched.append((sid, name, data))
                    print(f"[{sid}] 沿用缓存")
                    continue
                except Exception:
                    pass
            status.append({"id": sid, "name": name, "ok": False, "cached": False, "error": err})
            print(f"[{sid}] 全部失败: {err}")
            continue

        data, fixed_n = fix_ext_strings(data)
        data = normalize_types(data)
        print(f"[{sid}] 成功，站点 {len(data.get('sites', []))}，修 ext {fixed_n}")

        # 单源落盘（放 _sources/ 子目录，仅用于排错，主功能不依赖）
        src_path = os.path.join(SOURCES_DIR, f"{sid}.json")
        with open(src_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

        status.append({"id": sid, "name": name, "ok": True, "cached": False, "used_url": used_url})
        fetched.append((sid, name, data))

    # 聚合
    merged = merge(fetched)
    if merged:
        # 清空所有旧直播源，只保留央视/卫视
        merged["lives"] = []
        cctv = None
        live_path = os.path.join(OUTPUT_DIR, "cctv_live.txt")
        if REFRESH_LIVE:
            print("[live] 今天刷新直播源")
            cctv = build_cctv_live()
        else:
            print("[live] 非刷新日，沿用现有直播清单")
        if not cctv and os.path.exists(live_path):
            # 没重抓或重抓失败：只要旧文件还在，就继续挂上去，别让直播入口消失
            cctv = {
                "name": "央视直播",
                "url": "https://lsx9988.github.io/my-tvbox-cfg/output/cctv_live.txt",
                "group": "央视",
            }
            rows = [x.strip() for x in open(live_path, encoding="utf-8")
                    if x.strip() and not x.strip().endswith("#genre#")]
            chans = set(x.split(",", 1)[0] for x in rows)
            cctv_cnt = len([n for n in chans if n.startswith("CCTV")])
            sat_cnt = len([n for n in chans if not n.startswith("CCTV")
                           and n not in ("央视频道", "卫视频道")])
            globals()["_CCTV_PROFILE"] = (cctv_cnt, sat_cnt, ("-", 0))
            print("[live] 沿用 %d 台 / %d 条线路" % (len(chans), len(rows)))
        if cctv:
            merged["lives"].append(cctv)
        # 清洗直播列表（保留刚加的央视条目）
        merged["lives"] = clean_lives(merged.get("lives", []))
        # 清洗点播站点（只剔死 API，JS 爬虫保留）
        merged["sites"], site_speed = clean_sites(merged.get("sites", []))
        # 强制壁纸：深蓝渐变暗色图，保证文字可读
        merged["wallpaper"] = "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=1920&q=80"

        # 首页顶部提示：更新时间 + 站点数 + 每日寄语
        QUOTES = [
            "今天也要开心哦", "慢慢来，比较快", "保持热爱，奔赴山海",
            "你比想象中更勇敢", "明天会更好", "行动是治愈焦虑的良药",
            "先完成，再完美", "做难而正确的事", "认真生活，慢慢相遇",
            "所有的美好都在路上", "别怕，你已经在发光了", "日拱一卒，功不唐捐",
            "健康第一，其他都是锦上添花", "少熬夜，多喝热水", "今天的努力是明天的底气",
            "保持好奇，持续学习", "简单的事情重复做", "加油，你是最棒的",
            "生活总会给你答案", "把日子过成想要的样子", "不负时光，不负自己",
            "心静如水，遇事不慌", "一步一个脚印", "相信相信的力量",
            "感恩当下，期待未来", "好好吃饭，好好睡觉", "慢慢来，谁还没有一个努力的过程",
            "今天也是值得期待的一天", "你只管努力，剩下的交给时间",
        ]
        today = time.strftime("%Y-%m-%d")
        quote = QUOTES[hash(today) % len(QUOTES)]
        n_sites = len(merged.get("sites", []))
        n_lives = len(merged.get("lives", []))
        prof = globals().get("_CCTV_PROFILE")
        if prof and prof[1]:
            tail = f"{prof[0]}央视+{prof[1]}卫视"
        elif prof:
            tail = f"{prof[0]}央视台"
        else:
            tail = f"{n_lives}直播入口"
        banner = f"📅 {today} 更新 | 点播 {n_sites} 站 | 直播 {tail} | 今日寄语：{quote}"
        # FongMi 只认 notice（配置加载时弹一次长 Toast），warningText 它不读
        merged["notice"] = banner
        merged["warningText"] = banner
        print(f"[banner] {banner}")

        # 再次规范化 + 质量门：只要还有一处类型混合，FongMi 就会整份配置解析失败
        merged = normalize_types(merged)
        conflicts = check_type_conflicts(merged)
        if conflicts:
            print("!! 类型冲突未清除，这份配置会让 FongMi 报「配置取得失败」：")
            for f, k, c in conflicts:
                print("   %s.%s -> %s" % (f, k, c))
            sys.exit(1)

        # 兜底：可达站点过少说明这次探测整体异常（境外机房/源站挂了），保留旧文件别覆盖
        if len(merged.get("sites", [])) < 100 and os.path.exists(os.path.join(OUTPUT_DIR, "tvbox_new.json")):
            print("[guard] 可用站点过少（%d），保留上一次的 tvbox_new.json"
                  % len(merged.get("sites", [])))
            return

        # 主配置：tvbox_new.json（GitHub Pages 入口）
        new_path = os.path.join(OUTPUT_DIR, "tvbox_new.json")
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
        print("聚合完成：%d 站，%d 直播（类型校验通过）" % (
            len(merged.get("sites", [])), len(merged.get("lives", []))))

        # 额外按类型拆分输出，方便在仓库里直接浏览（FongMi 仍只用 tvbox_new.json）
        with open(os.path.join(OUTPUT_DIR, "sites.json"), "w", encoding="utf-8") as f:
            json.dump({"sites": merged.get("sites", [])}, f,
                      ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(OUTPUT_DIR, "lives.json"), "w", encoding="utf-8") as f:
            json.dump({"lives": merged.get("lives", [])}, f,
                      ensure_ascii=False, separators=(",", ":"))
        print("已拆分输出 sites.json / lives.json")

        # 清理 output 目录里的旧文件，只保留白名单
        KEEP = {
            "tvbox_new.json", "sites.json", "lives.json",
            "cctv_live.txt", "status.json", "多仓订阅.json",
        }
        removed = []
        for fn in os.listdir(OUTPUT_DIR):
            fp = os.path.join(OUTPUT_DIR, fn)
            if os.path.isfile(fp) and fn not in KEEP:
                os.remove(fp)
                removed.append(fn)
            elif os.path.isdir(fp) and fn != "_sources":
                # 保留 _sources 目录（原始抓取缓存），其他子目录删掉
                import shutil
                shutil.rmtree(fp, ignore_errors=True)
                removed.append(fn + "/")
        if removed:
            print(f"[cleanup] 删除旧文件：{', '.join(removed)}")

    # 多仓订阅（给影视仓用）
    repo = os.environ.get("GITHUB_REPOSITORY", "lsx9988/my-tvbox-cfg")
    sub = {"urls": []}
    for s in status:
        if s["ok"]:
            sub["urls"].append({
                "name": s["name"],
                "url": f"https://gh-proxy.com/https://raw.githubusercontent.com/{repo}/main/output/{s['id']}.json"
            })
    with open(os.path.join(OUTPUT_DIR, "多仓订阅.json"), "w", encoding="utf-8") as f:
        json.dump(sub, f, ensure_ascii=False, indent=2)

    # 状态 JSON
    with open(os.path.join(OUTPUT_DIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump({"updated_at": updated_at, "sources": status}, f, ensure_ascii=False, indent=2)

    # README 更新（完整生成：状态 + 速率表）
    ok_count = sum(1 for s in status if s["ok"])
    total = len(status)
    site_count = len(merged.get("sites", []))
    live_count = len(merged.get("lives", []))
    readme_path = os.path.join(ROOT, "README.md")

    # 生成状态块
    status_lines = [
        f"> 🔄 最近更新：{updated_at}（北京时间） · 成功 **{ok_count}/{total}** 个源 · 共 **{site_count}** 站 **{live_count}** 直播",
        "",
        "| 源 | 状态 |",
        "| --- | --- |",
    ]
    for s in status:
        if s.get("cached"):
            status_lines.append(f"| {s['name']} | 📦 缓存 |")
        elif s["ok"]:
            status_lines.append(f"| {s['name']} | ✅ |")
        else:
            err = (s.get("error") or "")[:40].replace("|", "/")
            status_lines.append(f"| {s['name']} | ❌ {err} |")

    # 生成点播速率表（前15，带真实速度）
    speed_map = {name: dt for name, dt in site_speed} if site_speed else {}
    site_lines = ["", "### 点播源 TOP 15（按速度排序）", "", "| 排名 | 名称 | 延迟 |", "| :---: | --- | :---: |"]
    for i, s in enumerate(merged.get("sites", [])[:15]):
        raw_name = s.get("name", "?")
        # 清理名字：去掉 | 和多余前缀，避免表格错乱
        name = raw_name.replace("|", "").replace("影视", "").replace("️", "").strip()
        if not name:
            name = raw_name[:10]
        dt = speed_map.get(raw_name)
        speed_str = f"{dt}ms" if dt else "爬虫"
        site_lines.append(f"| {i+1} | {name} | {speed_str} |")

    # 生成直播部分：央视官网直连，附最快频道实测延迟
    live_lines = ["", "### 央视直播（官网直连）", "", "| 项目 | 数量 | 最快频道 | 延迟 |", "| :---: | :---: | --- | :---: |"]
    tv_profile = globals().get("_CCTV_PROFILE")
    if tv_profile:
        cctv_cnt, tv_cnt, fastest = tv_profile
        if fastest[1]:
            live_lines.append(f"| 央视频道 | {cctv_cnt} | {fastest[0]} | {fastest[1]}ms |")
        else:
            live_lines.append(f"| 央视频道 | {cctv_cnt} | 沿用上周清单 | — |")
        if tv_cnt:
            live_lines.append(f"| 卫视频道 | {tv_cnt} | — | — |")
        live_lines.append("")
        if tv_cnt:
            live_lines.append(
                f"> 央视 **{cctv_cnt}** 个台直连央视官网（tv.cctv.com）CDN，不依赖任何第三方；"
                f"卫视 **{tv_cnt}** 个用的是运营商 IPTV 公网转播地址（各卫视官网实测不提供公开 m3u8）。"
                "完整列表见 `cctv_live.txt`")
        else:
            live_lines.append(
                f"> 共 **{cctv_cnt}** 个台，直接取央视官网（tv.cctv.com）的播放地址，"
                "不依赖任何第三方搬运站；完整列表见 `cctv_live.txt`")
    else:
        for i, l in enumerate(merged.get("lives", [])):
            lname = l.get("name", "?").replace("|", "").strip()
            live_lines.append(f"| {lname} | — | — | — |")

    block = "<!-- STATUS_START -->\n" + "\n".join(status_lines) + "\n" + "\n".join(site_lines) + "\n" + "\n".join(live_lines) + "\n<!-- STATUS_END -->"

    # 读现有 README，替换状态块
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()
        import re
        start = "<!-- STATUS_START -->"
        end = "<!-- STATUS_END -->"
        if start in readme and end in readme:
            readme = re.sub(re.escape(start) + r".*?" + re.escape(end), block, readme, flags=re.S)
        else:
            # 没有标记，追加到末尾
            readme += "\n\n" + block
        # 顶部徽章跟着真实数据走，别留写死的旧数字
        prof2 = globals().get("_CCTV_PROFILE")
        key = f"{site_count} 站"
        live_n = (prof2[0] + prof2[1]) if prof2 else live_count
        readme = re.sub(r"badge/sites-[^)]*", "badge/sites-" + urllib.parse.quote(key) + "-green", readme)
        readme = re.sub(r"badge/live-[^)]*", "badge/live-" + urllib.parse.quote(str(live_n) + " 台") + "-orange", readme)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme)
    else:
        # 没有 README，生成一个简单的
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# TVBox Config\n\n{block}\n")


if __name__ == "__main__":
    main()
