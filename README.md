# My TVBox Config

> 个人自用 TVBox / FongMi 影视配置自动聚合仓库。
> 通过 GitHub Actions 定时抓取公开源、做类型规范化与质量校验后发布，供本人 FongMi / TVBox 类壳应用使用。

![Update](https://img.shields.io/badge/update-every%206h-blue?logo=githubactions)
![Sources](https://img.shields.io/badge/sources-8%20aggregated-green)
![Live](https://img.shields.io/badge/international%20live-2701%20channels-orange)
![License](https://img.shields.io/badge/license-personal%20use-lightgrey)

---

## 推荐配置地址

在 FongMi / TVBox 的「设置 → 配置地址」中，把**点播**和**直播**两个框都填成下面这条：

```
https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox.json
```

> 为什么用 `gcore.jsdelivr.net`：jsDelivr 的 `fastly` 节点对同一文件名有最长 12 小时硬缓存，
> 我推送新版本后它仍会返回旧内容；`gcore` 节点更新及时，已实测可用。
> 仓库 Actions 在每次发布后会自动调用 `purge.jsdelivr.net` 清理缓存。

### 备用入口

| 入口 | 地址 | 用途 |
| --- | --- | --- |
| 主配置（推荐） | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox.json` | 点播 + 直播 同一份 |
| 备用节点 | `https://fastly.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox.json` | 主节点不通时切换 |
| 国际直播单链 | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/live_intl.txt` | 单独挂直播时用 |

---

## 当前聚合状态

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-11 14:12:10（北京时间） · 成功 **5/8** 个源

| 源 | 状态 | 地址 |
| --- | --- | --- |
| 王二小 | ✅ | `https://d.kstore.dev/download/9280/wex.json` |
| 老刘备 | ✅ | `https://raw.liucn.cc/box/m.json` |
| 小马 | ✅ | `https://szyyds.cn/tv/x.json` |
| 讴歌 | ❌ | 403 Client Error: Forbidden for url: http://xn--dkw0c.v.nxog |
| 4K小盒子 | ✅ | `http://xhztv.top/4k.json` |
| 小盒子单仓 | ✅ | `http://xhztv.top/xhz` |
| 拾光多仓 | ❌ | 不是 TVBox 配置（缺 sites/spiders/lives） |
| 挺好分享多仓 | ❌ | 不是 TVBox 配置（缺 sites/spiders/lives） |
<!-- STATUS_END -->

---

## 自动更新机制

| 项目 | 说明 |
| --- | --- |
| 触发频率 | 每 6 小时一次（北京时间 02:00 / 08:00 / 14:00 / 20:00） |
| 手动触发 | 仓库 Actions 页面 → `Daily Update` → `Run workflow` |
| 源失败处理 | 单源失败不影响整体，沿用上一次缓存结果 |
| 缓存清理 | 发布后自动 `purge.jsdelivr.net` |

## 质量保障

聚合脚本对每份源配置做以下处理后才允许发布：

1. **多地址容灾**：每个源配主地址 + 备用地址，中文域名自动 punycode。
2. **类型规范化**：不同源把同一字段写成 int/str 混合（例如 `playerType` 写成 `"2"`），
   FongMi 的 Gson 严格解析会整份配置抛异常、界面报「配置取得失败」。脚本强制把数值字段转 int、
   `ext` 强制为对象，类型冲突直接终止发布。
3. **可达性抽检**：国际直播源按并发 40 路 HEAD/GET 探测，丢弃超时与 4xx 地址。
4. **去重**：站点 key、直播 name/url、解析 name 全部按主键去重。

## 国际直播

除国内公开源外，本仓库额外从 [iptv-org](https://iptv-org.github.io/) 拉取公开 IP 频道索引，
按国家与分类聚合为 24 个分组（中国 / 香港 / 台湾 / 澳门 / 美国 / 英国 / 日本 / 韩国 / 东南亚 / 欧美 /
新闻 / 体育 / 电影 / 音乐 / 少儿 / 纪录片 等），写入 `output/live_intl.txt`。

> **边界说明**：iptv-org 只收录有公开来源的频道。
> Netflix / Disney+ / HBO / Amazon Prime 等带 DRM 加密的正版流媒体、以及付费体育版权直播，
> 任何 TVBox 类壳都无法接入，不在本仓库覆盖范围内。

## 本地运行

```bash
pip install requests
python scripts/update.py
```

## 目录结构

```
.
├── config/sources.json          # 源列表
├── scripts/update.py            # 聚合 / 规范化 / 抽检 / 状态回写
├── .github/workflows/daily.yml  # 每 6 小时跑一次
├── output/
│   ├── tvbox.json               # 主配置入口（FongMi 直接填这个）
│   ├── config.json              # 同名备份
│   ├── live_intl.txt            # 国际直播分组
│   └── <source_id>.json         # 单个源的干净副本
└── README.md
```

---

## 免责声明

本仓库仅为个人技术练习与配置管理用途，聚合的所有站点、接口、直播源均来自互联网公开地址，
版权归原作者与原站点所有。本仓库不托管、不存储、不提供任何视频内容，
不鼓励、不支持任何形式的侵权行为。请于下载后 24 小时内删除，并支持正版内容。
如涉及侵权，请联系删除。
