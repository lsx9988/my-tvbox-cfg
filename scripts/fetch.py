# -*- coding: utf-8 -*-
"""
每日聚合：VOD 点播源 + 直播源 + 解析规则
输出 config.json（FongMi/TV 可直接订阅）
"""
import json, os, ssl, sys, urllib.request
from datetime import datetime, timezone, timedelta

# 上游种子：都是每天自动探活的活跃仓库
VOD_SEEDS = [
    "https://raw.githubusercontent.com/dimogu/tvbox-merged/main/tvbox-cn-fast.json",
    "https://raw.githubusercontent.com/dimogu/tvbox-merged/main/tvbox-stable7.json",
    "https://raw.githubusercontent.com/Daiwangyang/tvbox-probe/main/my.json",
]
LIVE_SEEDS = [
    "https://raw.githubusercontent.com/Supprise0901/TVBox_live/main/live.json",
    "https://raw.githubusercontent.com/ouyushan/tvbox-cfg/main/config/live.json",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))

def merge_list(items, key_fields=("key", "name", "url")):
    """按 key/name/url 去重，先到先得"""
    seen, out = set(), []
    for it in items:
        if not isinstance(it, dict):
            continue
        k = it.get("key") or it.get("name") or it.get("url")
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out

def main():
    sites, lives, parsers, flags, rules = [], [], [], [], []
    header = {}

    for url in VOD_SEEDS:
        try:
            cfg = fetch(url)
            if not header:
                header = {k: v for k, v in cfg.items()
                          if k not in ("sites", "lives", "parsers", "flags", "rules")}
            sites += cfg.get("sites", [])
            parsers += cfg.get("parsers", [])
            flags += cfg.get("flags", [])
            rules += cfg.get("rules", [])
            print(f"[vod] OK {url.split('/')[-1]}")
        except Exception as e:
            print(f"[vod][warn] {url}: {e}", file=sys.stderr)

    for url in LIVE_SEEDS:
        try:
            cfg = fetch(url)
            lives += cfg.get("lives", [])
            # 有些直播配置把直播直接当 sites 给
            for s in cfg.get("sites", []):
                if "live" in str(s.get("type", "")).lower() or "直播" in str(s.get("name", "")):
                    pass
            print(f"[live] OK {url.split('/')[-1]}")
        except Exception as e:
            print(f"[live][warn] {url}: {e}", file=sys.stderr)

    cfg = dict(header)
    cfg["sites"] = merge_list(sites)
    cfg["lives"] = merge_list(lives)
    cfg["parsers"] = merge_list(parsers)
    cfg["flags"] = merge_list(flags)
    cfg["rules"] = merge_list(rules)
    cfg["update"] = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")

    os.makedirs("out", exist_ok=True)
    with open("out/config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"[done] sites={len(cfg['sites'])} lives={len(cfg['lives'])} "
          f"parsers={len(cfg['parsers'])} flags={len(cfg['flags'])}")

if __name__ == "__main__":
    main()
