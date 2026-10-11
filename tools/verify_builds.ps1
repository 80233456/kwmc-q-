# -*- coding: utf-8 -*-
"""验证两个打包版本：单文件版孤立目录运行 + 配置持久化目录落位。"""
$ErrorActionPreference = 'SilentlyContinue'
$dist = 'D:\project\dsh-purge\re-baseapk\dist'
$one = (Get-ChildItem $dist -Filter '*.exe' | Where-Object { $_.Name -like '*单文件*' }).FullName
$folderExe = Join-Path $dist '音乐盒Studio\音乐盒Studio.exe'

Write-Output '=== 0) 清理旧的自解压目录与持久目录 ==='
Get-ChildItem $env:TEMP -Directory -Filter '_MEI*' | Remove-Item -Recurse -Force
$persist = Join-Path $env:LOCALAPPDATA 'MusicBoxStudio'
if (Test-Path $persist) { Remove-Item $persist -Recurse -Force }
Write-Output ("  persistent dir exists before: " + (Test-Path $persist))

function Test-Exe([string]$path, [string]$label) {
    Write-Output ("=== " + $label + " ===")
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process $path -PassThru
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 3
        $w = @(Get-Process | Where-Object { $_.MainWindowTitle -eq '音乐盒 Studio' })
        if ($w.Count -gt 0) {
            Write-Output ("  OK window in {0:N1}s  pid={1}  mem={2}MB" -f $sw.Elapsed.TotalSeconds, $w[0].Id, [math]::Round($w[0].WorkingSet64 / 1MB))
            Start-Sleep -Seconds 3
            $w | ForEach-Object { $_.Kill() }
            return $true
        }
    }
    if ($p.HasExited) { Write-Output ("  FAILED: exited code=" + $p.ExitCode) } else { Write-Output '  FAILED: no window in 60s' }
    $p | ForEach-Object { $_.Kill() }
    return $false
}

$ok1 = Test-Exe $one '1) 单文件版（直接运行）'
$ok2 = Test-Exe $folderExe '2) 单目录版（文件夹内运行）'

Start-Sleep -Seconds 2
Write-Output '=== 3) 配置/缓存持久化目录 ==='
Write-Output ("  " + $persist + "  exists=" + (Test-Path $persist))
if (Test-Path $persist) { Get-ChildItem $persist -Recurse | Select-Object -First 5 FullName | Format-Table -AutoSize }
Write-Output '=== 4) 结论 ==='
Write-Output ("  单文件版: " + $(if ($ok1) { 'PASS' } else { 'FAIL' }))
Write-Output ("  单目录版: " + $(if ($ok2) { 'PASS' } else { 'FAIL' }))
