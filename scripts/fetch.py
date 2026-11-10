# -*- coding: utf-8 -*-
"""Daily aggregate: VOD + LIVE, FongMi v5.x compatible."""
import json, os, ssl, sys, urllib.request
from datetime import datetime, timezone, timedelta

VOD_SEEDS = [
    "https://raw.githubusercontent.com/dimogu/tvbox-merged/main/tvbox-cn-fast.json",
    "https://raw.githubusercontent.com/dimogu/tvbox-merged/main/tvbox-stable7.json",
    "https://raw.githubusercontent.com/Daiwangyang/tvbox-probe/main/my.json",
]
LIVE_SEEDS = [
    "https://raw.githubusercontent.com/ouyushan/tvbox-cfg/main/config/live.json",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))

def fix_ext(item):
    """FongMi v5.x expects ext to be object, not JSON-encoded string."""
    if isinstance(item, dict):
        e = item.get("ext")
        if isinstance(e, str):
            try:
                item["ext"] = json.loads(e)
            except Exception:
                item["ext"] = {}
    return item

def merge_list(items):
    seen, out = set(), []
    for it in items:
        if not isinstance(it, dict):
            continue
        k = it.get("key") or it.get("name") or it.get("url")
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(fix_ext(it))
    return out

def main():
    sites, lives, parsers, flags, rules = [], [], [], [], []
    parses = []
    header = {}
    for url in VOD_SEEDS:
        try:
            cfg = fetch(url)
            if not header:
                header = {k: v for k, v in cfg.items()
                          if k not in ("sites","lives","parsers","parses","flags","rules","ext")}
            sites += cfg.get("sites", [])
            lives += cfg.get("lives", [])
            parsers += cfg.get("parsers", [])
            parses += cfg.get("parses", [])
            flags += cfg.get("flags", [])
            rules += cfg.get("rules", [])
            print(f"[vod] OK {url}")
        except Exception as e:
            print(f"[vod][warn] {url}: {e}", file=sys.stderr)
    for url in LIVE_SEEDS:
        try:
            cfg = fetch(url)
            lives += cfg.get("lives", [])
            print(f"[live] OK {url}")
        except Exception as e:
            print(f"[live][warn] {url}: {e}", file=sys.stderr)

    cfg = dict(header)
    cfg["sites"] = merge_list(sites)
    cfg["lives"] = merge_list(lives)
    cfg["parsers"] = merge_list(parsers)
    cfg["parses"] = merge_list(parses)
    cfg["flags"] = merge_list(flags)
    cfg["rules"] = merge_list(rules)
    # FongMi v5.x requires root ext object
    cfg["ext"] = {"spider": ""}
    cfg["update"] = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")

    os.makedirs("out", exist_ok=True)
    with open("out/config.json","w",encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"[done] sites={len(cfg['sites'])} lives={len(cfg['lives'])} parsers={len(cfg['parsers'])} parses={len(cfg['parses'])}")

if __name__ == "__main__":
    main()
