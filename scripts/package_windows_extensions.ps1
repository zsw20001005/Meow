param(
    [string]$Version = '0.3.0',
    [string]$Dotnet = '',
    [string]$Iscc = '',
    [switch]$SkipLocalModel
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid version' }
if (!$Dotnet) { $Dotnet = Join-Path $root '.build-tools/dotnet/dotnet.exe' }
if (!$Iscc) { $Iscc = Join-Path $root '.build-tools/installer/InnoSetup/ISCC.exe' }
$vc = Join-Path $root 'build/installer-dependencies/vc_redist.x64.exe'
$publish = & (Join-Path $PSScriptRoot 'package_windows_installer.ps1') -Version $Version -Dotnet $Dotnet -Iscc $Iscc -StageOnly -IncludeLocalModel:(!$SkipLocalModel)
$source = [IO.Path]::GetFullPath([string]$publish[-1])
if (!$source.StartsWith([IO.Path]::GetFullPath((Join-Path $root 'build/installer-stage-')), [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected staging path' }
$work = Join-Path $root ('build/modular-stage-' + [Guid]::NewGuid().ToString('N'))
$output = Join-Path $root "build/installers/modular-$Version"
New-Item -ItemType Directory -Force $work, $output | Out-Null
$packs = [ordered]@{ core='基础主包'; motion='动作表情扩展包'; bed='上床睡觉扩展包'; mail='信箱扩展包' }
if (!$SkipLocalModel) { $packs.model='本地模型扩展包' }
foreach ($id in $packs.Keys) { New-Item -ItemType Directory -Force (Join-Path $work $id) | Out-Null }
function Move-Payload([string]$relative, [string]$id) {
    $from = [IO.Path]::GetFullPath((Join-Path $source $relative))
    $to = [IO.Path]::GetFullPath((Join-Path (Join-Path $work $id) $relative))
    if (!$from.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase) -or !$to.StartsWith([IO.Path]::GetFullPath($work) + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Payload path escaped staging' }
    New-Item -ItemType Directory -Force (Split-Path -Parent $to) | Out-Null
    Move-Item -LiteralPath $from -Destination $to
}
$video = Get-Content (Join-Path $source 'Assets/Lulu/Video/manifest.json') -Raw | ConvertFrom-Json
$basic = @('idle','walk','talk','wave','happy','think','sleep','drag','fall','land','jump')
$videoFiles = @{}
foreach ($property in $video.clips.psobject.Properties) {
    $clip = $property.Value
    for ($i=0; $i -lt [math]::Ceiling($clip.frames/$video.pageFrames); $i++) {
        $file = $clip.file.Replace('{page}', [string]$i)
        $videoFiles[$file] = if ($basic -contains $property.Name) { 'core' } else { 'motion' }
    }
}
$bed = Get-Content (Join-Path $source 'Assets/Lulu/Bed/manifest.json') -Raw | ConvertFrom-Json
$bedFiles = @('manifest.json', "$($bed.assetPrefix)arrive-bed.png", "$($bed.assetPrefix)leave-bed.png")
foreach ($property in $bed.clips.psobject.Properties) {
    for ($i=0; $i -lt [math]::Ceiling($property.Value.frames/$bed.pageFrames); $i++) { $bedFiles += "$($bed.assetPrefix)$($property.Name)-$i.png" }
}
# Compatibility is tied to the exact animation definitions, not the app version.
$contentId = ((Get-FileHash (Join-Path $source 'Assets/Lulu/Video/manifest.json')).Hash + (Get-FileHash (Join-Path $source 'Assets/Lulu/Bed/manifest.json')).Hash).ToLowerInvariant()
$omitted = [Collections.Generic.List[object]]::new()
foreach ($file in @(Get-ChildItem -LiteralPath $source -File -Recurse)) {
    $relative = [IO.Path]::GetRelativePath($source, $file.FullName)
    $id = 'core'
    if ($relative -like 'Assets\Lulu\Video\*' -and $file.Name -ne 'manifest.json') { $id = $videoFiles[$file.Name] }
    elseif ($relative -like 'Assets\Lulu\Bed\*') { $id = if ($bedFiles -contains $file.Name) { 'bed' } else { $null } }
    elseif ($relative -like 'mailbridge\*') { $id = 'mail' }
    elseif ($relative -like 'local-engine\*') { $id = 'model' }
    elseif ($relative -in @('package-files.json','使用说明.txt')) { $id = $null }
    if ($id) { Move-Payload $relative $id }
    else { $omitted.Add([ordered]@{path=$relative;bytes=$file.Length}) } # Keep omitted files in staging for audit, never package them.
}
$notes = @"
Meow · 张噜噜 $Version 模块化安装

先安装基础主包。它包含现有形象、云端聊天、小本本、备忘录，以及待机、聊天、走路、挥手、开心、思考、跳跃、拖动、落地、基础睡觉和贴边动画。
动作表情扩展包：吃瓜、玩球、转圈、跳舞、打滚和更多动作表情。
上床睡觉扩展包：走到床边、上床盖被、睡眠呼吸、叫醒和离床。
信箱扩展包：设备之间寄信收信；未安装时保留历史信件和草稿。
本地模型扩展包：离线文本推理；使用云端 API 时不需要安装。

扩展包是独立安装文件，不必全部下载。安装到主程序的同一目录（安装器会尝试自动定位），安装前请退出噜噜，完成后重新启动。
设置中可查看扩展状态；扩展包可从 Windows“已安装的应用”单独卸载。
所有包均不修改个人聊天、密钥、信件和笔记。已有完整安装升级不会自动删除旧资源；若需回收旧安装空间，可卸载旧程序后重新安装，用户存档保留。
程序保留原动画分辨率和帧率，首次使用部分动作会生成可再生的磁盘缓存；此缓存不包含在下载包中。
"@
$notes | Set-Content (Join-Path $output '安装说明.txt') -Encoding utf8
$reports = @()
foreach ($id in $packs.Keys) {
    $payload = Join-Path $work $id
    if ($id -eq 'core') {
        "[Package]`nVersion=$Version`nContentId=$contentId" | Set-Content (Join-Path $payload 'package.ini') -Encoding utf8
        $notes | Set-Content (Join-Path $payload '使用说明.txt') -Encoding utf8
    }
    $inventory = @(Get-ChildItem $payload -File -Recurse | ForEach-Object { [ordered]@{path=[IO.Path]::GetRelativePath($payload,$_.FullName);bytes=$_.Length;sha256=(Get-FileHash $_.FullName).Hash.ToLowerInvariant()} })
    $inventory | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $payload "package-$id-files.json") -Encoding utf8
    $log = Join-Path $output "$id-build.log"
    & $Iscc "/DPayloadDir=$payload" "/DOutputDir=$output" "/DAppVersion=$Version" "/DPackId=$id" "/DPackName=$($packs[$id])" "/DContentId=$contentId" "/DIconFile=$root/windows/Meow.Windows/Assets/Lulu.ico" "/DVCRedist=$vc" (Join-Path $root 'windows/installer/MeowModular.iss') *> $log
    if ($LASTEXITCODE -ne 0) { Get-Content $log -Tail 30; throw "Failed to compile $id" }
    $setup = Join-Path $output "Meow-$Version-$id-Setup.exe"
    $hash = (Get-FileHash $setup).Hash.ToLowerInvariant()
    "$hash  $([IO.Path]::GetFileName($setup))" | Set-Content ($setup+'.sha256') -Encoding ascii
    $reports += [ordered]@{id=$id;name=$packs[$id];setup=$setup;bytes=(Get-Item $setup).Length;payload=$payload;payloadBytes=($inventory | Measure-Object bytes -Sum).Sum;sha256=$hash;files=$inventory.Count}
    Write-Output "$id ready: $setup"
}
[ordered]@{version=$Version;contentId=$contentId;basicClips=$basic;packs=$reports;omitted=$omitted} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $output 'build-report.json') -Encoding utf8
Write-Output "Modular installers ready: $output"
