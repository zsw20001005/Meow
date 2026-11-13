param([switch]$Performance, [switch]$Limbs, [switch]$Human)
$ErrorActionPreference = 'Stop'
$nodePath = (Get-Command node -ErrorAction Stop).Source
$url = 'http://127.0.0.1:8426/motion.html'
if ($Human) { $url += '?mode=human' }
elseif ($Performance) { $url += '?mode=performance' }
elseif ($Limbs) { $url += '?mode=limbs' }
$ready = $false
try { $ready = (Invoke-WebRequest $url -TimeoutSec 2).StatusCode -eq 200 } catch { }
if (!$ready) {
    Start-Process -FilePath $nodePath -ArgumentList ('"' + (Join-Path $PSScriptRoot 'server.mjs') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try { $ready = (Invoke-WebRequest $url -TimeoutSec 1).StatusCode -eq 200; if ($ready) { break } } catch { Start-Sleep -Milliseconds 150 }
    }
}
if (!$ready) { throw '动作预览服务未能启动，请检查本机 8426 端口。' }
Start-Process $url
