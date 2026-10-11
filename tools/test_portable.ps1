# Verify the single-file exe: copy to an isolated dir (no _internal nearby) and run it.
$ErrorActionPreference = 'SilentlyContinue'
$src = 'D:\project\dsh-purge\re-baseapk\dist\MusicBox-Studio-onefile.exe'
if (-not (Test-Path $src)) {
    $src = Get-ChildItem 'D:\project\dsh-purge\re-baseapk\dist' -Filter '*onefile*.exe' | Select-Object -First 1
    $src = $src.FullName
}
Write-Output ("source: " + $src)
$t = Join-Path $env:TEMP 'MBPortableTest'
Remove-Item $t -Recurse -Force
New-Item -ItemType Directory -Path $t | Out-Null
Copy-Item $src (Join-Path $t 'app.exe')

$before = @(Get-ChildItem $env:TEMP -Directory -Filter '_MEI*').Count
Write-Output ("_MEI* dirs before: " + $before)
Write-Output "launching (first run self-extracts, please wait)..."

$sw = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process (Join-Path $t 'app.exe') -PassThru
$shown = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 3
    $wins = @(Get-Process -Name 'app' | Where-Object { $_.MainWindowTitle -ne '' })
    if ($wins.Count -gt 0) {
        Write-Output ("  OK: window appeared in {0:N1}s  title='{1}'  pid={2}  mem={3}MB" -f `
            $sw.Elapsed.TotalSeconds, $wins[0].MainWindowTitle, $wins[0].Id, `
            [math]::Round($wins[0].WorkingSet64 / 1MB))
        $shown = $true
        break
    }
}
if (-not $shown) {
    $state = 'alive but no window'
    if ($p.HasExited) { $state = 'exited code=' + $p.ExitCode }
    Write-Output ("  FAILED: no window within 90s; state: " + $state)
}

$after = @(Get-ChildItem $env:TEMP -Directory -Filter '_MEI*')
if ($after.Count -gt 0) {
    $d = $after[0].FullName
    $sz = (Get-ChildItem $d -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
    $n = (Get-ChildItem $d -Recurse -File).Count
    Write-Output ("  extracted dir: {0}   {1:N1} MB / {2} files" -f $d, $sz, $n)
}

Get-Process -Name 'app' | ForEach-Object { $_.Kill() }
Start-Sleep -Seconds 1
Remove-Item $t -Recurse -Force
Write-Output "(test instance cleaned up)"
