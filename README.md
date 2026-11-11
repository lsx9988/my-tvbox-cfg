# 🎬 My TVBox Config

> 个人自用 FongMi / TVBox 影视配置自动聚合仓库
> 每天凌晨 3 点自动抓取公开源、测速排序、剔死链、发布

![Update](https://img.shields.io/badge/update-daily%2003:00-blue?logo=githubactions)
![Sites](https://img.shields.io/badge/sites-401%20%E7%AB%99-green)
![Live](https://img.shields.io/badge/live-59%20%E5%8F%B0-orange)

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
- 💬 **每日寄语**：首页顶部显示每日一句励志语（随机，每天不同）
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
> 🔄 最近更新：2026-11-11 23:07:09（北京时间） · 成功 **5/8** 个源 · 共 **401** 站 **59** 台直播
> 📱 手机嫌卡就用精简版：`output/tvbox_lite.json`（前 80 个最快站点）

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
| 1 | 率率[直连] | 77ms |
| 2 | 极速[直连] | 87ms |
| 3 | 光速资源(切) | 152ms |
| 4 | 非凡[直连] | 163ms |
| 5 | 🐯虎牙采集 | 202ms |
| 6 | 天涯 | 225ms |
| 7 | 红牛资源(切) | 226ms |
| 8 | 🐓┃爱坤┃资源 | 244ms |
| 9 | 闪电资源(切) | 288ms |
| 10 | 🦊火狐采集 | 291ms |
| 11 | 新浪资源(切) | 299ms |
| 12 | 天堂┃采集 | 300ms |
| 13 | 电影天堂 | 337ms |
| 14 | 🌪暴风影音 | 353ms |
| 15 | 建安 | 389ms |

### 央视直播（官网直连）

| 项目 | 数量 | 最快频道 | 延迟 |
| :---: | :---: | --- | :---: |
| 央视频道 | 19 | 沿用上周清单 | — |
| 卫视频道 | 40 | — | — |

> 央视 **19** 个台直连央视官网（tv.cctv.com）CDN，不依赖任何第三方；卫视 **40** 个用的是运营商 IPTV 公网转播地址（各卫视官网实测不提供公开 m3u8）。完整列表见 `cctv_live.txt`
<!-- STATUS_END -->

---

*仅供学习交流，请于 24 小时内删除*
