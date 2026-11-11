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

## 📊 当前源排序

### 点播源 TOP 15

| 排名 | 名称 | 速度 |
| :---: | --- | :---: |
| 🥇 | 建安 | 143ms |
| 🥈 | 量子资源 | 201ms |
| 🥉 | 非凡直连 | 222ms |
| 4 | 天堂采集 | 357ms |
| 5 | 电影天堂 | 384ms |
| 6 | 初恋官源 | 420ms |
| 7 | 量子切 | 455ms |
| 8 | 天涯 | 512ms |
| 9 | 率率直连 | 580ms |
| 10 | 索尼资源 | 620ms |

> 共 462 站，完整列表见 `sites.json`

### 直播源

| 排名 | 名称 | 速度 |
| :---: | --- | :---: |
| 🥇 | 国际频道（2706 台） | 112ms |
| 🥈 | 有效期27年7月 | 156ms |
| 🥉 | 音乐所 | 171ms |
| 4 | 咪咕 | 172ms |
| 5 | 手动更新 | 215ms |
| 6 | 综合直播 | 489ms |
| 7 | live | 649ms |
| 8 | Kimentanm | 3011ms |

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
| 1 | 🎥┃光速┃资源 | 151ms |
| 2 | 影视 | 率率[直连] | 177ms |
| 3 | 🎥┃红牛┃资源 | 181ms |
| 4 | ️天堂┃采集 | 184ms |
| 5 | 🐉┃索尼┃高清 | 190ms |
| 6 | 影视 | 极速[直连] | 192ms |
| 7 | 红牛资源(切) | 207ms |
| 8 | 🐓┃爱坤┃资源 | 210ms |
| 9 | 🐯虎牙采集 | 212ms |
| 10 | 光速资源(切) | 260ms |
| 11 | 闪电资源(切) | 280ms |
| 12 | 新浪资源(切) | 282ms |
| 13 | 影视 | 建安 | 289ms |
| 14 | 影视 | 天涯 | 306ms |
| 15 | 🎥┃索尼┃资源 | 362ms |

### 直播源（按速度排序）

| 排名 | 名称 |
| :---: | --- |
| 1 | 国际频道 |
| 2 | Kimentanm |
| 3 | 综合直播 |
| 4 | 咪咕 |
| 5 | 手动不知何时更新 |
| 6 | 有效期27年7月 |
| 7 | 音乐所 |
| 8 | live |
<!-- STATUS_END -->

---

*仅供学习交流，请于 24 小时内删除*
