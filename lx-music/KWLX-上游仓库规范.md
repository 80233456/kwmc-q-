# lx-music 上游仓库规范速查（kwlx 改动必读）

> 这份文档是改 kwlx 前**先读**的规则清单。每一条都来自仓库里的真实文件和实测，
> 不是推测。踩过的坑标了 ⚠️。

---

## 0. 工程约定

| 规则 | 出处 |
| --- | --- |
| UTF-8 / **LF** / **2 空格缩进** / 行尾不留空格 / 文件末尾留空行 | `.editorconfig` |
| ESLint：根 `.eslintrc.cjs` 继承 `.eslintrc.base.cjs`，各子目录另有 `.eslintrc.cjs` | `src/{common,main,renderer,lang}/.eslintrc.cjs` |
| `target: ESNext`、`moduleResolution: bundler`、`resolveJsonModule: true` | `tsconfig.json` |
| Node ≥ 22 / npm ≥ 8.5.2 | `package.json#engines` |
| 组件用 **Options API + `setup()` 返回** 的写法（不是 `<script setup>`） | 全仓库 `components/**` |

---

## 1. 面向用户的文案：**必须走 i18n** ⚠️

```
src/lang/zh-cn.json   ← 简体（fallback）
src/lang/zh-tw.json
src/lang/en-us.json
src/lang/ko-kr.json   ← 四种语言都要加，缺了会 fallback 成中文
```

* 模板里：`:aria-label="$t('key')"`、`:title="$t('key')"`、`{{ $t('key') }}`
* 脚本里：`const t = useI18n()`（`src/lang/index.ts` 导出）
* **禁止**在模板/属性里直接写死中文 —— 这是我在第一版犯的错。

**已加的键**（kwlx 专用，四种语言齐全）：

| key | zh-cn |
| --- | --- |
| `lists__scan_download_dir` | 扫描下载目录 |
| `lists__scan_download_dir_tip` | 扫描下载目录，把新增歌曲加入「本地音乐（下载目录）」 |

---

## 2. 样式：less + CSS Modules ⚠️

* `<style lang="less" module>`，模板里用 `:class="$style.xxx"`
* 全局变量/混入从 `@renderer/assets/styles/layout.less` 引入（`@radius-border`、`@transition-normal` 等）
* **不允许内联样式**（除上游已有的个例）

**关键坑**：侧栏「我的列表」页头按钮默认是**几乎透明**的 —— 这是**上游设计**：

```less
.listHeader { &:hover { .listsAdd { opacity: 1; } } }   // 悬停标题区才显形
.listsAdd   { opacity: .1; }                            // 默认 .1
```

要让某个按钮**常显**，必须加修饰类（`.listsAlways { opacity: 1; }`），否则用户"看不见"。

---

## 3. 图标：隐藏 sprite + **viewBox 必须匹配自身坐标系** ⚠️⚠️

```html
<!-- src/renderer/components/layout/Icons.vue -->
<svg style="display:none"><defs>
  <g id="icon-xxx" fill="currentColor">
    <!-- 0 0 291.13 291.13-->          ← 这行注释就是该图标的坐标系
    <path d="M 50.981 282.415 ..." />
  </g>
</defs></svg>
```

用的时候：

```html
<svg height="70%" viewBox="0 0 24 24"><use xlink:href="#icon-xxx" /></svg>
```

* `viewBox` **必须是该图标注释里的那个尺寸**。用错（例如把 291×291 的图标塞进 24×24）
  → 图形被画到视口外 → **按钮是空的**（我踩过）。
* ⚠️ 这个仓库里**同名 `<g id>` 有重复定义**（`icon-musicFolder`、`icon-musicFile`、`icon-refresh`、
  `icon-list-add` 都出现两次，坐标系还不一样）。`<use>` 命中的是**第一个**，所以
  **先用 `getComputedStyle`/截图确认能画出来**，别只看 id 存在。
* 已验证可用的 24×24 图标：`icon-refresh`、`icon-list-add`、`icon-search-2`、`icon-download-2`
  （具体以 `Icons.vue` 里对应注释为准）。

---

## 4. 状态与数据流

```
src/renderer/store/<domain>/
  state.ts    ← 响应式状态（如 userLists、qualityList）
  action.ts   ← 业务动作（createUserList / addListMusics / getUserLists …）
```

* 往列表加歌：`createUserList({id,name})` → `addListMusics(id, musicInfos)`
* 生成本地歌曲信息：`window.lx.worker.main.createLocalMusicInfos(paths)`（**worker 里**有 Node fs）
* **改完数据一定要刷新状态**：`await getUserLists()`，否则侧栏不更新（我踩过）

---

## 5. 设置项

| 位置 | 作用 |
| --- | --- |
| `src/common/defaultSetting.ts` | 默认值（新增项必须在这里声明） |
| `src/common/types/app_setting.d.ts` | 类型 |
| `src/renderer/views/Setting/components/Setting*.vue` | 设置 UI（Pug；改这里要小心缩进，改坏会整块空白） |
| `src/main/utils/index.ts#initSetting` | **主进程加载设置**：旧存档优先于默认值，要强制某项只能在这里改写并落盘 |

kwlx 强制项（都在 `initSetting` 里）：

```ts
'download.enable': true               // 下载功能（上游默认关）
'list.actionButtonsVisible': true     // 每行操作按钮（上游默认关）
'common.isAgreePact': true            // 视为已同意协议，避免首启弹窗挡住界面
'player.playQuality': 'flac'          // 播放音质默认无损
```

⚠️ **许可协议弹窗** `components/layout/PactModal.vue`：首启会盖住整个界面，
`接受` 按钮还有倒计时（期间是 disabled）。排查"界面看不见/点不动"时**先看有没有这个弹窗**。

---

## 6. 构建

```powershell
$env:NODE_ENV="production"
node build-config\pack.js                                              # webpack（main/renderer/worker）
node build-config\build-pack.js target=win arch=x64 type=setup         # electron-builder
```

`build-pack.js` 已打补丁：`appId` / `productName` / `npmRebuild:false`（本机无 VS，用 node:sqlite 垫片）。

---

## 7. 验证方式（不许靠猜）

```powershell
# 启动带调试端口
.\kwlx-music.exe --remote-debugging-port=9244

# 读运行时状态（音源/设置）
node tools\check_runtime.js 9244

# 截图 + 几何/样式校验（按钮是否真的可见）
node cdp_mark.js 9244 shot.png
```

判断标准（都要满足才算"看得见"）：

1. `getBoundingClientRect()` 宽高 > 0
2. `getComputedStyle().opacity` = 1、`visibility: visible`、`display` 不是 none
3. **截图里那个坐标真的画出了东西**（这次的问题就是 1、2 都过、3 不过）

---

## 8. Apache-2.0 合规

修改上游后分发必须：保留 `LICENSE`、不使用上游商标作产品名、**列出全部改动**
（见 `KWLX-使用说明.md` 第五节）。
