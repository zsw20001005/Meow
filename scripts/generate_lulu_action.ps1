param([Parameter(Mandatory=$true)][ValidateSet('walk','sleep','eat','stretch','nod','dance')][string]$Action,[ValidateSet(4,6,8)][int]$Steps=6)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$output=Join-Path $projectRoot "build/lulu-video-free/$Action"
New-Item -ItemType Directory -Path $output -Force | Out-Null
$hostUrl='https://zerogpu-aoti-wan2-2-fp8da-aoti-faster.hf.space'
$config=(Invoke-WebRequest -Uri "$hostUrl/config" -TimeoutSec 30).Content | ConvertFrom-Json -AsHashtable
if(-not ($config.dependencies | Where-Object {$_.api_name -eq 'generate_video'})){throw 'Expected free video endpoint is unavailable'}
$image=Get-Item -LiteralPath (Join-Path $projectRoot 'windows/Meow.Windows/Assets/Lulu/reference.png')
$uploaded=@((Invoke-WebRequest -Uri "$hostUrl/gradio_api/upload" -Method Post -Form @{files=$image} -TimeoutSec 45).Content | ConvertFrom-Json -AsHashtable)
$imagePath=[string]$uploaded[0]
if($imagePath.Length -lt 12 -or !$imagePath.EndsWith('.png')){throw 'Unexpected image upload response'}
$identity='A single continuous locked-off frontal full-body shot of the exact plush yellow capybara in the reference. Keep the same round brown glasses, dark bowl haircut, orange muzzle and orange shorts. Keep the character centered, identical body proportions and camera distance, same cream background and soft lighting. '
$actionText=switch($Action){
 'walk' {
    'Start in the exact relaxed standing pose of the reference, both feet planted and arms hanging at the sides. After a brief still moment, perform two gentle complete walking-in-place cycles: left foot lifts slightly and lands, then right foot lifts slightly and lands, alternating naturally with small opposite arm swings. Remain centered without drifting or hopping. Gently decelerate and finish with both feet planted and both arms relaxed, returning to the exact original standing pose. Hold that identical starting pose for the final half second. Mouth remains softly closed throughout. '
 }
 'sleep' {
    'Start in the exact relaxed standing pose of the reference, both feet planted and arms hanging at the sides. The eyelids slowly become heavy and close. The head makes one tiny sleepy forward nod while the body breathes gently, then the character wakes softly, opens the eyes and returns the head to the exact original upright position. Finish in the identical original relaxed standing pose, and hold it for the final half second. No yawning or large mouth movement, no falling over, no arm gestures. '
 }
 'eat' {
    'Start in the exact relaxed standing pose with empty paws at the sides. Reach one paw behind the hip and bring out one small triangular watermelon slice. Hold the slice with both paws, bring it to the mouth and take one small cute bite, then lower the slice and put it back behind the hip. Relax both empty paws at the sides again, mouth closed with the same gentle smile. Feet remain planted, no change in head size. Finish in the exact original standing pose and hold it for the final half second. The watermelon is a solid handheld object, never floating or growing. '
 }
 'stretch' {
    'Start in the exact relaxed standing pose with arms at the sides. Slowly raise both short rounded paws upward in a comfortable morning stretch, lift the chin just slightly and close the eyes contentedly. Lower both paws smoothly, open the eyes and return to the exact relaxed upright starting pose. Both feet stay planted, body length and arm length stay constant. Hold the original pose for the final half second. No yawning, no body rotation, no fingers. '
 }
 'nod' {
    'Start in the exact relaxed standing pose with both feet planted and arms at the sides. Make two small slow friendly yes-nods, gently lowering and lifting only the head around the neck, with soft blinks and a closed-mouth smile. Keep the torso, paws and feet almost still. Settle back into the exact original upright head angle and relaxed standing pose and hold it for the final half second. No head shaking, no arm gestures, no bowing the whole body. '
 }
 'dance' {
    'Start in the exact relaxed standing pose. Perform a tiny cheerful dance: gently shift weight left then right twice, with small rhythmic bends of the knees and soft alternating paw swings at waist level. Keep both feet near their original positions and the character centered; movements are small, relaxed and grounded. Gradually settle and return both paws to the sides and both feet to the exact original standing pose. Hold it for the final half second. Keep a gentle closed-mouth smile. No hopping, no spins, no exaggerated arm flailing. '
 }
}
$prompt=$identity+$actionText+'The ending composition and pose must match the first frame for a seamless transition to idle. Smooth physically coherent movement with stable weight and no sudden acceleration.'
$negative='camera motion, camera cut, zoom, changing angle, sideways travel, hopping, jumping, sliding feet, huge steps, long legs, extra limbs, changing proportions, changing face, growing head, melting, morphing, jitter, ghosting, text, watermark, new props, different final pose'
if($Action -eq 'eat'){$negative=$negative.Replace('new props, ','floating food, giant watermelon, ')}
$body=@{data=@(@{path=$imagePath;orig_name='reference.png';meta=@{_type='gradio.FileData'}},$prompt,$Steps,$negative,3.5,1,1,42,$false)} | ConvertTo-Json -Depth 6
$body | Set-Content -LiteralPath (Join-Path $output 'request.json')
$job=(Invoke-WebRequest -Uri "$hostUrl/gradio_api/call/generate_video" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 45).Content | ConvertFrom-Json -AsHashtable
$job | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'job.json')
@{action=$Action;event_id=$job.event_id;output=$output} | ConvertTo-Json
