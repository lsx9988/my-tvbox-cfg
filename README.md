# my-tvbox-cfg

TVBox / FongMi 自动聚合配置，每日 06:00（北京时间）由 GitHub Actions 自动更新。

## 使用地址

**单仓（直接填 FongMi）：**
```
https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/config.json
```

**多仓订阅（影视仓用）：**
```
https://gcore.jsdelivr.net/gh/lsx9988/my-tvbox-cfg@main/output/多仓订阅.json
```

**单源直链：**
| 源 | 地址 |
| --- | --- |
<!-- STATUS_START -->
> 🔄 最近更新：2026-11-11 10:05:09（北京时间） · 成功 **5/8** 个源

| 源 | 状态 | 地址 |
| --- | --- | --- |
| 王二小 | ✅ | `https://9280.kstore.vip/newwex.json` |
| 老刘备 | ✅ | `https://raw.liucn.cc/box/m.json` |
| 小马 | ✅ | `https://szyyds.cn/tv/x.json` |
| 讴歌 | ❌ | 409 Client Error: Conflict for url: http://xn--dkw0c.v.nxog. |
| 4K小盒子 | ✅ | `http://xhztv.top/4k.json` |
| 小盒子单仓 | ✅ | `http://xhztv.top/xhz` |
| 拾光多仓 | ❌ | 不是 TVBox 配置（缺 sites/spiders/lives） |
| 挺好分享多仓 | ❌ | 不是 TVBox 配置（缺 sites/spiders/lives） |
<!-- STATUS_END -->

## 特性

- 自动聚合 8 个公开源（王二小/老刘备/小马/讴歌/4K小盒子/小盒子/拾光/挺好分享）
- 自动重试 + 备用地址 + 中文域名 punycode
- 自动修复 `ext` 字符串字段（FongMi v5.x 兼容）
- 失败源自动沿用上次缓存，不会整个挂掉
- 状态写回 README，一眼看到哪些源活着

## 本地运行

```bash
pip install requests
python scripts/update.py
```

仅供学习交流，请勿商用。
