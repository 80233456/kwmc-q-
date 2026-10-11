# -*- coding: utf-8 -*-
# 设置仓库信息 + 创建 Release 并上传两个 exe 附件
$ErrorActionPreference = 'Stop'
$owner = '80233456'
$repo = 'kwmc-q-'
$api = "https://api.github.com/repos/$owner/$repo"

$cred = "protocol=https`nhost=github.com`n`n" | git credential fill 2>$null
$tok = ($cred | Select-String -Pattern '^password=') -replace '^password=', ''
$h = @{ Authorization = "token $tok"; 'User-Agent' = 'kwmc-q-release'; Accept = 'application/vnd.github+json' }

# PowerShell 5.1 默认按 Latin-1 发送字符串 body，中文会 400 —— 统一用 UTF-8 字节
function Invoke-Json($uri, $method, $obj) {
    $json = $obj | ConvertTo-Json -Depth 6
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $hd = $h.Clone()
    $hd['Content-Type'] = 'application/json; charset=utf-8'
    return Invoke-RestMethod -Uri $uri -Method $method -Headers $hd -Body $bytes -TimeoutSec 120
}

Write-Output '=== 1) 设置仓库描述与标签 ==='
$desc = '酷我音源桌面音乐播放器 | 搜索 · 在线试听 · 无损下载 · 本地曲库 · 动画歌词 | PySide6 / Qt 6'
try {
    $r = Invoke-Json $api 'Patch' @{ description = $desc; homepage = '' }
    Write-Output ("  OK description -> " + $r.description)
} catch { Write-Output ('  描述设置失败: ' + $_.Exception.Message) }
try {
    $t = Invoke-Json "$api/topics" 'Put' @{ names = @('python', 'pyside6', 'qt6', 'music-player', 'kuwo', 'music-downloader', 'desktop-app', 'lyrics') }
    Write-Output ("  OK topics -> " + ($t.names -join ', '))
} catch { Write-Output ('  标签设置失败: ' + $_.Exception.Message) }

Write-Output '=== 2) 创建 Release v1.0.0 ==='
$notes = @'
## 音乐盒 Studio v1.0.0

基于**酷我音源**的现代桌面音乐播放器：搜索 · 在线试听 · 无损下载 · 本地曲库 · 动画歌词（PySide6 / Qt 6）

### 下载哪个？

| 文件 | 说明 |
| --- | --- |
| **音乐盒Studio-单文件版.exe**（55 MB） | ★ 推荐：**单个文件**，拷到任何 Win10/11 电脑双击即用，无需装 Python（首次启动约 3 秒） |
| **音乐盒Studio-单目录版.zip**（56 MB） | 解压后运行里面的 `音乐盒Studio.exe`，启动更快；**切勿只把 exe 单独拖出来**（会报 `Failed to load Python DLL`） |

### 功能

- **搜索**：歌曲/歌手/专辑，带专辑封面、VIP 徽标、可用音质与体积
- **试听**：双击即播线上流媒体，无需先下载
- **下载**：无损 FLAC / 320k / 128k MP3，真实进度条，按内嵌标签规范命名，可选保存歌词
- **歌词页**：平滑滚动 + 卡拉OK 渐变填充 + 切行弹入动画 + 点击任意行跳转
- **本地曲库**：自动扫描、FLAC/MP3 区分、双击播放、右键定位/删除
- **界面**：全部图标为矢量自绘（无 emoji/字体依赖），深色主题，60fps 动画

### 数据位置

- 下载歌曲：`%USERPROFILE%\Music\音乐盒Studio\`
- 设置与歌词缓存：`%LOCALAPPDATA%\MusicBoxStudio\`

### 致谢（引用的开源项目）

本项目的 q 参数加密实现与部分接口思路来自这些开源项目：

- **[JayZorn-LJZ/GetFreeMusicYourself](https://github.com/JayZorn-LJZ/GetFreeMusicYourself)** — 核心：q 参数加密算法（自定义 DES 变体）的完整实现，`kuwo_q.py` 即在其基础上移植整理
- **[CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl)** — 多平台下载器接口组织方式参考
- **[zhiyYo/Groove](https://github.com/zhiyYo/Groove)** — 封面地址拼接方式参考
- **[listen1/listen1_chrome_extension](https://github.com/listen1/listen1_chrome_extension)** — 多音源聚合接口思路
- **[UnblockNeteaseMusic/server](https://github.com/UnblockNeteaseMusic/server)** — 音源降级与歌词兜底思路
- **[sdbabd/QQKWKG-TriMusicDecrypt](https://github.com/sdbabd/QQKWKG-TriMusicDecrypt)** — 平台加解密参考资料

运行时依赖：[PySide6/Qt 6](https://www.qt.io/qt-for-python)（LGPL v3）、[FFmpeg](https://ffmpeg.org/)（LGPL v2.1+，经 Qt Multimedia 调用）。

### 免责声明

仅供个人学习与技术研究；音乐版权归原版权方所有，本项目不存储、不分发任何音乐内容。
'@
$rel = $null
try {
    $rel = Invoke-Json "$api/releases" 'Post' @{ tag_name = 'v1.0.0'; name = '音乐盒 Studio v1.0.0'; body = $notes; draft = $false; prerelease = $false }
    Write-Output ("  OK release -> " + $rel.html_url)
} catch {
    Write-Output ('  创建失败，尝试复用已存在的 release: ' + $_.Exception.Message)
    try { $rel = Invoke-RestMethod -Uri "$api/releases/tags/v1.0.0" -Headers $h -TimeoutSec 60 } catch { Write-Output '  无法获取 release，终止附件上传' }
}

if ($rel) {
    Write-Output '=== 3) 上传附件 ==='
    $files = @(
        @{ p = 'D:\project\dsh-purge\re-baseapk\dist\音乐盒Studio-单文件版.exe'; n = 'MusicBox-Studio-v1.0.0-portable.exe' },
        @{ p = 'D:\project\dsh-purge\re-baseapk\dist\音乐盒Studio-单目录版.zip'; n = 'MusicBox-Studio-v1.0.0-folder.zip' }
    )
    foreach ($f in $files) {
        if (-not (Test-Path $f.p)) { Write-Output ('  跳过（不存在）: ' + $f.p); continue }
        $size = [math]::Round((Get-Item $f.p).Length / 1MB, 1)
        Write-Output ("  上传 " + $f.n + " (" + $size + " MB) …")
        $up = "https://uploads.github.com/repos/$owner/$repo/releases/$($rel.id)/assets?name=$($f.n)"
        $uh = @{ Authorization = "token $tok"; 'User-Agent' = 'kwmc-q-release'; Accept = 'application/vnd.github+json' }
        try {
            $a = Invoke-RestMethod -Uri $up -Method Post -Headers $uh -InFile $f.p -ContentType 'application/octet-stream' -TimeoutSec 900
            Write-Output ("    OK -> " + $a.browser_download_url)
        } catch { Write-Output ('    上传失败: ' + $_.Exception.Message) }
    }
    Write-Output '=== 完成 ==='
    Write-Output ("Release 页面: " + $rel.html_url)
}
