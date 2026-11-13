param(
    [string]$Version = '0.1.0',
    [string]$Dotnet = '',
    [string]$Iscc = '',
    [string]$VCRedist = '',
    [string]$Icon = '',
    [switch]$IncludeLocalModel,
    [switch]$StageOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must have major.minor.patch format' }
if (!$Dotnet) { $Dotnet = Join-Path $projectRoot '.build-tools/dotnet/dotnet.exe' }
if (!$Iscc) { $Iscc = Join-Path $projectRoot '.build-tools/installer/InnoSetup/ISCC.exe' }
if (!$VCRedist) { $VCRedist = Join-Path $projectRoot 'build/installer-dependencies/vc_redist.x64.exe' }
if (!$Icon) { $Icon = Join-Path $projectRoot 'windows/Meow.Windows/Assets/Lulu.ico' }
foreach ($required in @($Dotnet, $Iscc, $VCRedist, $Icon)) {
    if (!(Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing build dependency: $required" }
}
$signature = Get-AuthenticodeSignature -LiteralPath $VCRedist
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') { throw 'VC runtime must have a valid Microsoft signature' }
# Always publish into a new folder: never include stale test output or user data.
$staging = Join-Path $projectRoot ('build/installer-stage-' + [Guid]::NewGuid().ToString('N'))
$output = Join-Path $projectRoot 'build/installers'
New-Item -ItemType Directory -Force $staging, $output | Out-Null
& $Dotnet publish (Join-Path $projectRoot 'windows/Meow.Windows/Meow.Windows.csproj') -c Release -r win-x64 --self-contained true -o $staging --no-restore -p:DebugType=None -p:DebugSymbols=false
if ($LASTEXITCODE -ne 0) { throw 'Publish failed' }
# A new icon path per release prevents Explorer reusing the old character icon.
Copy-Item -LiteralPath $Icon -Destination (Join-Path $staging "Lulu-$Version.ico")
$instructions = if ($IncludeLocalModel) { '安装说明.txt' } else { '精简安装说明.txt' }
Copy-Item -LiteralPath (Join-Path $projectRoot "windows/installer/$instructions") -Destination (Join-Path $staging '使用说明.txt')
$licenses = Join-Path $staging 'licenses'
New-Item -ItemType Directory -Force $licenses | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE') -Destination (Join-Path $licenses 'Meow-MIT.txt')
$sdkDirectory = Split-Path -Parent $Dotnet
Copy-Item -LiteralPath (Join-Path $sdkDirectory 'LICENSE.txt') -Destination (Join-Path $licenses 'dotnet-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $sdkDirectory 'ThirdPartyNotices.txt') -Destination (Join-Path $licenses 'dotnet-ThirdPartyNotices.txt')
foreach ($notice in @('OpenCvSharp-LICENSE.txt', 'OpenCV-LICENSE.txt')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot "build/installer-dependencies/$notice") -Destination (Join-Path $licenses $notice)
}
# Playback uses PNG atlases; only optical flow needs OpenCV. Do not distribute
# the optional FFmpeg video-I/O plugin that this application never loads.
$unusedVideoPlugin = Join-Path $staging 'opencv_videoio_ffmpeg4130_64.dll'
if (Test-Path -LiteralPath $unusedVideoPlugin) { Remove-Item -LiteralPath $unusedVideoPlugin }
if ($IncludeLocalModel) {
    $engine = Join-Path $projectRoot 'build/local-engine'
    $provenance = Get-Content (Join-Path $engine 'provenance.json') -Raw | ConvertFrom-Json
    if ((Get-FileHash (Join-Path $engine 'model.gguf') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $provenance.modelHash) { throw 'Local model hash mismatch' }
    $destination = Join-Path $staging 'local-engine'
    New-Item -ItemType Directory -Force $destination | Out-Null
    Get-ChildItem -LiteralPath $engine -File | Where-Object { $_.Name -ne 'runtime.zip' } | Copy-Item -Destination $destination
}
$files = @(Get-ChildItem -LiteralPath $staging -File -Recurse)
if (!$IncludeLocalModel -and @($files | Where-Object { $_.Extension -eq '.gguf' -or $_.FullName -match '[\\/]local-engine[\\/]' }).Count) { throw 'Lite payload must not contain a model or local engine' }
$forbidden = $files | Where-Object { $_.Name -match '^(state\.json|\.env.*|.*\.pfx|.*\.p12|.*\.lnk|.*\.pdb)$' -or $_.FullName -match '[\\/](edge-checks|mail-inbox|backups)[\\/]' }
if ($forbidden) { throw 'Unexpected private or development files in installer staging' }
$inventory = @($files | ForEach-Object {
    [ordered]@{ path = [IO.Path]::GetRelativePath($staging, $_.FullName); bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
})
$inventory | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $staging 'package-files.json') -Encoding utf8
if ($StageOnly) { Write-Output $staging; return }
& $Iscc "/DPayloadDir=$staging" "/DOutputDir=$output" "/DAppVersion=$Version" "/DVCRedist=$VCRedist" (Join-Path $projectRoot 'windows/installer/Meow.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
$baseName = if ($IncludeLocalModel) { "Meow-$Version-Windows-x64-Setup" } else { "Meow-$Version-Windows-x64-Lite-Setup" }
$setup = Join-Path $output "$baseName.exe"
$hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $([IO.Path]::GetFileName($setup))" | Set-Content -LiteralPath ($setup + '.sha256') -Encoding ascii
[ordered]@{ version=$Version; setup=$setup; sha256=$hash; bytes=(Get-Item $setup).Length; staging=$staging; localModel=$IncludeLocalModel.IsPresent } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output "$baseName.build.json") -Encoding utf8
Write-Output "Installer ready: $setup"
