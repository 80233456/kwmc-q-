# 音乐盒 Studio · kwmc-q

> 一个基于**酷我音源**的现代桌面音乐播放器：在线搜索 · 直接试听 · 无损下载 · 本地曲库 · 动画歌词
> 界面 PySide6 / Qt 6，纯 Python 实现，可打包成免安装 exe。

![界面总览](docs/screenshots/overview.png)

---

## 📦 直接下载（免安装）

到 [**Releases**](https://github.com/80233456/kwmc-q-/releases/latest) 下载：

| 文件 | 说明 |
| --- | --- |
| `MusicBox-Studio-v1.0.0-portable.exe`（55 MB） | ★ **单文件版**：拷到任何 Win10/11 电脑双击即用，**不需要装 Python**（首次启动约 3 秒） |
| `MusicBox-Studio-v1.0.0-folder.zip`（56 MB） | **单目录版**：解压后运行里面的 `音乐盒Studio.exe`，启动更快；⚠️ 切勿只把 exe 单独拖出来 |

> Windows 10/11 64 位可直接运行；Win7 不支持（Python 3.11 限制）。

---

## ✨ 功能

| 模块 | 说明 |
| --- | --- |
| **搜索** | 歌曲 / 歌手 / 专辑 / 混合关键词；结果带**专辑封面**、`VIP` 徽标、**可用音质与体积**（如 `VIP · FLAC 26.6M`） |
| **试听** | 双击即播**线上流媒体**，无需先下载（QtMultimedia + FFmpeg 后端） |
| **下载** | 无损 FLAC / 320k / 128k MP3，**真实进度条**，按内嵌标签自动规范命名，可选保存 `.lrc` |
| **歌词** | 独立歌词页：**平滑滚动 + 卡拉OK 渐变填充 + 切行弹入动画 + 点击跳转**；四级降级 + 磁盘缓存 |
| **本地曲库** | 自动扫描下载目录，FLAC/MP3 区分图标，双击播放、右键定位/删除 |
| **播放条** | 上一首/播放暂停/停止/下一首/播放模式、进度拖动、音量与静音、律动指示 |
| **设置** | 下载目录、启动音量、缓存统计与清理、关于 |

全部图标为 **QPainter 矢量自绘**（不依赖 emoji/字体，任意尺寸颜色都锐利一致）。

---

## 🚀 快速开始

### 源码运行
```bash
pip install PySide6            # 仅此一个依赖
python kuwo_app.py             # 或双击 启动音乐盒.bat
```

### 打包成免安装 exe
```bash
双击 打包-单文件.bat           # → dist\音乐盒Studio-单文件版.exe（一个文件，可直接发给别人）
双击 打包-单目录.bat           # → dist\音乐盒Studio\（文件夹版，启动更快，需整个文件夹一起发）
```
> ⚠️ 单目录版**不能只发 exe**（缺 `_internal` 会报 `Failed to load Python DLL`），详见
> [docs/怎么发给别人用.md](docs/怎么发给别人用.md)

### 自检 / 复现截图
```bash
python tools/healthcheck.py    # ★ 链路自检：搜索/播放地址/下载/歌词/封面 7 项，坏了哪一环一目了然
python tools/app_test.py       # 端到端：搜索 / 试听 / 下载 / 歌词 / 队列
python tools/app_shots.py      # 渲染各页截图（窗口移到屏幕外）
python tools/ui_audit.py       # 图标/文字/歌词的数值化体检
```
> 双击 `自检.bat` 也能跑（Windows）。

**这个程序能用多久？** —— 它不是离线工具，而是在线服务的非官方客户端，
接口随时可能变（本项目已遇到两次小型失效）。为此配备了自检工具与维护手册：
所有对外依赖、失效症状、修复位置都列在 [docs/接口速查与维护.md](docs/接口速查与维护.md)。
即使音源全部失效，**本地曲库 / 播放器 / 歌词动画仍然完全可用**。

---

## 🧩 技术架构

```
kuwo_app.py            PySide6 主程序（页面 + 播放条 + 线程模型 Engine）
ui_kit.py              界面组件库：矢量图标 / 图标按钮 / 动画歌词 / 律动条 / 空状态 / Toast / Spinner
kuwo_pc_download.py    引擎：搜索解析 / 播放地址解析 / 分块下载 / 歌词多级降级 / FLAC 标签
kuwo_q.py              酷我 q 参数加解密（自定义 DES 变体，密钥 ylzsxkwm）
tools/                 开发与验证脚本（测试、截图、体检、图标生成）
docs/                  使用说明与技术报告
```

几个关键点：

* **q 参数加密**：酷我私有接口用自定义 DES 变体（自定义 S 盒 `MATRIXNSBOX` 与置换表），
  **标准 DES 库无法解开**（曾暴力枚举 20 万+ 候选全部失败）。本项目移植了开源实现后，
  可实现「PC 端纯离线生成 q」→ 搜索、解析播放地址、取歌词全部只需 Python 标准库。
* **搜索解析容错**：接口返回的 JSON 里存在**未转义双引号**（如 `"ALBUM":"What"s Going On...?`），
  会导致 `json.loads` 直接失败 → 表现为"某些歌搜不到"。现改为**严格 JSON 失败则按条目扫描取值**。
* **歌词四级降级**：酷我 `http` H5 → 酷我 `https` H5 → App 加密通道 → 网易云兜底，
  并落盘缓存（`%LOCALAPPDATA%\MusicBoxStudio\lyrics`）。
* **界面动画**：统一 60fps 定时器 + 缓动插值（歌词滚动、切行弹入、导航指示条、Toast 淡入）。
* **线程模型**：网络操作全部在 `QThread` 中，通过信号回主线程，界面不卡顿。

更详细的分析见：
- [docs/接口速查与维护.md](docs/接口速查与维护.md)　← 对外依赖速查表 / 失效症状→修复位置 / 寿命评估
- [docs/技术报告-算法与纯离线管线.md](docs/技术报告-算法与纯离线管线.md)
- [docs/技术报告-加密算法与接口.md](docs/技术报告-加密算法与接口.md)
- [docs/修复记录-搜索解析.md](docs/修复记录-搜索解析.md)
- [docs/UI检查与优化报告.md](docs/UI检查与优化报告.md)

---

## 🎧 kwlx music（lx-music 定制版）

把本项目的酷我接口作为**自定义音源**接进 [lx-music-desktop](https://github.com/lyswhut/lx-music-desktop)，
预装、默认启用，**酷我 + 网易云双引擎，均可出无损**。详见 **[lx-music/README.md](lx-music/README.md)**。

| 文件 | 说明 |
| --- | --- |
| [`lx-music/kwlx-kuwo-source.js`](lx-music/kwlx-kuwo-source.js) | 纯 JS 自定义源：酷我 q 加密直连 + 网易云 GDAPI + 跨源兜底 + 歌词，可直接导入官方 lx-music |
| [`lx-music/tools/`](lx-music/tools) | 生成器、对拍/源级测试、`wy_harness.js`、lx-music 补丁脚本、`node:sqlite` 垫片、验证脚本 |
| [`lx-music/KWLX-上游仓库规范.md`](lx-music/KWLX-上游仓库规范.md) | 改上游前必读：i18n 四语言 / less 模块 / 图标 viewBox / store 数据流 / 设置强制项 |
| [`lx-music/KWLX-故障修复记录.md`](lx-music/KWLX-故障修复记录.md) | 五个真实根因（音源 id 判定、跨源注册、sqlite 垫片语义、按钮默认隐藏、旧存档覆盖） |

### 双引擎

| 源 | 实现 | 实测 |
| --- | --- | --- |
| **酷我 kw** | 自研 **q 参数加密**（自定义 DES 变体，纯 JS/BigInt，无 Buffer/require）→ `mobi.kuwo.cn/mobi.s` → `convert_url2` | flac **26.6 MB**、`fLaC` ✅ |
| **网易云 wy** | **GDAPI**（`music-api.gdstudio.xyz`，`br=740/999`）→ 网易 CDN 直链；失败回退酷我跨源 | flac **50.7 MB**、`fLaC` ✅ |
| kg / tx / mg | 「歌名+歌手」跨源到酷我搜索取 rid 再解析 | kg 歌 → 酷我 flac ✅ |
| 歌词 | 酷我 H5（http，https 被限流）→ 网易云兜底 | 65–72 行 ✅ |

### 为什么"直连"值得

实测市面 6 个热门音源（★6532 仓库里的候选）**全部是转发第三方聚合 API**（`oiapi`/`gdstudio`/`xcvts`…），
没有一个是直连酷我 —— 对照表见 [`tools/compare_kw_direct.py`](lx-music/tools/compare_kw_direct.py)。
第三方中间层会限流、收费、关站（`music.nxinxz.com`、`175.27.166.236` 已 404；`oiapi` 的 `level=flac` **只返回 MP3**）。
所以核心播放链路我们**不依赖任何第三方**。

### 开箱即用（改装项）

* 预装音源 + id 用 `user_api_*` + `getUserApis()` **幂等补回**（清档/升级不丢）
* 默认选中音源、**下载默认开启**、每行**下载按钮常显**、**默认音质 flac**
* **本地音乐库**：自动跟随「下载目录」建列表「下载的歌」+ 「我的列表」页头**手动扫描**按钮
* 许可协议默认已同意（协议正文仍在「关于」页），避免首启弹窗挡住界面
* `better-sqlite3` → **`node:sqlite` 垫片**（无需 Visual Studio 即可构建）

### 测试现状

```
cipher 对拍（vs Python）  7/7      test_cipher.js
酷我源级 + 跨源          15/15     test_source.js
网易云源级（含真 FLAC）   16/16     wy_harness.js
node:sqlite 垫片兼容       6/6      测试台内联用例
```

> kwlx music 是 lx-music-desktop（© lyswhut，**Apache-2.0**）的修改版，遵守 Apache-2.0 分发，
> 改动清单见 [lx-music/README.md](lx-music/README.md) 第五节。

---

## 🙏 致谢与引用的开源项目

本项目的**加密算法实现**与部分接口思路来自以下开源项目，特此致谢（按贡献程度排序）：

| 项目 | 本项目用到了什么 |
| --- | --- |
| **[JayZorn-LJZ/GetFreeMusicYourself](https://github.com/JayZorn-LJZ/GetFreeMusicYourself)** | ⭐ **核心**：`kuwo_query_encryption.py` 提供了 q 参数加密算法的完整实现（自定义 DES 变体、S 盒与置换表）。本项目的 `kuwo_q.py` 是在其基础上移植/整理而来 |
| **[CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl)** | 多平台音乐下载器的接口组织方式，搜索/下载字段与参数命名参考 |
| **[zhiyYo/Groove](https://github.com/zhiyYo/Groove)** | 专辑封面地址拼接方式（`web_albumpic_short` → `img1.kuwo.cn/star/albumcover/...`） |
| **[listen1/listen1_chrome_extension](https://github.com/listen1/listen1_chrome_extension)** | 多音源聚合与接口适配的总体思路 |
| **[UnblockNeteaseMusic/server](https://github.com/UnblockNeteaseMusic/server)** | 音源降级/替换（fallback）思路，歌词兜底方案参考 |
| **[sdbabd/QQKWKG-TriMusicDecrypt](https://github.com/sdbabd/QQKWKG-TriMusicDecrypt)** | 音乐平台加解密与接口逆向的参考资料 |
| **[guoyue2010/lxmusic-](https://github.com/guoyue2010/lxmusic-)** | ⭐ **网易云**链路：GDAPI（`music-api.gdstudio.xyz`，与「星海音乐源」同源）实测可出真 FLAC；候选音源对比也在该仓库取样（Apache-2.0） |
| **[lyswhut/lx-music-desktop](https://github.com/lyswhut/lx-music-desktop)** | ⭐ **kwlx music** 的宿主应用（Apache-2.0）：我们以其「自定义源」机制接入酷我音源，并发布带改动的定制版（改动清单见 [lx-music/README.md](lx-music/README.md)） |

使用的开源软件与库：

| 组件 | 用途 | 许可 |
| --- | --- | --- |
| [PySide6 / Qt 6](https://www.qt.io/qt-for-python) | 界面与多媒体播放 | LGPL v3 |
| [FFmpeg](https://ffmpeg.org/)（经 Qt Multimedia 调用） | 音频解码（MP3 / FLAC / 流式 HTTP） | LGPL v2.1+ |
| [PyInstaller](https://pyinstaller.org/) | 打包为独立 exe | GPL v2 + 例外条款 |
| [Pillow](https://python-pillow.org/) | 图标生成、界面截图拼版 | MIT-CMU |

界面设计上参考了 Spotify / Apple Music 的深色布局，以及 [VutronMusic](https://github.com/stark81/VutronMusic)、
[MusicFree](https://github.com/maotoumao/MusicFree)、[FeelUOwn](https://github.com/feeluown/FeelUOwn)
等开源播放器的功能组织方式（仅作设计参考，未使用其代码）。

---

## ⚠️ 免责声明

* 本项目**仅供个人学习、研究与技术交流**，用于学习网络协议分析、加解密算法与桌面 GUI 开发；
* 所有音乐内容与接口版权归**原版权方（酷我音乐及其版权方）**所有，本项目不存储、不分发任何音乐内容；
* 请勿将本项目用于商业用途或大规模分发下载内容；使用产生的任何后果由使用者自行承担；
* 若相关权利方认为本项目不妥，请联系删除。

---

## 📄 许可

本项目代码以 **MIT License** 发布（见 [LICENSE](LICENSE)）。
注意：`kuwo_q.py` 的算法实现移植自上述开源项目（[GetFreeMusicYourself](https://github.com/JayZorn-LJZ/GetFreeMusicYourself)），
该部分请一并遵守原项目的许可与声明。
