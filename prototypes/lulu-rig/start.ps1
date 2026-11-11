$ErrorActionPreference = 'Stop'
$prototypeRoot = $PSScriptRoot
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCommand) { $nodePath = $nodeCommand.Source }
else { $nodePath = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' }
if (-not (Test-Path -LiteralPath $nodePath)) { throw '请先安装 Node.js，或通过当前 Codex 环境启动。' }
$available = $false
try { $available = (Invoke-WebRequest 'http://127.0.0.1:8426/' -TimeoutSec 2).StatusCode -eq 200 } catch { }
if (-not $available) {
    Start-Process -FilePath $nodePath -ArgumentList ('"' + (Join-Path $prototypeRoot 'server.mjs') + '"') -WorkingDirectory $prototypeRoot -WindowStyle Hidden
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        try { if ((Invoke-WebRequest 'http://127.0.0.1:8426/' -TimeoutSec 1).StatusCode -eq 200) { break } } catch { Start-Sleep -Milliseconds 150 }
    }
}
Start-Process 'http://127.0.0.1:8426/' -WindowStyle Hidden
