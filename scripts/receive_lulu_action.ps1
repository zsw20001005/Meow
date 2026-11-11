param([Parameter(Mandatory=$true)][ValidateSet('walk','sleep','eat','stretch','nod','dance')][string]$Action)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$output=Join-Path $projectRoot "build/lulu-video-free/$Action"
$job=Get-Content -LiteralPath (Join-Path $output 'job.json') -Raw | ConvertFrom-Json
$eventsUrl='https://zerogpu-aoti-wan2-2-fp8da-aoti-faster.hf.space/gradio_api/call/generate_video/'+$job.event_id
$eventsFile=Join-Path $output 'events.txt'
curl.exe --silent --show-error --no-buffer --max-time 45 $eventsUrl --output $eventsFile
$events=Get-Content -LiteralPath $eventsFile
$completed=$events | Where-Object {$_.StartsWith('data: [{')} | Select-Object -Last 1
if(!$completed){$events | Select-Object -Last 10; if($events -contains 'event: error'){throw 'Free service returned an error; no new job was submitted.'}; Write-Output 'Job still pending'; exit 2}
$result=$completed.Substring(6) | ConvertFrom-Json -AsHashtable -NoEnumerate
$url=$result[0].url
if(([Uri]$url).Host -ne 'zerogpu-aoti-wan2-2-fp8da-aoti-faster.hf.space'){throw 'Unexpected result host'}
$video=Join-Path $output "lulu-$Action.mp4"
Invoke-WebRequest -Uri $url -OutFile $video -TimeoutSec 45
Get-Item -LiteralPath $video | Select-Object Name,Length
