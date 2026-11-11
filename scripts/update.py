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
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

        # 单源落盘
        src_path = os.path.join(OUTPUT_DIR, f"{sid}.json")
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
                merged["lives"].insert(0, intl)

        # 再次规范化 + 质量门：只要还有一处类型混合，FongMi 就会整份配置解析失败
        merged = normalize_types(merged)
        conflicts = check_type_conflicts(merged)
        if conflicts:
            print("!! 类型冲突未清除，这份配置会让 FongMi 报「配置取得失败」：")
            for f, k, c in conflicts:
                print("   %s.%s -> %s" % (f, k, c))
            sys.exit(1)

        merged_path = os.path.join(OUTPUT_DIR, "config.json")
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
        # tvbox.json：相同内容，换一个文件名作为主入口。
        # 原因：jsDelivr 对同一路径有最长 12 小时缓存且忽略 query 参数，
        # 用新文件名可以让 CDN 缓存键立即刷新，避免用户长时间拉到旧配置。
        entry_path = os.path.join(OUTPUT_DIR, "tvbox.json")
        with open(entry_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
        # 根目录也放一份（FongMi 直接用）
        root_path = os.path.join(ROOT, "config.json")
        with open(root_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
        print("聚合完成：%d 站，%d 直播（类型校验通过）" % (
            len(merged.get("sites", [])), len(merged.get("lives", []))))

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

    # README 更新
    ok_count = sum(1 for s in status if s["ok"])
    total = len(status)
    readme_path = os.path.join(ROOT, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()
        start = "<!-- STATUS_START -->"
        end = "<!-- STATUS_END -->"
        if start in readme and end in readme:
            lines = [f"> 🔄 最近更新：{updated_at}（北京时间） · 成功 **{ok_count}/{total}** 个源", "",
                     "| 源 | 状态 | 地址 |", "| --- | --- | --- |"]
            for s in status:
                if s.get("cached"):
                    lines.append(f"| {s['name']} | 📦 缓存 | 上次成功 |")
                elif s["ok"]:
                    lines.append(f"| {s['name']} | ✅ | `{s.get('used_url','')}` |")
                else:
                    err = (s.get("error") or "")[:60].replace("|", "/")
                    lines.append(f"| {s['name']} | ❌ | {err} |")
            block = start + "\n" + "\n".join(lines) + "\n" + end
            import re
            readme = re.sub(re.escape(start) + r".*?" + re.escape(end), block, readme, flags=re.S)
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme)


if __name__ == "__main__":
    main()
