# 国外IPTV源检测

本项目用于定期检测并清理国外 IPTV 源，自动运行于 GitHub Actions，每 4 小时执行一次。

## 使用方式

1. 克隆项目
2. 安装依赖：`pip install -r requirements.txt`
3. 运行脚本：`python mergeclean.py`

## 逻辑缺陷：

1.节目名去重过于简单
2.同源直接去除
3.节目可用性测试过于简单

## 自动化

通过 GitHub Actions 自动运行并更新结果。
订阅链接：
https://raw.githubusercontent.com/mingxing0769/iptv/main/out/MergedCleanPlaylist.m3u8

## 所有源来自:

https://github.com/Drewski2423/drewlive
本项目基于 Drewski2423/drewlive 项目进行二次开发，仅用于学习和非商业用途。

## 开源准则

本项目只是修改于原项目，符合个人使用原则 ，对复制 修改等没有任何限制。
除非原项目有要求！请参阅原项目！
