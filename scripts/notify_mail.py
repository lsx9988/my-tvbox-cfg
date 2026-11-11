# -*- coding: utf-8 -*-
"""更新完成后发一封汇总邮件到指定邮箱。

依赖两个仓库 Secret：
    MAIL_USER  发件邮箱（QQ 邮箱地址）
    MAIL_PASS  该邮箱的 SMTP 授权码（不是登录密码）
    MAIL_TO    收件地址，可选，默认等于 MAIL_USER

任一缺失时静默跳过，不影响主流程。
"""
import json
import os
import re
import smtplib
import ssl
import sys
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465

USER = (os.environ.get("MAIL_USER") or "").strip()
PASS = (os.environ.get("MAIL_PASS") or "").strip()
TO = (os.environ.get("MAIL_TO") or "").strip() or USER
JOB = (os.environ.get("JOB_STATUS") or "success").strip()

if not USER or not PASS:
    print("[mail] 未配置 MAIL_USER / MAIL_PASS，跳过发送")
    sys.exit(0)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")


def read_json(name, default):
    path = os.path.join(OUT, name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print("[mail] 读取 %s 失败: %s" % (name, exc))
        return default


status = read_json("status.json", {})
conf = read_json("tvbox_new.json", {})
info = read_json("lives.json", {})

updated = status.get("updated_at") or ""
sources = status.get("sources") or []
ok_src = [s for s in sources if s.get("ok")]
bad_src = [s for s in sources if not s.get("ok")]

n_sites = len(conf.get("sites") or [])
n_lives = len(conf.get("lives") or [])

# 直播清单统计
cctv_cnt = sat_cnt = line_cnt = 0
live_file = os.path.join(OUT, "cctv_live.txt")
if os.path.exists(live_file):
    rows = []
    with open(live_file, encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t and not t.endswith("#genre#"):
                rows.append(t)
    line_cnt = len(rows)
    names = set(r.split(",", 1)[0] for r in rows)
    names.discard("央视频道")
    names.discard("卫视频道")
    cctv_cnt = len([n for n in names if n.startswith("CCTV")])
    sat_cnt = len([n for n in names if not n.startswith("CCTV")])

# 从 README 里抠出点播速度榜前几名
top_rows = []
readme_path = os.path.join(BASE, "README.md")
if os.path.exists(readme_path):
    text = open(readme_path, encoding="utf-8").read()
    block = re.search(r"### 点播源 TOP.*?\n(.+?)\n\n", text, re.S)
    if block:
        for line in block.group(1).splitlines():
            if line.startswith("|") and "---" not in line and "排名" not in line:
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 4:
                    top_rows.append(cells)
                    if len(top_rows) >= 5:
                        break

quote = ""
notice = conf.get("notice") or conf.get("warningText") or ""
m = re.search(r"今日寄语：(.+)", notice)
if m:
    quote = m.group(1).strip()

subject = "[TVBox] %s %s · %d 站 / %d 台直播" % (
    updated[:10] or "更新", "完成" if JOB == "success" else "失败", n_sites, cctv_cnt + sat_cnt)

ok_chip = "".join(
    '<span style="display:inline-block;margin:2px 6px 2px 0;padding:2px 8px;'
    'border-radius:10px;background:#e8f5e9;color:#2e7d32;font-size:13px">%s</span>' % s.get("name", "")
    for s in ok_src
)
bad_chip = "".join(
    '<span style="display:inline-block;margin:2px 6px 2px 0;padding:2px 8px;'
    'border-radius:10px;background:#fdecea;color:#c62828;font-size:13px">%s</span>' % s.get("name", "")
    for s in bad_src
)

top_html = ""
if top_rows:
    body = "".join(
        "<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>%s</td>"
        "<td style='padding:6px 10px;border-bottom:1px solid #eee'>%s</td>"
        "<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>%s</td></tr>"
        % (r[0], r[1], r[3] if len(r) > 3 else "")
        for r in top_rows
    )
    top_html = (
        "<h3 style='margin:22px 0 8px;font-size:15px;color:#333'>点播源速度排名</h3>"
        "<table style='border-collapse:collapse;width:100%;font-size:13px;color:#444'>"
        "<tr style='background:#fafafa'>"
        "<th style='padding:6px 10px;text-align:left;border-bottom:1px solid #ddd'>排名</th>"
        "<th style='padding:6px 10px;text-align:left;border-bottom:1px solid #ddd'>名称</th>"
        "<th style='padding:6px 10px;text-align:right;border-bottom:1px solid #ddd'>速度</th>"
        "</tr>%s</table>" % body
    )

html = """<!DOCTYPE html>
<html><body style="margin:0;padding:24px;background:#f4f5f7;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
<div style="max-width:620px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;
            box-shadow:0 2px 10px rgba(0,0,0,.06)">
  <div style="padding:22px 26px;background:%(head_bg)s;color:#fff">
    <div style="font-size:19px;font-weight:600">影视配置更新%(state)s</div>
    <div style="margin-top:6px;font-size:13px;opacity:.92">%(updated)s（北京时间）</div>
  </div>
  <div style="padding:22px 26px">
    <table style="width:100%%;font-size:14px;color:#333;border-collapse:collapse">
      <tr>
        <td style="padding:8px 0">点播站点</td>
        <td style="padding:8px 0;text-align:right;font-weight:600">%(n_sites)d 站</td>
      </tr>
      <tr>
        <td style="padding:8px 0">直播频道</td>
        <td style="padding:8px 0;text-align:right;font-weight:600">%(n_ch)d 台（央视 %(cctv)d + 卫视 %(sat)d）</td>
      </tr>
      <tr>
        <td style="padding:8px 0">直播线路</td>
        <td style="padding:8px 0;text-align:right;font-weight:600">%(lines)d 条</td>
      </tr>
      <tr>
        <td style="padding:8px 0">聚合源</td>
        <td style="padding:8px 0;text-align:right;font-weight:600">成功 %(ok)d / %(total)d</td>
      </tr>
    </table>
    <div style="margin-top:16px">
      %(ok_chip)s
      %(bad_chip)s
    </div>
    %(top)s
    %(quote_block)s
    <div style="margin-top:24px;padding-top:18px;border-top:1px solid #eee;font-size:13px;color:#666">
      手机端配置地址（复制到 App 里粘上）：
      <div style="margin-top:8px;padding:10px 12px;background:#f7f8fa;border-radius:6px;
                  word-break:break-all;font-family:Consolas,monospace;font-size:12px;color:#333">
        https://lsx9988.github.io/my-tvbox-cfg/output/tvbox_new.json
      </div>
      <div style="margin-top:10px">
        直播清单：
        <a href="https://lsx9988.github.io/my-tvbox-cfg/output/cctv_live.txt" style="color:#1976d2">
          cctv_live.txt</a>
      </div>
    </div>
  </div>
</div>
</body></html>""" % {
    "head_bg": "#2e7d32" if JOB == "success" else "#c62828",
    "state": "" if JOB == "success" else "（失败）",
    "updated": updated or "未知时间",
    "n_sites": n_sites,
    "n_ch": cctv_cnt + sat_cnt,
    "cctv": cctv_cnt,
    "sat": sat_cnt,
    "lines": line_cnt,
    "ok": len(ok_src),
    "total": len(sources),
    "ok_chip": ok_chip,
    "bad_chip": bad_chip,
    "top": top_html,
    "quote_block": (
        "<div style='margin-top:22px;padding:14px 16px;background:#f7f8fa;border-radius:8px;"
        "font-size:14px;color:#444'>今日寄语：%s</div>" % quote
    ) if quote else "",
}

msg = MIMEText(html, "html", "utf-8")
msg["Subject"] = Header(subject, "utf-8")
msg["From"] = formataddr((str(Header("TVBox 自动更新", "utf-8")), USER))
msg["To"] = TO

try:
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=30) as svr:
        svr.login(USER, PASS)
        svr.sendmail(USER, [TO], msg.as_string())
    print("[mail] 已发送到 %s" % TO)
except Exception as exc:
    print("[mail] 发送失败: %s" % exc)
    # 邮件发不出去不该让整个任务变红，退出码仍为 0
