# My TVBox Config

> 个人自用 FongMi / TVBox 影视配置自动聚合仓库。
> 每天凌晨 3 点自动抓取公开源、测速排序、剔死链、发布。

![Update](https://img.shields.io/badge/update-daily%2003:00-blue?logo=githubactions)
![Sites](https://img.shields.io/badge/sites-462-green)
![Live](https://img.shields.io/badge/live-8%20sources%20%282700+%20international%20channels%29-orange)

---

## 配置地址（手机端填这个）

在 FongMi / TVBox 的「设置 → 配置地址」中，**点播**和**直播**两个框都填：

```
https://lsx9988.github.io/my-tvbox-cfg/output/tvbox_new.json
```

填完保存，以后不用动。

## 功能

- **智能排序**：每天自动测每个点播站响应速度，快的排前面，死的删掉
- **直播排序**：直播源同样按速度排，国际频道（2706 台）排第一
- **自动清洗**：剔网盘类、引流站、死链、类型冲突
- **每日寄语**：首页顶部显示更新时间 + 站点数 + 每日一句
- **暗色壁纸**：默认深蓝渐变，文字清晰可读

## 备用地址

| 场景 | 地址 |
| --- | --- |
| 主用（GitHub Pages，推荐） | `https://lsx9988.github.io/my-tvbox-cfg/output/tvbox_new.json` |
| jsDelivr 备用 | `https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/tvbox_new.json` |
| 只挂国际直播 | `https://lsx9988.github.io/my-tvbox-cfg/output/live_intl.txt` |

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `tvbox_new.json` | **主配置**（手机端填这个） |
| `sites.json` | 纯点播站列表 |
| `lives.json` | 纯直播源列表 |
| `live_intl.txt` | 国际频道（2706 个台） |
| `status.json` | 聚合状态 |

## 自动更新

- 每天北京时间 **03:00** 自动跑
- 跑完 1-2 分钟内手机端生效
- 自动剔死源、加新源、测速排序

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-11 15:15（北京时间） · 成功 **5/8** 个源

| 源 | 状态 | 地址 |
| --- | --- | --- |
| 王二小 | ✅ | kstore.dev |
| 老刘备 | ✅ | raw.liucn.cc |
| 小马 | ✅ | szyyds.cn |
| 讴歌 | ❌ | 403 |
| 4K小盒子 | ✅ | xhztv.top |
| 小盒子单仓 | ✅ | xhztv.top |
| 拾光多仓 | ❌ | 非合法配置 |
| 挺好分享多仓 | ❌ | 非合法配置 |
<!-- STATUS_END -->

---

仅供学习交流，请于 24 小时内删除。
