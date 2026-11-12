# 🎬 My TVBox Config

> 个人自用 FongMi / TVBox 影视配置自动聚合仓库
> 每天凌晨 3 点自动抓取公开源、测速排序、剔死链、发布

![Update](https://img.shields.io/badge/update-daily%2003:00-blue?logo=githubactions)
![Sites](https://img.shields.io/badge/sites-652%20%E7%AB%99-green)
![Live](https://img.shields.io/badge/live-65%20%E5%8F%B0-orange)


> ⚠️ **唯一官方地址：`github.com/lsx9988/my-tvbox-cfg`** ｜ 其它同名仓库、二次打包版、收费版均与本人无关，禁止转售。

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
- 📺 **央视 + 卫视直播**：央视 16 台直连央视官网 CDN；卫视走运营商 IPTV 公网转播
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
> 🔄 最近更新：2026-11-12 23:53:10（北京时间） · 成功 **7/7** 个源 · 共 **652** 站 **65** 台直播
> 📱 手机嫌卡就用精简版：`output/tvbox_lite.json`（前 80 个最快站点）

| 源 | 状态 |
| --- | --- |
| 王二小 | ✅ |
| 老刘备 | ✅ |
| 小马 | ✅ |
| 4K小盒子 | ✅ |
| 小盒子单仓 | ✅ |
| 拾光 | ✅ |
| 挺好分享 | ✅ |

### 点播源 TOP 15（按速度排序）

| 排名 | 名称 | 延迟 |
| :---: | --- | :---: |
| 1 | 豪华｜采集 | 56ms |
| 2 | 极速｜采集 | 60ms |
| 3 | 率率[直连] | 91ms |
| 4 | 光速｜采集 | 93ms |
| 5 | 天翼｜采集 | 136ms |
| 6 | 黑木耳｜采集 | 158ms |
| 7 | 新浪资源(切) | 185ms |
| 8 | 最大｜采集 | 219ms |
| 9 | 天堂┃采集 | 221ms |
| 10 | 电影天堂 | 231ms |
| 11 | 🎥┃红牛┃资源 | 254ms |
| 12 | 天涯 | 255ms |
| 13 | 天涯｜采集 | 258ms |
| 14 | 无尽｜采集 | 265ms |
| 15 | 闪电资源(切) | 271ms |

### 央视直播（官网直连）

| 项目 | 数量 | 最快频道 | 延迟 |
| :---: | :---: | --- | :---: |
| 央视频道 | 16 | CCTV-1 综合 | 3452ms |
| 卫视频道 | 39 | — | — |
| 电影频道 | 10 | — | — |

> 央视 **16** 个台直连央视官网（tv.cctv.com）CDN，不依赖任何第三方；卫视 **39** 个用的是运营商 IPTV 公网转播地址（各卫视官网实测不提供公开 m3u8）；电影频道 **10** 个优先官方，官网无公开流的退回运营商持牌转播。完整列表见 `cctv_live.txt`
<!-- STATUS_END -->

---

*仅供学习交流，请于 24 小时内删除*
