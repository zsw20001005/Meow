param([string]$Setup = '', [string]$RestoreExecutable = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (!$Setup) { $Setup = Join-Path $root 'build/installers/Meow-0.1.0-Windows-x64-Setup.exe' }
$Setup = (Resolve-Path -LiteralPath $Setup).Path
$registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{163D833B-4C53-440A-A130-4D1362F7531F}_is1'
if (Test-Path $registry) { throw 'A real Meow installer registration exists; do not overwrite it for testing.' }
$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Meow · 张噜噜.lnk'
$startLink = Join-Path ([Environment]::GetFolderPath('Programs')) 'Meow · 张噜噜/Meow · 张噜噜.lnk'
if ((Test-Path -LiteralPath $desktop) -or (Test-Path -LiteralPath $startLink)) { throw 'Existing installer shortcuts must not be overwritten by smoke tests.' }
$work = Join-Path $root ('build/installer-smoke-' + [Guid]::NewGuid().ToString('N'))
$destination = Join-Path $work 'App'
New-Item -ItemType Directory -Force $work | Out-Null
$results = [Collections.Generic.List[string]]::new()
function Check([bool]$value, [string]$message) {
    if (!$value) { throw $message }; $results.Add("PASS $message"); Write-Output "PASS $message"
}
function Run([string]$file, [string[]]$arguments, [int]$timeout = 180) {
    $process = Start-Process -FilePath $file -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if (!$process.WaitForExit($timeout * 1000)) { Stop-Process -Id $process.Id; throw "Timeout: $file" }
    $process.Refresh()
    Check ($process.ExitCode -eq 0) "$([IO.Path]::GetFileName($file)) $($arguments[0]) exit 0"
}
$running = @(Get-Process Meow -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    if (!$RestoreExecutable) { throw 'Specify the exact current application path before stopping it for testing.' }
    $RestoreExecutable = (Resolve-Path -LiteralPath $RestoreExecutable).Path
    if (@($running | Where-Object { $_.Path -ne $RestoreExecutable }).Count -gt 0) { throw 'Unexpected Meow process; refusing to stop it' }
}
$userState = Join-Path $env:LOCALAPPDATA 'Meow.Windows/state.json'
try {
    foreach ($process in $running) { Stop-Process -Id $process.Id; $process.WaitForExit() }
    $stateHash = if (Test-Path -LiteralPath $userState) { (Get-FileHash -LiteralPath $userState).Hash } else { '' }
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=$destination", '/TYPE=full', '/TASKS=desktopicon', "/LOG=$work/install.log")
    Run $Setup $arguments
    Check (Test-Path -LiteralPath (Join-Path $destination 'Meow.exe')) 'installed executable exists'
    Check (Test-Path -LiteralPath (Join-Path $destination 'local-engine/model.gguf')) 'full install includes optional model'
    Check ((Get-ItemProperty $registry).InstallLocation.TrimEnd('\') -eq $destination.TrimEnd('\')) 'uninstall registration targets the test directory'
    $shell = New-Object -ComObject WScript.Shell
    foreach ($link in @($desktop, $startLink)) {
        Check (Test-Path -LiteralPath $link) 'installer created shortcut'
        Check ($shell.CreateShortcut($link).TargetPath -eq (Join-Path $destination 'Meow.exe')) 'shortcut targets installed executable'
    }
    $inventory = Get-Content (Join-Path $destination 'package-files.json') -Raw | ConvertFrom-Json
    foreach ($item in $inventory) {
        $file = Join-Path $destination $item.path
        if (!(Test-Path -LiteralPath $file) -or (Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -ne $item.sha256) { throw "Payload mismatch: $($item.path)" }
    }
    Check $true "all $($inventory.Count) installed payload hashes match"
    $exe = Join-Path $destination 'Meow.exe'
    foreach ($test in @('--selftest', '--edgecheck', '--bed-entrycheck', '--localcheck')) { Run $exe @($test) 120 }
    Push-Location (Join-Path $destination 'mailbridge')
    try {
        & ./node.exe --input-type=module -e 'await import("@number0/iroh"); console.log("native mail dependency loaded")'
        Check ($LASTEXITCODE -eq 0) 'bundled Node and native mail module load'
    } finally { Pop-Location }
    # Reinstalling the same version exercises the upgrade path without reading
    # or launching with the real account. Checks above use isolated test stores.
    Run $Setup $arguments
    $uninstaller = Join-Path $destination 'unins000.exe'
    Run $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=$work/uninstall.log")
    # Inno's uninstaller may finish its final self-removal in a child process.
    for ($i=0; $i -lt 20 -and (Test-Path -LiteralPath $exe); $i++) { Start-Sleep -Milliseconds 250 }
    Check (!(Test-Path -LiteralPath $exe)) 'uninstall removes program'
    Check (!(Test-Path -LiteralPath $desktop) -and !(Test-Path -LiteralPath $startLink)) 'uninstall removes its shortcuts'
    Check (!(Test-Path $registry)) 'uninstall removes its registration'
    $afterHash = if (Test-Path -LiteralPath $userState) { (Get-FileHash -LiteralPath $userState).Hash } else { '' }
    Check ($stateHash -eq $afterHash) 'real user state unchanged by install, checks, upgrade and uninstall'
    $results | Set-Content -LiteralPath (Join-Path $work 'results.txt')
    Copy-Item -LiteralPath (Join-Path $work 'results.txt') -Destination (Join-Path $root 'build/installers/verification.txt')
    Write-Output "Verification artifacts: $work"
} catch {
    $results.Add("FAIL $($_.Exception.Message)")
    $results | Set-Content -LiteralPath (Join-Path $work 'results.txt')
    throw
} finally {
    if ($RestoreExecutable -and $running.Count -gt 0) {
        Start-Process -FilePath $RestoreExecutable -WorkingDirectory (Split-Path -Parent $RestoreExecutable) -WindowStyle Hidden
    }
}
