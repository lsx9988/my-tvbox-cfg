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
- 📺 **直播排序**：国际频道（2706 台）排第一，其他按速度排
- 🧹 **自动清洗**：剔网盘类、引流站、死链、类型冲突
- 💬 **每日寄语**：首页顶部显示更新时间 + 站点数 + 每日一句
- 🌙 **暗色壁纸**：默认深蓝渐变，文字清晰可读

---

## 🔗 备用地址

| 场景 | 地址 |
| --- | --- |
| 主用（GitHub Pages） | `https://lsx9988.github.io/my-tvbox-cfg/output/tvbox_new.json` |
| jsDelivr 备用 | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox_new.json` |
| 只挂国际直播 | `https://lsx9988.github.io/my-tvbox-cfg/output/live_intl.txt` |

---

## 📁 文件说明

| 文件 | 说明 |
| --- | --- |
| `tvbox_new.json` | 主配置（手机端填这个） |
| `sites.json` | 纯点播站列表 |
| `lives.json` | 纯直播源列表 |
| `live_intl.txt` | 国际频道（2706 个台） |
| `status.json` | 聚合状态 |

---

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-11 17:13:45（北京时间） · 成功 **5/8** 个源 · 共 **430** 站 **8** 直播

### 点播源 TOP 15（按速度排序）

| 排名 | 名称 | 延迟 |
| :---: | --- | :---: |
| 1 | 建安 | 148ms |
| 2 | 量子资源(切) | 188ms |
| 3 | 量子资源 | 209ms |
| 4 | 豪华资源 | 342ms |
| 5 | 天堂采集 | 369ms |
| 6 | 电影天堂 | 381ms |
| 7 | 非凡直连 | 387ms |
| 8 | 火狐采集 | 399ms |
| 9 | 初恋官源 | 399ms |
| 10 | 率率直连 | 575ms |

### 直播源（按速度排序）

| 排名 | 名称 |
| :---: | --- |
| 1 | 国际频道 |
| 2 | Kimentanm |
| 3 | 综合直播 |
| 4 | 咪咕 |
| 5 | 手动更新 |
| 6 | 有效期27年7月 |
| 7 | 音乐所 |
| 8 | live |
<!-- STATUS_END -->

---

*仅供学习交流，请于 24 小时内删除*
