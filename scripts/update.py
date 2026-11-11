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
        merged_path = os.path.join(OUTPUT_DIR, "config.json")
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
        # 根目录也放一份（FongMi 直接用）
        root_path = os.path.join(ROOT, "config.json")
        with open(root_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
        print(f"聚合完成：{len(merged.get('sites', []))} 站，{len(merged.get('lives', []))} 直播")

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
