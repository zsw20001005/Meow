param([string]$Node = 'node')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$target=Join-Path $root 'windows/Meow.MailBridge'
$cache=Join-Path $root '.build-tools'
New-Item -ItemType Directory -Force $cache | Out-Null
foreach($package in @('iroh','iroh-win32-x64-msvc')) {
    $meta=Invoke-RestMethod ('https://registry.npmjs.org/@number0/'+$package+'/1.2.0')
    $archive=Join-Path $cache ($package+'.tgz')
    Invoke-WebRequest $meta.dist.tarball -OutFile $archive
    $actual=[Convert]::ToBase64String([Security.Cryptography.SHA512]::HashData([IO.File]::ReadAllBytes($archive)))
    if(('sha512-'+$actual) -ne $meta.dist.integrity){throw 'iroh integrity mismatch'}
    $directory=Join-Path $target ('node_modules/@number0/'+$package)
    New-Item -ItemType Directory -Force $directory | Out-Null
    tar -xzf $archive -C $directory --strip-components=1
    if($LASTEXITCODE -ne 0){throw 'iroh extraction failed'}
}
Copy-Item (Get-Command $Node).Source (Join-Path $target 'node.exe') -Force
Write-Output 'Windows iroh 1.2.0 ready.'
