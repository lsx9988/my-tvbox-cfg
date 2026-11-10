# -*- coding: utf-8 -*-
"""Daily aggregate: mirror dimogu's working structure exactly."""
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
    if isinstance(item, dict):
        e = item.get("ext")
        if isinstance(e, str):
            try: item["ext"] = json.loads(e)
            except Exception: item.pop("ext", None)
    return item

def merge_list(items):
    seen, out = set(), []
    for it in items:
        if not isinstance(it, dict): continue
        k = it.get("key") or it.get("name") or it.get("url")
        if not k or k in seen: continue
        seen.add(k)
        out.append(fix_ext(it))
    return out

def main():
    sites, lives, parses = [], [], []
    meta = {}
    for url in VOD_SEEDS:
        try:
            cfg = fetch(url)
            if not meta:
                meta = cfg.get("_meta", {})
            sites += cfg.get("sites", [])
            lives += cfg.get("lives", [])
            parses += cfg.get("parses", [])
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

    # Match dimogu's structure exactly: only parses/lives/_meta/sites
    out = {
        "parses": merge_list(parses),
        "lives": merge_list(lives),
        "_meta": meta,
        "sites": merge_list(sites),
    }
    os.makedirs("out", exist_ok=True)
    with open("out/config.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] sites={len(out['sites'])} lives={len(out['lives'])} parses={len(out['parses'])}")

if __name__ == "__main__":
    main()
