param([string]$Output = '')
$ErrorActionPreference='Stop'
if(!$Output){$Output=Join-Path (Split-Path -Parent $PSScriptRoot) 'build/local-engine'}
New-Item -ItemType Directory -Force $Output | Out-Null
$release=Invoke-RestMethod 'https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b12242'
$asset=$release.assets | Where-Object {$_.name -eq 'llama-b12242-bin-win-cpu-x64.zip'} | Select-Object -First 1
if(!$asset -or !$asset.digest){throw 'Missing official runtime hash'}
$archive=Join-Path $Output 'runtime.zip'
Invoke-WebRequest $asset.browser_download_url -OutFile $archive -TimeoutSec 300
if(('sha256:'+(Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()) -ne $asset.digest){throw 'Runtime hash mismatch'}
Expand-Archive -LiteralPath $archive -DestinationPath $Output -Force
$repo='Qwen/Qwen2.5-0.5B-Instruct-GGUF'
$meta=Invoke-RestMethod ('https://huggingface.co/api/models/'+$repo)
$tree=Invoke-RestMethod ('https://huggingface.co/api/models/'+$repo+'/tree/'+$meta.sha)
$file=$tree | Where-Object {$_.path -eq 'qwen2.5-0.5b-instruct-q4_k_m.gguf'} | Select-Object -First 1
if(!$file.lfs.oid){throw 'Missing official model hash'}
$model=Join-Path $Output 'model.gguf'
if(!(Test-Path $model) -or (Get-FileHash $model -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.lfs.oid){
    Invoke-WebRequest ('https://huggingface.co/'+$repo+'/resolve/'+$meta.sha+'/'+$file.path) -OutFile ($model+'.download') -TimeoutSec 600
    if((Get-FileHash ($model+'.download') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.lfs.oid){throw 'Model hash mismatch'}
    Move-Item -LiteralPath ($model+'.download') -Destination $model -Force
}
Invoke-WebRequest ('https://huggingface.co/'+$repo+'/raw/'+$meta.sha+'/LICENSE') -OutFile (Join-Path $Output 'MODEL-LICENSE.txt')
@{runtime=$asset.name;runtimeHash=$asset.digest;model=$repo;revision=$meta.sha;modelHash=$file.lfs.oid} | ConvertTo-Json | Set-Content (Join-Path $Output 'provenance.json')
Write-Output ('Local engine ready: '+$Output)
