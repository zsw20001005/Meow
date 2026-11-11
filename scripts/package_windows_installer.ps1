param(
    [string]$Version = '0.1.0',
    [string]$Dotnet = '',
    [string]$Iscc = '',
    [string]$VCRedist = '',
    [string]$Icon = '',
    [switch]$IncludeLocalModel
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must have major.minor.patch format' }
if (!$Dotnet) { $Dotnet = Join-Path $projectRoot '.build-tools/dotnet/dotnet.exe' }
if (!$Iscc) { $Iscc = Join-Path $projectRoot '.build-tools/installer/InnoSetup/ISCC.exe' }
if (!$VCRedist) { $VCRedist = Join-Path $projectRoot 'build/installer-dependencies/vc_redist.x64.exe' }
if (!$Icon) { $Icon = Join-Path $projectRoot 'build/installer-dependencies/Meow.ico' }
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
Copy-Item -LiteralPath $Icon -Destination (Join-Path $staging 'Meow.ico')
Copy-Item -LiteralPath (Join-Path $projectRoot 'windows/installer/安装说明.txt') -Destination (Join-Path $staging '使用说明.txt')
$licenses = Join-Path $staging 'licenses'
New-Item -ItemType Directory -Force $licenses | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE') -Destination (Join-Path $licenses 'Meow-MIT.txt')
$sdkDirectory = Split-Path -Parent $Dotnet
Copy-Item -LiteralPath (Join-Path $sdkDirectory 'LICENSE.txt') -Destination (Join-Path $licenses 'dotnet-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $sdkDirectory 'ThirdPartyNotices.txt') -Destination (Join-Path $licenses 'dotnet-ThirdPartyNotices.txt')
if ($IncludeLocalModel) {
    $engine = Join-Path $projectRoot 'build/local-engine'
    $provenance = Get-Content (Join-Path $engine 'provenance.json') -Raw | ConvertFrom-Json
    if ((Get-FileHash (Join-Path $engine 'model.gguf') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $provenance.modelHash) { throw 'Local model hash mismatch' }
    $destination = Join-Path $staging 'local-engine'
    New-Item -ItemType Directory -Force $destination | Out-Null
    Get-ChildItem -LiteralPath $engine -File | Where-Object { $_.Name -ne 'runtime.zip' } | Copy-Item -Destination $destination
}
$files = @(Get-ChildItem -LiteralPath $staging -File -Recurse)
$forbidden = $files | Where-Object { $_.Name -match '^(state\.json|\.env.*|.*\.pfx|.*\.p12|.*\.lnk|.*\.pdb)$' -or $_.FullName -match '[\\/](edge-checks|mail-inbox|backups)[\\/]' }
if ($forbidden) { throw 'Unexpected private or development files in installer staging' }
$inventory = @($files | ForEach-Object {
    [ordered]@{ path = [IO.Path]::GetRelativePath($staging, $_.FullName); bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
})
$inventory | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $staging 'package-files.json') -Encoding utf8
& $Iscc "/DPayloadDir=$staging" "/DOutputDir=$output" "/DAppVersion=$Version" "/DVCRedist=$VCRedist" (Join-Path $projectRoot 'windows/installer/Meow.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
$setup = Join-Path $output "Meow-$Version-Windows-x64-Setup.exe"
$hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $([IO.Path]::GetFileName($setup))" | Set-Content -LiteralPath ($setup + '.sha256') -Encoding ascii
[ordered]@{ version=$Version; setup=$setup; sha256=$hash; bytes=(Get-Item $setup).Length; staging=$staging; localModel=$IncludeLocalModel.IsPresent } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'build-report.json') -Encoding utf8
Write-Output "Installer ready: $setup"
