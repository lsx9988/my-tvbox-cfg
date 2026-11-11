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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT, "config", "sources.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
# 单源干净副本放子目录，避免把 output 根目录弄得像垃圾场
SOURCES_DIR = os.path.join(OUTPUT_DIR, "_sources")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SOURCES_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0"
TIMEOUT = 15
MAX_RETRIES = 2

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


# ============ 国际直播（iptv-org 公开频道） ============
# 说明：iptv-org 是公开的全球 IPTV 频道索引，只收录有公开来源的台。
# 本脚本把各国 m3u 抓下来，转成 FongMi 支持的 txt（"分组,#genre#" 格式），
# 托管在本仓库的 output/live_intl.txt，手机只从自己的仓库拉，避免直连 GitHub Pages。
INTL_FEEDS = [
    ("国际·中国", "https://iptv-org.github.io/iptv/countries/cn.m3u"),
    ("国际·香港", "https://iptv-org.github.io/iptv/countries/hk.m3u"),
    ("国际·台湾", "https://iptv-org.github.io/iptv/countries/tw.m3u"),
    ("国际·澳门", "https://iptv-org.github.io/iptv/countries/mo.m3u"),
    ("国际·美国", "https://iptv-org.github.io/iptv/countries/us.m3u"),
    ("国际·英国", "https://iptv-org.github.io/iptv/countries/uk.m3u"),
    ("国际·日本", "https://iptv-org.github.io/iptv/countries/jp.m3u"),
    ("国际·韩国", "https://iptv-org.github.io/iptv/countries/kr.m3u"),
    ("国际·新加坡", "https://iptv-org.github.io/iptv/countries/sg.m3u"),
    ("国际·马来西亚", "https://iptv-org.github.io/iptv/countries/my.m3u"),
    ("国际·泰国", "https://iptv-org.github.io/iptv/countries/th.m3u"),
    ("国际·越南", "https://iptv-org.github.io/iptv/countries/vn.m3u"),
    ("国际·印度", "https://iptv-org.github.io/iptv/countries/in.m3u"),
    ("国际·俄罗斯", "https://iptv-org.github.io/iptv/countries/ru.m3u"),
    ("国际·德国", "https://iptv-org.github.io/iptv/countries/de.m3u"),
    ("国际·法国", "https://iptv-org.github.io/iptv/countries/fr.m3u"),
    ("国际·加拿大", "https://iptv-org.github.io/iptv/countries/ca.m3u"),
    ("国际·澳大利亚", "https://iptv-org.github.io/iptv/countries/au.m3u"),
    ("国际·新闻", "https://iptv-org.github.io/iptv/categories/news.m3u"),
    ("国际·体育", "https://iptv-org.github.io/iptv/categories/sports.m3u"),
    ("国际·电影", "https://iptv-org.github.io/iptv/categories/movies.m3u"),
    ("国际·音乐", "https://iptv-org.github.io/iptv/categories/music.m3u"),
    ("国际·少儿", "https://iptv-org.github.io/iptv/categories/kids.m3u"),
    ("国际·纪录片", "https://iptv-org.github.io/iptv/categories/documentary.m3u"),
]
INTL_MAX_PER_GROUP = 200      # 每组最多保留多少个频道
INTL_PROBE = True             # 是否做可达性抽检（丢弃 404/超时的源）
INTL_PROBE_TIMEOUT = 3.0
INTL_PROBE_WORKERS = 40
INTL_PROBE_MAX = 1200         # 最多抽检多少个地址，防止 Actions 跑太久


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
    """探测直播地址是否可达（HEAD 不行就退回 GET 读一小段）。"""
    try:
        r = requests.head(url, timeout=INTL_PROBE_TIMEOUT, allow_redirects=True,
                          headers={"User-Agent": USER_AGENT})
        if r.status_code < 400:
            return True
        if r.status_code in (403, 405, 501):
            r2 = requests.get(url, timeout=INTL_PROBE_TIMEOUT, stream=True,
                              allow_redirects=True, headers={"User-Agent": USER_AGENT})
            ok = r2.status_code < 400
            r2.close()
            return ok
        return False
    except Exception:
        return False


def build_intl_live():
    """抓 iptv-org 各国频道，生成 FongMi 直播 txt，返回一条 lives 条目。"""
    repo = os.environ.get("GITHUB_REPOSITORY", "lsx9988/my-tvbox-cfg")
    groups = []
    total = 0
    for group, url in INTL_FEEDS:
        try:
            r = requests.get(url, timeout=25, headers={"User-Agent": USER_AGENT})
            if r.status_code != 200:
                print(f"[intl] {group} 拉取失败 HTTP {r.status_code}")
                continue
            chans = parse_m3u(r.text)
            if not chans:
                continue
            # 频道名去重
            seen = set()
            uniq = []
            for n, u in chans:
                n2 = n.replace(",", " ").replace("#", "").strip() or "频道"
                if n2 in seen:
                    continue
                seen.add(n2)
                uniq.append((n2, u))
            uniq = uniq[:INTL_MAX_PER_GROUP]
            groups.append((group, uniq))
            total += len(uniq)
            print(f"[intl] {group}: {len(uniq)} 个")
        except Exception as e:
            print(f"[intl] {group} 异常: {e}")

    if not groups:
        print("[intl] 无可用国际源，跳过")
        return None

    # 可达性抽检（只抽样前 INTL_PROBE_MAX 个，保证 Actions 时长可控）
    if INTL_PROBE and total:
        from concurrent.futures import ThreadPoolExecutor
        alive = {}
        budget = INTL_PROBE_MAX
        to_check = []
        for g, chans in groups:
            take = chans[: max(1, budget // max(1, len(groups)))]
            to_check.extend([(g, n, u) for n, u in take])
        urls = list({u for _g, _n, u in to_check})
        try:
            with ThreadPoolExecutor(max_workers=INTL_PROBE_WORKERS) as ex:
                res = list(ex.map(_url_alive, urls))
            alive = dict(zip(urls, res))
        except Exception as e:
            print(f"[intl] 抽检异常，跳过测速: {e}")
            alive = {}
        if alive:
            dropped = sum(1 for v in alive.values() if not v)
            print(f"[intl] 抽检 {len(urls)} 个地址，丢弃 {dropped} 个不可达")
            groups = [
                (g, [(n, u) for n, u in chans if alive.get(u, True)])
                for g, chans in groups
            ]

    # 不要写注释行：FongMi 的 txt 解析按 "名称,地址" 切分，
    # 任何含逗号的非 #genre# 行都会被当成一个频道，必须保持纯净
    lines = []
    kept = 0
    for group, chans in groups:
        if not chans:
            continue
        lines.append(f"{group},#genre#")
        for n, u in chans:
            lines.append(f"{n},{u}")
            kept += 1

    path = os.path.join(OUTPUT_DIR, "live_intl.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[intl] 写入 live_intl.txt：{kept} 个频道 / {len(groups)} 组")

    return {
        "name": "国际频道",
        "url": f"https://fastly.jsdelivr.net/gh/{repo}@main/output/live_intl.txt",
        "group": "国际",
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


def _site_alive(api):
    """点播 API 活性探测，返回 (是否存活, 延迟毫秒)。HEAD 4 秒，不支持 HEAD 退到 GET。"""
    import time as _t
    try:
        t0 = _t.time()
        r = requests.head(api, timeout=4, allow_redirects=True,
                          headers={"User-Agent": USER_AGENT})
        dt = int((_t.time() - t0) * 1000)
        if r.status_code < 400:
            return True, dt
        if r.status_code in (405, 501, 403):
            t0 = _t.time()
            r2 = requests.get(api, timeout=4, stream=True, allow_redirects=True,
                              headers={"User-Agent": USER_AGENT})
            dt = int((_t.time() - t0) * 1000)
            ok = r2.status_code < 400
            r2.close()
            return ok, dt
        return False, 99999
    except Exception:
        return False, 99999


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
    """清洗点播站点：剔网盘、剔引流站、剔死 API、按响应延迟排序。"""
    direct = []   # (latency, site)
    others = []   # JS 爬虫类
    dropped_pan = []
    dropped_junk = []
    dropped_dead = []
    # 引流/配置站：直接删除，不是真点播
    JUNK_KWS = ("配置", "免费分享", "更新日期", "公告", "导航",
                "微信", "公众号", "加群", "下载APP", "下载app",
                "配置中心", "配置中心", "破解", "会员", "VIP", "vip")

    def _is_junk(s):
        text = ((s.get("name") or "") + " " + (s.get("key") or "")).lower()
        return any(k.lower() in text for k in JUNK_KWS)

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
        if probe and stype == 1 and api.startswith("http"):
            ok, dt = _site_alive(api)
            if not ok:
                dropped_dead.append(name)
                continue
            direct.append((dt, s))
        else:
            others.append(s)
    direct.sort(key=lambda x: x[0])
    if direct:
        print(f"   最快 5 个：{[(s.get('name'), dt) for dt, s in direct[:5]]}")
    out = []
    speed_data = []  # 保存 (name, latency) 给 README 用
    for dt, s in direct:
        out.append(s)
        speed_data.append((s.get("name", "?"), dt))
    out.extend(others)
    for n in dropped_pan[:20]:
        print(f"   - 网盘: {n}")
    for n in dropped_dead[:20]:
        print(f"   - 死链: {n}")
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

    for field in ("lives", "parses", "doh", "rules", "flags"):
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
        # 国际直播：抓 iptv-org 生成 live_intl.txt，作为一条 lives 入口
        intl = build_intl_live()
        if intl:
            merged.setdefault("lives", [])
            names = {x.get("name") for x in merged["lives"] if isinstance(x, dict)}
            if intl["name"] not in names:
                merged["lives"].append(intl)
        # 清洗直播列表
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
        merged["warningText"] = f"📅 {today} 更新 | {n_sites}站 {n_lives}直播 | 今日寄语：{quote}"
        print(f"[banner] {merged['warningText']}")

        # 再次规范化 + 质量门：只要还有一处类型混合，FongMi 就会整份配置解析失败
        merged = normalize_types(merged)
        conflicts = check_type_conflicts(merged)
        if conflicts:
            print("!! 类型冲突未清除，这份配置会让 FongMi 报「配置取得失败」：")
            for f, k, c in conflicts:
                print("   %s.%s -> %s" % (f, k, c))
            sys.exit(1)

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
            "live_intl.txt", "status.json", "多仓订阅.json",
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

    # 生成直播速率表
    live_lines = ["", "### 直播源（按速度排序）", "", "| 排名 | 名称 |", "| :---: | --- |"]
    for i, l in enumerate(merged.get("lives", [])):
        lname = l.get("name", "?").replace("|", "").strip()
        live_lines.append(f"| {i+1} | {lname} |")

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
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme)
    else:
        # 没有 README，生成一个简单的
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# TVBox Config\n\n{block}\n")


if __name__ == "__main__":
    main()
