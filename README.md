# 🎬 My TVBox Config

> 个人自用 FongMi / TVBox 影视配置自动聚合仓库
> 每天凌晨 3 点自动抓取公开源、测速排序、剔死链、发布

![Update](https://img.shields.io/badge/update-daily%2003:00-blue?logo=githubactions)
![Sites](https://img.shields.io/badge/sites-462-green)
![Live](https://img.shields.io/badge/live-8%20%E6%BA%90%20%282700+%E5%8F%B0%29-orange)

---

## 📱 配置地址

在 FongMi / TVBox 的「设置 → 配置地址」中，**点播**和**直播**两个框都填：

```
https://lsx9988.github.io/my-tvbox-cfg/output/tvbox_new.json
```

> 填完保存，以后不用动。每天自动更新，1-2 分钟生效。

---

## ✨ 功能特点

- ⚡ **智能排序**：每天自动测速，快的排前面，死的删掉
- 📺 **央视 + 卫视直播**：央视 19 台直连央视官网 CDN；卫视走运营商 IPTV 公网转播
- 🧹 **自动清洗**：剔网盘类、引流站、死链、类型冲突
- 💬 **每日寄语**：首页顶部显示更新时间 + 站点数 + 每日一句
- 🌙 **暗色壁纸**：默认深蓝渐变，文字清晰可读

---

## 🔗 备用地址

| 场景 | 地址 |
| --- | --- |
| 主用（GitHub Pages） | `https://lsx9988.github.io/my-tvbox-cfg/output/tvbox_new.json` |
| jsDelivr 备用 | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox_new.json` |
| 直播单独看 | `https://lsx9988.github.io/my-tvbox-cfg/output/cctv_live.txt` |

---

## 📁 文件说明

| 文件 | 说明 |
| --- | --- |
| `tvbox_new.json` | 主配置（手机端填这个） |
| `sites.json` | 纯点播站列表 |
| `lives.json` | 纯直播源列表 |
| `cctv_live.txt` | 央视 + 卫视直播（央视官网直连 + IPTV 转播） |
| `status.json` | 聚合状态 |

---

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-11 19:49:15（北京时间） · 成功 **5/8** 个源 · 共 **445** 站 **1** 直播

| 源 | 状态 |
| --- | --- |
| 王二小 | ✅ |
| 老刘备 | ✅ |
| 小马 | ✅ |
| 讴歌 | ❌ ('Connection aborted.', ConnectionResetE |
| 4K小盒子 | ✅ |
| 小盒子单仓 | ✅ |
| 拾光多仓 | ❌ 不是 TVBox 配置（缺 sites/spiders/lives） |
| 挺好分享多仓 | ❌ 不是 TVBox 配置（缺 sites/spiders/lives） |

### 点播源 TOP 15（按速度排序）

| 排名 | 名称 | 延迟 |
| :---: | --- | :---: |
| 1 | 建安 | 141ms |
| 2 | 天堂┃采集 | 364ms |
| 3 | 🦊火狐采集 | 366ms |
| 4 | 🎥┃豪华┃资源 | 370ms |
| 5 | 电影天堂 | 402ms |
| 6 | 非凡[直连] | 410ms |
| 7 | 🧡┃初恋┃官源 | 439ms |
| 8 | 量子资源(切) | 441ms |
| 9 | 闪电资源(切) | 659ms |
| 10 | 🎥┃量子┃资源 | 665ms |
| 11 | 新浪资源(切) | 694ms |
| 12 | 量子[直连] | 717ms |
| 13 | 天涯 | 791ms |
| 14 | 率率[直连] | 1084ms |
| 15 | 🎥┃索尼┃资源 | 1147ms |

### 央视直播（官网直连）

| 项目 | 数量 | 最快频道 | 延迟 |
| :---: | :---: | --- | :---: |
| 央视频道 | 19 | CCTV-1 综合 | 399ms |
| 卫视频道 | 40 | — | — |

> 央视 **19** 个台直连央视官网（tv.cctv.com）CDN，不依赖任何第三方；卫视 **40** 个用的是运营商 IPTV 公网转播地址（各卫视官网实测不提供公开 m3u8）。完整列表见 `cctv_live.txt`
<!-- STATUS_END -->

---

*仅供学习交流，请于 24 小时内删除*
