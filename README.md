# 国外IPTV源检测

本项目用于定期检测并清理国外 IPTV 源，每小时更新一次。

节目单 仅包含订阅播放列表(MergedCleanPlaylist.m3u8)中对应频道的节目。


## 使用方式

1. 克隆项目
2. 安装依赖：`pip install -r requirements.txt`
3. 更新播放列表 运行脚本：`python mergeclean.py`

   可对 mergeclean.py 脚本中的分类过滤进行开启与关闭CategoryFilter = True
   
   或修改过滤内容：utils/filter_keywords.py
   
4. 更新节目单 运行脚本：`python scripts/epg_getcher.py`




## 自动化

通过 GitHub Actions 自动运行并更新结果。

订阅链接：
https://raw.githubusercontent.com/mingxing0769/iptv/main/out/MergedCleanPlaylist.m3u8


节目单链接：
https://raw.githubusercontent.com/mingxing0769/iptv/main/out/DrewLive3.xml.gz


## 所有源来自:

https://github.com/Drewski2423/drewlive

本项目基于 Drewski2423/drewlive 项目进行二次开发，仅用于学习和非商业用途。


