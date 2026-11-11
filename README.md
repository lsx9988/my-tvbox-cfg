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
- 📺 **央视直播**：19 个央视频道直连央视官网 CDN，不依赖第三方
- 🧹 **自动清洗**：剔网盘类、引流站、死链、类型冲突
- 💬 **每日寄语**：首页顶部显示更新时间 + 站点数 + 每日一句
- 🌙 **暗色壁纸**：默认深蓝渐变，文字清晰可读

---

## 🔗 备用地址

| 场景 | 地址 |
| --- | --- |
| 主用（GitHub Pages） | `https://lsx9988.github.io/my-tvbox-cfg/output/tvbox_new.json` |
| jsDelivr 备用 | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox_new.json` |
| 央视直播单独看 | `https://lsx9988.github.io/my-tvbox-cfg/output/cctv_live.txt` |

---

## 📁 文件说明

| 文件 | 说明 |
| --- | --- |
| `tvbox_new.json` | 主配置（手机端填这个） |
| `sites.json` | 纯点播站列表 |
| `lives.json` | 纯直播源列表 |
| `cctv_live.txt` | 央视频道直播（央视官网直连） |
| `status.json` | 聚合状态 |

---

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-11 17:48:52（北京时间） · 成功 **5/8** 个源 · 共 **462** 站 **1** 直播

| 源 | 状态 |
| --- | --- |
| 王二小 | ✅ |
| 老刘备 | ✅ |
| 小马 | ✅ |
| 讴歌 | ❌ 403 Client Error: Forbidden for url: htt |
| 4K小盒子 | ✅ |
| 小盒子单仓 | ✅ |
| 拾光多仓 | ❌ 不是 TVBox 配置（缺 sites/spiders/lives） |
| 挺好分享多仓 | ❌ 不是 TVBox 配置（缺 sites/spiders/lives） |

### 点播源 TOP 15（按速度排序）

| 排名 | 名称 | 延迟 |
| :---: | --- | :---: |
| 1 | 量子资源(切) | 96ms |
| 2 | 建安 | 154ms |
| 3 | 非凡[直连] | 195ms |
| 4 | 🎥┃豪华┃资源 | 301ms |
| 5 | 天堂┃采集 | 366ms |
| 6 | 🧡┃初恋┃官源 | 440ms |
| 7 | 闪电资源(切) | 473ms |
| 8 | 新浪资源(切) | 492ms |
| 9 | 🦊火狐采集 | 519ms |
| 10 | 率率[直连] | 588ms |
| 11 | 🎥┃索尼┃资源 | 593ms |
| 12 | 🎥┃量子┃资源 | 655ms |
| 13 | 天涯 | 662ms |
| 14 | 量子[直连] | 668ms |
| 15 | 🐉┃索尼┃高清 | 756ms |

### 央视直播（官网直连）

| 项目 | 数量 | 最快频道 | 延迟 |
| :---: | :---: | --- | :---: |
| 央视频道 | 19 | CCTV-1 综合 | 269ms |

> 共 **19** 个台，直接取央视官网（tv.cctv.com）的播放地址，不依赖任何第三方搬运站；完整列表见 `cctv_live.txt`
<!-- STATUS_END -->

---

*仅供学习交流，请于 24 小时内删除*
