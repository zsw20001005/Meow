param([string]$Dotnet = 'dotnet', [switch]$SelfContained, [switch]$IncludeLocalModel, [string]$Output = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $projectRoot 'windows/Meow.Windows/Meow.Windows.csproj'
if(!$Output){$Output = Join-Path $projectRoot 'build/Meow-Windows-x64'}
& $Dotnet publish $project -c Release -r win-x64 --self-contained ($SelfContained.IsPresent.ToString().ToLowerInvariant()) -o $output
if ($LASTEXITCODE -ne 0) { throw 'Windows 构建失败。' }
if($IncludeLocalModel){
    $engine=Join-Path $projectRoot 'build/local-engine'
    if(!(Test-Path (Join-Path $engine 'model.gguf'))){throw '请先运行 prepare_windows_local.ps1'}
    $destination=Join-Path $output 'local-engine'
    New-Item -ItemType Directory -Force $destination | Out-Null
    Get-ChildItem -LiteralPath $engine | Where-Object {$_.Name -ne 'runtime.zip'} | Copy-Item -Destination $destination -Recurse -Force
}
Copy-Item (Join-Path $projectRoot 'docs/WINDOWS.md') (Join-Path $output 'README.md') -Force
Write-Output "已生成：$output/Meow.exe"
