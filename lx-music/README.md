# kwlx music —— 基于 lx-music 的酷我音源定制版

> 把本项目的**酷我接口（q 参数加密）**作为**自定义音源**接进 [lx-music-desktop](https://github.com/lyswhut/lx-music-desktop)，
> 并预装、默认启用，支持 **无损 FLAC 下载**。

---

## 一、直接使用（推荐）

| 文件 | 说明 |
| --- | --- |
| `kwlx-music/` 文件夹（或 `kwlx-music-portable.zip`） | ★ **便携版**：解压后双击 `kwlx-music.exe`。数据保存在程序目录 `portable\userData`，**完全绿色、不写系统目录** |
| `kwlx-music-v2.12.6-x64-Setup.exe` | 安装版（NSIS），装完从开始菜单启动 |

启动后：

1. 窗口标题为 **kwlx Music** ✓
2. **音源已预装并默认选中**（设置 → 自定义源 → `酷我音源 · kwlx`）
3. 搜索歌曲 → 右键/点击下载 → **音质选「无损 FLAC」→ 得到真无损**

> 搜索走 lx-music 内置的酷我搜索接口；我们的音源负责**解析播放/下载地址**与**歌词**。
> 若哪天内置搜索失效，可先在其它源搜到同名歌曲，再切回本音源播放/下载。

---

## 二、这是什么（技术说明）

```
lx-music-desktop (Apache-2.0)          kwlx 补丁
├─ 界面/播放/下载/歌单/歌词（上游）  + 默认预装「酷我音源 · kwlx」
├─ 自定义源沙箱（上游）             + 放开 kw 源的 lyric 动作
└─ 数据库层 better-sqlite3（原生）  → 换成 node:sqlite 垫片（免编译）
```

### 音源做了什么

| 能力 | 实现 |
| --- | --- |
| `musicUrl`（播放/下载地址） | 自研 **q 参数加密**（自定义 DES 变体，密钥 `ylzsxkwm`）→ `mobi.kuwo.cn/mobi.s?f=kuwo&q=…` → `convert_url2` → 真实 FLAC/MP3 直链 |
| 音质档位 | `128k` / `320k` / `flac` / `flac24bit`（**flac24bit 自动回退到 flac**）；主档失败自动降级 |
| `lyric` 歌词 | 酷我 H5 `http://` 接口（https 会被限流）→ 失败自动走**网易云兜底** |
| 纯 JS 实现 | **无 Buffer、无 require**，算法与 Python 版 `kuwo_q.py` **逐字节对拍一致**（7 组向量） |

### 实测数据

```
flac       → 26.6 MB，文件头 "fLaC"        ✅ 无损
320k       → MP3 帧正确                    ✅
flac24bit  → 回退成功                      ✅
歌词        → 72 行                         ✅
异常入参    → 正确报错                      ✅   （13/13 通过）
```

---

## 三、只想要音源脚本（不改装 lx-music）

把 `kwlx-kuwo-source.js` 导入**官方 lx-music** 即可：

1. 设置 → 自定义源 → 导入（选文件或粘贴脚本）
2. 选中 `酷我音源 · kwlx`
3. ⚠️ 官方版把 `kw` 源的 actions 限定为 `['musicUrl']`，**歌词不会生效**（播放/下载不受影响）；
   歌词需要 kwlx 定制版（已放开 `['musicUrl','lyric']`）

---

## 四、自己重新构建

```powershell
# 0) 环境：Node ≥ 22、pnpm、git；Windows 无需 Visual Studio（已用 node:sqlite 垫片）
git clone --depth 1 https://github.com/lyswhut/lx-music-desktop.git lx-src
cd lx-src; pnpm install

# 1) 首次：下载 Electron 二进制（国内建议走镜像）
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
node node_modules\electron\install.js

# 2) 打入 kwlx 补丁（幂等）
python patch_lx.py          # 预装音源 + 默认选中 + 放开歌词 + 品牌名/标题/appId
python patch_lx_sqlite.py   # better-sqlite3 → node:sqlite 垫片 + 关闭原生重建

# 3) 构建
$env:NODE_ENV="production"
node build-config\pack.js
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"
node build-config\build-pack.js target=win arch=x64 type=setup
```

产物：`build\win-unpacked\`（便携）与 `build\kwlx-music-v*-x64-Setup.exe`（安装包）。

### 为什么用 `node:sqlite` 垫片

`better-sqlite3` 是**原生模块**，必须按 Electron 的 ABI 编译（需要 Visual Studio）。
而 Electron 42 内置 **Node 24**，自带 `node:sqlite`（`DatabaseSync`）。垫片实现了项目用到的
`exec / prepare().run|get|all / pragma / transaction / close`，以及 `fileMustExist` 语义，
因此**无编译器环境也能出包**。

---

## 五、许可证与改动声明（Apache-2.0 合规）

本项目分发的 kwlx music 是 **[lx-music-desktop](https://github.com/lyswhut/lx-music-desktop)（© lyswhut，Apache License 2.0）的修改版**，
遵循 Apache-2.0 分发，并在此**明确列出改动**：

1. `src/main/modules/userApi/config/index.ts`：预装音源「酷我音源 · kwlx」（脚本内联）
2. `src/common/defaultSetting.ts`：`common.apiSource` 默认值 `temp` → `kwlx_kuwo`
3. `src/main/modules/userApi/renderer/preload.js`：`supportActions.kw` 由 `['musicUrl']` 放宽为 `['musicUrl','lyric']`
4. `src/main/index.ts`：`app.setName('kwlx-music')`
5. `src/renderer/index.html`：窗口标题 `LX Music` → `kwlx Music`
6. `build-config/build-pack.js`：`appId` → `cn.kwlx.music.desktop`；`productName` → `kwlx-music`；`npmRebuild: false`
7. 新增 `src/main/worker/dbService/nodeSqliteShim.ts`，并将 `db.ts` 由 `better-sqlite3` 改为该垫片

> 未使用上游商标作为产品名；原版权与许可文件（`LICENSE`）随分发保留。
> 本项目自有代码（音源脚本、q 加密实现、补丁脚本）以 MIT 发布，q 加密算法移植自
> [JayZorn-LJZ/GetFreeMusicYourself](https://github.com/JayZorn-LJZ/GetFreeMusicYourself)（见主 README 致谢）。

---

## 六、常见问题

| 现象 | 处理 |
| --- | --- |
| 下载下来不是无损 | 下载前把音质切到「无损 FLAC」；部分歌曲平台只有 320k，会自动降级 |
| 提示拿不到播放地址 | 该曲受限；换同名其它版本（Live/翻唱）通常可以 |
| 歌词为空 | 已内置网易云兜底；若两者都失败则是该曲无版权歌词 |
| 便携版数据在哪 | `程序目录\portable\userData\LxDatas\`（含 `lx.data.db` 歌单/历史） |
| 想要官方原版 | 直接下 [lx-music 官方 Release](https://github.com/lyswhut/lx-music-desktop/releases)，再导入 `kwlx-kuwo-source.js` |
