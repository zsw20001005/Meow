param([string]$Report = 'build/installers/modular-0.3.0/build-report.json')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$reportPath = [IO.Path]::GetFullPath((Join-Path $root $Report))
$buildInfo = Get-Content $reportPath -Raw | ConvertFrom-Json
$work = Join-Path $root ('build/modular-validation-' + [Guid]::NewGuid().ToString('N'))
$target = Join-Path $work 'App'
$installers = Join-Path $work 'Installers'
New-Item -ItemType Directory -Force $target,$installers | Out-Null
$results = [Collections.Generic.List[string]]::new()
function Check([bool]$condition, [string]$name) { if (!$condition) { throw $name }; $results.Add("PASS $name") }
function Run([string]$file, [string[]]$arguments, [bool]$expectSuccess=$true) {
    $process = Start-Process -FilePath $file -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if (!$process.WaitForExit(180000)) { Stop-Process -Id $process.Id; throw "Test timed out: $file" }
    $process.Refresh()
    Check (($process.ExitCode -eq 0) -eq $expectSuccess) "$([IO.Path]::GetFileName($file)) $($arguments[0]) expected exit ($($process.ExitCode))"
}
$owners = @{}
try {
    foreach ($pack in $buildInfo.packs) {
        foreach ($entry in (Get-Content (Join-Path $pack.payload "package-$($pack.id)-files.json") -Raw | ConvertFrom-Json)) {
            Check (!$owners.ContainsKey($entry.path)) "disjoint ownership: $($entry.path)"
            $owners[$entry.path]=$pack.id
            Check ((Get-FileHash (Join-Path $pack.payload $entry.path)).Hash.ToLowerInvariant() -eq $entry.sha256) "payload hash: $($entry.path)"
        }
        $id=$pack.id
        & (Join-Path $root '.build-tools/installer/InnoSetup/ISCC.exe') '/DTestMode=1' "/DPayloadDir=$($pack.payload)" "/DOutputDir=$installers" "/DAppVersion=$($buildInfo.version)" "/DPackId=$id" "/DPackName=$($pack.name)" "/DContentId=$($buildInfo.contentId)" "/DIconFile=$root/windows/Meow.Windows/Assets/Lulu.ico" "/DVCRedist=$root/build/installer-dependencies/vc_redist.x64.exe" (Join-Path $root 'windows/installer/MeowModular.iss') *> (Join-Path $work "$id-compile.log")
        if ($LASTEXITCODE -ne 0) { throw "Validation installer compile failed: $id" }
    }
    $argsBase=@('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=$target")
    function Setup([string]$id) { Join-Path $installers "Meow-$($buildInfo.version)-$id-Setup.exe" }
    Run (Setup 'motion') ($argsBase + "/LOG=$work/reject-without-core.log") $false
    Check (!(Test-Path (Join-Path $target 'Assets'))) 'extension rejected before creating payload without core'
    Run (Setup 'core') ($argsBase + "/LOG=$work/core-install.log")
    Run (Join-Path $target 'Meow.exe') @('--packagecheck','--core-only')
    Copy-Item (Join-Path $target 'package-checks.txt') (Join-Path $work 'core-checks.txt')
    Run (Join-Path $target 'Meow.exe') @('--selftest')
    # A mismatched content family must fail even in silent installation.
    $ini=Join-Path $target 'package.ini'; $original=[IO.File]::ReadAllBytes($ini)
    try {
        '[Package]' + "`nContentId=incompatible" | Set-Content $ini -Encoding utf8
        Run (Setup 'bed') ($argsBase + "/LOG=$work/reject-mismatch.log") $false
        Check (!(Test-Path (Join-Path $target 'Assets/Lulu/Bed'))) 'mismatched extension leaves no bed payload'
    } finally { [IO.File]::WriteAllBytes($ini,$original) }
    Run (Setup 'bed') ($argsBase + "/LOG=$work/bed-install.log")
    Run (Join-Path $target 'Meow.exe') @('--bed-entrycheck')
    $results.Add('PASS bed extension works without motion, mail or model extensions')
    foreach ($pack in $buildInfo.packs | Where-Object { $_.id -notin @('core','bed') }) { Run (Setup $pack.id) ($argsBase + "/LOG=$work/$($pack.id)-install.log") }
    foreach ($pack in $buildInfo.packs) {
        foreach ($entry in (Get-Content (Join-Path $pack.payload "package-$($pack.id)-files.json") -Raw | ConvertFrom-Json)) {
            Check ((Get-FileHash (Join-Path $target $entry.path)).Hash.ToLowerInvariant() -eq $entry.sha256) "installed hash: $($entry.path)"
        }
    }
    Run (Join-Path $target 'Meow.exe') @('--packagecheck')
    Copy-Item (Join-Path $target 'package-checks.txt') (Join-Path $work 'full-checks.txt')
    Run (Join-Path $target 'Meow.exe') @('--strollcheck')
    Push-Location (Join-Path $target 'mailbridge')
    try { & ./node.exe --input-type=module -e 'await import("@number0/iroh");'; Check ($LASTEXITCODE -eq 0) 'mail native dependency loads' } finally { Pop-Location }
    if ($buildInfo.packs.id -contains 'model') { Run (Join-Path $target 'Meow.exe') @('--localcheck') }
    foreach ($pack in $buildInfo.packs | Where-Object id -ne 'core') {
        Run (Join-Path $target "uninstall-$($pack.id)/unins000.exe") @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
        foreach ($entry in (Get-Content (Join-Path $pack.payload "package-$($pack.id)-files.json") -Raw | ConvertFrom-Json)) { Check (!(Test-Path (Join-Path $target $entry.path))) "uninstalled extension file: $($entry.path)" }
    }
    Run (Join-Path $target 'Meow.exe') @('--packagecheck','--core-only')
    Check (Test-Path (Join-Path $target 'Meow.exe')) 'removing extensions preserves main app'
    Run (Setup 'core') ($argsBase + "/LOG=$work/core-reinstall.log")
    Run (Join-Path $target 'uninstall-core/unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    Check (!(Test-Path (Join-Path $target 'Meow.exe'))) 'core uninstall removes executable'
    $results.Add('All modular installer checks passed. Test-mode installers omit registration/shortcuts and use a separate mutex; production registration/shortcuts were not modified.')
} catch { $results.Add("FAIL $_"); throw }
finally {
    $results | Set-Content (Join-Path $work 'results.txt') -Encoding utf8
    Copy-Item (Join-Path $work 'results.txt') (Join-Path (Split-Path $reportPath) 'verification.txt')
    Write-Output "Validation artifacts: $work"
}
