# kwlx music 故障修复记录（双击没反应 / 没有下载按钮）

> 现象：kwlx music 首页或搜索出来的歌**双击没反应、不播放**；界面上**看不到下载按钮**。
> 本文记录三处真实根因与修法，全部已在 v1.1.2 修复并实测验证。

---

## 根因 1：音源 id 不以 `user_api` 开头 → 应用根本不用它

lx-music 选择「用哪个音源」的判定（编译后代码）：

```js
const getApi = (source) => {
  if (/^user_api/.test(currentApiId)) return userApi.apis[source]   // 用户源
  const t = builtinApis[`${currentApiId}_api_${source}`]
  if (t) return t
  throw new Error('Api is not found')                              // ← 你看到的报错
}
```

我们把音源 id 起成了 `kwlx_kuwo`，**不匹配 `/^user_api/`** → 走了内置分支 → 每次播放都抛
`Api is not found` → 双击等于没反应。

**修法**：id 改为 **`user_api_kwlx`**，默认值 `common.apiSource` 同步为 `user_api_kwlx`。

---

## 根因 2：音源只注册了 `kw`，而列表里大多是 kg/tx/wy/mg

lx-music 的结果是**多源聚合**的。原脚本只声明 `kw` 一个源，其它源的歌**没有地址提供者** → 同样报错。

**修法**：音源**接管全部 5 个源**（`kw/kg/tx/wy/mg`）：

* `kw` 的歌：直接用 `meta.songId`（酷我 rid）解析，精确；
* 其它源的歌：用「歌名 + 歌手」在**酷我搜索**里找到对应 rid，再解析（跨源解析），并做内存缓存。

单测结果：`kg 歌曲 → 酷我 FLAC（文件头 fLaC）` ✅

---

## 根因 3：`node:sqlite` 垫片的命名参数语义与 `better-sqlite3` 不同

（这是我们为了「无 Visual Studio 也能构建」而引入的垫片）

| 场景 | better-sqlite3 | node:sqlite |
| --- | --- | --- |
| SQL 里没有的多余命名参数 | **忽略** | **抛错** `Unknown named parameter 'order'` |
| 少传的命名参数 | 绑成 NULL | **抛错** `Missing named parameter` |
| 参数值是 `undefined` | 当 NULL | 报类型错 |

结果：**"把歌曲加入播放列表"这一步写库失败** → 播放列表为空 → 双击不播放。

**修法**：垫片里做**双向容错**——按报错逐个剔除多余参数、补齐缺失参数、`undefined` 转 `null`。
单测：多余参数 / 缺失参数 / undefined / 数组参数 / 事务 **6/6 通过**。

---

## 根因 4：下载按钮整列默认隐藏

```ts
// src/common/defaultSetting.ts
'list.actionButtonsVisible': false,   // ← 每行的「播放/添加到/下载」整列默认不渲染
'download.enable': false,             // ← 下载功能默认关闭
```

模板里：

```vue
<base-virtualized-list v-if="actionButtonsVisible"> …带按钮的行… </base-virtualized-list>
<base-virtualized-list v-else>          …不带按钮的行… </base-virtualized-list>
```

**修法**：

1. 默认值改为 `true`；
2. 主进程 `initSetting()` 里**强制写入**（旧存档一并纠正并落盘）：
   ```ts
   setting = { ...(setting||{}), 'download.enable': true, 'list.actionButtonsVisible': true }
   ```
3. 行内下载按钮去掉 `appSetting['download.enable']` 门槛，**始终显示**。

---

## 根因 5（追加）：旧存档会覆盖"预装音源"

`getUserApis()` 的逻辑是：**存档里有 `userApis` 就用存档**，预装的默认值只在**首次运行**生效。
所以老用户升级后，列表里没有我们的 id → `setApi()` 直接 return → 音源永远不会加载。

**修法**：在 `getUserApis()` 里加"**确保内置音源始终存在**"——缺则补进列表并落盘（幂等）。

---

## 验证方式（可复现）

用 Chrome DevTools Protocol 驱动真实应用（不是单测）：

```powershell
# 启动带调试端口的应用
.\kwlx-music.exe --remote-debugging-port=9234
# 读运行时诊断（音源是否加载、注册了哪些源、音质档位）
node tools\cdp_state.js 9234
```

实测输出：

```json
{"status":true,"apiId":"user_api_kwlx","current":"user_api_kwlx",
 "sources":["kw","kg","tx","wy","mg"],
 "qualities":{"kw":["128k","320k","flac","flac24bit"], …}}
```

行内按钮实测：

```
rows: 15
downloadIcons: 30   downloadVisible: 30
rowAriaLabels: ["播放", "添加到...", "下载"]   ← 下载按钮已出现
```

---

## 给老用户的升级提示

* 直接用新包（v1.1.2）覆盖即可 —— 上面第 5 条会让预装音源自动补回，第 4 条的强制写入会打开下载按钮；
* 若仍有异常：**设置 → 音源** 里手动选一次「酷我音源 · kwlx」；
* 极端情况可删除数据目录重置：便携版是 `程序目录\portable\userData`，安装版是
  `%APPDATA%\lx-music-desktop`（注意这也会清空歌单/历史）。
