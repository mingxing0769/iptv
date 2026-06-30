# IPTV 频道合并与清理项目

本项目用于定期检测、合并并清理 IPTV 播放列表，仅保留 `channels.txt` 中指定的频道。项目每 12 小时通过 GitHub Actions 自动运行并更新结果。

## ✨ 核心功能

- **频道过滤**：仅保留 `channels.txt` 中定义的频道及其别名，过滤掉不在列表中的频道。
- **规范化匹配**：支持移除分辨率（如 `1080p`、`720p`、`HD`、`SD`）、`Geo-blocked`、`Not 24/7` 等后缀的模糊匹配。
- **正式名优先**：生成的播放列表中，频道名使用 `channels.txt` 中的正式名（第一列名称），而非别名或原始标题。
- **EPG 源冗余**：主 EPG 源失效时自动尝试备用源，确保节目单不中断。
- **流式 EPG 处理**：避免加载巨大临时文件到内存，防止 GitHub Actions 内存溢出。

## 📺 当前有效源

### M3U 源列表
- **`vbskycn/iptv`**：国内央视频道、卫视频道，支持 IPv4/IPv6，每 6 小时自动更新。
  - URL: `https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv4.m3u`
- **`iptv-org/iptv`**：全球国际频道，包含 ESPN、Sky Sports、TSN、beIN Sports 等体育频道。
  - URL: `https://iptv-org.github.io/iptv/index.m3u`

### EPG 源列表
- **主源**：`https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz`
- **备用源1**：`http://epg.51zmt.top:8000/e.xml`（老张的 EPG，被 TiviMate、Perfect Player 等广泛使用）
- **备用源2**：`https://raw.githubusercontent.com/fanmingming/live/main/e.xml`

## 🔗 订阅链接

### 播放列表
```
https://raw.githubusercontent.com/mingxing0769/iptv/refs/heads/main/out/MergedCleanPlaylist_no_tvg_id.m3u8
```

### 节目单 (EPG)
```
https://raw.githubusercontent.com/mingxing0769/iptv/main/out/DrewLive3.xml
```

## 📱 播放器配置建议

### TiviMate (Android TV)
1. 添加播放列表：选择 `M3U` 类型，输入上述播放列表链接。
2. 添加 EPG：选择 `XMLTV (URL)` 类型，输入上述 EPG 链接。
3. 在设置中启用 `EPG 自动更新`。

### Perfect Player (Android)
1. 播放列表类型选择 `M3U playlist`，输入播放列表链接。
2. EPG 类型选择 `XML TV Guide (URL)`，输入 EPG 链接。

### Kodi
1. 安装 `PVR IPTV Simple Client` 插件。
2. 配置播放列表和 EPG 链接，启用 `EPG 抓取`。

## ⚠️ 废弃说明

- **FSTV 脚本已废弃**：`fstv.py` 及相关 FSTV 镜像站（fstv.zip, fstv.online, fstv.space）已失效，不再维护。如需体育频道，请使用当前稳定的 M3U 源（如 `iptv-org/iptv`）。

## 🛠️ 本地运行

1. 克隆项目：
   ```bash
   git clone https://github.com/mingxing0769/iptv.git
   cd iptv
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 更新播放列表：
   ```bash
   python mergeclean.py
   ```

4. 更新节目单：
   ```bash
   python scripts/epg_getcher.py
   ```

## 📋 频道列表配置

项目使用 `channels.txt` 文件来定义需要保留的频道。格式为：
```
#正式名,别名1,别名2,...
CCTV2,CCTV-2
ESPN,ESPN HD
```

- 第一列为**正式名**，生成的播放列表中将使用正式名作为频道显示名称。
- 后续列为**别名**，用于匹配源中的频道标题。
- 以 `#` 开头的行会被跳过。

如果某些频道在当前源中缺失，`mergeclean.py` 会在处理后输出缺失频道列表，您可以据此补充到 `config/sources_urls.py` 中或扩展 `channels.txt` 中的别名。
