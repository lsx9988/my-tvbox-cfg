# My TVBox Config

> 个人自用 TVBox / FongMi 影视配置自动聚合仓库。
> 通过 GitHub Actions 定时抓取公开源、做类型规范化与质量校验后发布，供本人 FongMi / TVBox 类壳应用使用。

![Update](https://img.shields.io/badge/update-every%206h-blue?logo=githubactions)
![Sources](https://img.shields.io/badge/sources-8%20aggregated-green)
![Live](https://img.shields.io/badge/international%20live-2700%2B%20channels-orange)
![License](https://img.shields.io/badge/license-personal%20use-lightgrey)

---

## 我只需要做一件事

在 FongMi / TVBox 的「设置 → 配置地址」中，**点播**和**直播**两个框都填：

```
https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox.json
```

填完保存，以后不用动。每 6 小时自动更新一次，APP 下拉刷新即可。

### 备用地址

| 场景 | 地址 |
| --- | --- |
| 主用（推荐） | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox.json` |
| gcore 不通时备用 | `https://fastly.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox.json` |
| 只挂直播 | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/live_intl.txt` |

> 为什么用 gcore：jsDelivr 的 fastly 节点对同一文件名有最长 12 小时硬缓存，gcore 更新及时。
> 每次发布后 Actions 会自动调用 `purge.jsdelivr.net` 清缓存。

---

## 当前聚合状态

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-11 14:48:31（北京时间） · 成功 **5/8** 个源

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

## 目录结构

```
.
├── config/
│   └── sources.json          # 【改这里】8 个聚合源列表，加新源就编辑它
├── scripts/
│   └── update.py            # 聚合 / 清洗 / 校验 / 状态回写
├── .github/workflows/
│   └── daily.yml            # 定时任务（cron）
└── output/
    ├── tvbox.json           # ★ FongMi 直接填这个（合并版）
    ├── sites.json           # 纯点播站点列表（503 个），浏览用
    ├── lives.json           # 纯直播入口列表（8 条），浏览用
    ├── live_intl.txt        # 国际节目单（24 组 2700+ 频道）
    ├── status.json          # 各源成败状态
    ├── 多仓订阅.json         # 影视仓类 APP 用
    └── _sources/            # 单源干净副本（排错用）
```

---

## 日常维护指南

### 加一个新的点播源

编辑 `config/sources.json`，在 `sources` 数组里加一项：

```json
{
  "id": "简短英文名",
  "name": "显示名",
  "urls": ["主地址.json", "备用地址.json"]
}
```

提交后等下一次定时任务（或手动 Run workflow）即可。脚本会自动：
- 抓下来 → 修类型 → 去重 → 合并到 tvbox.json

### 改刷新频率

编辑 `.github/workflows/daily.yml` 里的 cron：
- `0 */6 * * *` = 每 6 小时（当前）
- `0 */12 * * *` = 每 12 小时
- `0 8,20 * * *` = 每天 8 点和 20 点（北京时间 = UTC+8）

### 手动立即更新

仓库 → Actions → 左侧 Daily Update → 右侧 Run workflow → 选 main → 绿色 Run workflow 按钮。

### 加国际频道

不用改。脚本自动从 [iptv-org](https://iptv-org.github.io/) 拉各国公开频道。
想加减国家，改 `scripts/update.py` 顶部的 `INTL_FEEDS` 列表。

---

## 自动质量保障

每次发布前脚本会做：

1. **多地址容灾**：每个源配主备 URL，中文域名自动 punycode
2. **类型规范化**：把 `playerType`/`type` 等字段强制转 int、`ext` 强制转对象（修掉 FongMi "配置取得失败"）
3. **直播清洗**：丢相对路径、本地代理、死链、重复，只保留活的
4. **国际频道抽检**：并发 40 路 HEAD 探测，剔掉 4xx/超时
5. **类型冲突质量门**：有任何类型混合直接 `exit 1`，不发布坏配置
6. **缓存清理**：发布后自动 purge jsDelivr

---

## 故障排查

| 症状 | 原因 / 处理 |
| --- | --- |
| 「配置取得失败」 | 通常是 CDN 还在旧缓存。等 10 分钟手动 Run workflow，或换备用地址 |
| 直播某分组全是死链 | 国际源是公开 m3u，每周会有 20-40% 频道失效，自动跑会剔除 |
| 点播某站打不开 | 源站本身挂了，等下一轮聚合自动换备用地址 |
| Actions 红色叉号 | 点开看日志，通常是某个源 403/超时，不影响整体发布 |

---

## 边界说明

- 国内主流 CCTV/卫视 由聚合源自带，iptv-org 不收录黄金台
- Netflix / Disney+ / HBO 等 DRM 内容、付费体育版权直播，任何 TVBox 壳都拿不到
- 本仓库只做配置聚合，不托管视频内容

---

## 本地运行

```bash
pip install requests
python scripts/update.py
```

---

## 免责声明

本仓库仅为个人技术练习与配置管理用途，聚合的所有站点、接口、直播源均来自互联网公开地址，
版权归原作者与原站点所有。本仓库不托管、不存储、不提供任何视频内容，
不鼓励、不支持任何形式的侵权行为。请于下载后 24 小时内删除，并支持正版内容。
如涉及侵权，请联系删除。
