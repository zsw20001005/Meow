import json, time
from pathlib import Path
from gradio_client import Client, handle_file
ROOT=Path(__file__).resolve().parent
client=Client('https://jasongzy-make-it-animatable-v2.hf.space', download_files=str(ROOT/'rig-downloads'))
job=client.submit(progress=handle_file(str(ROOT/'lulu-rig-input.glb')),
                  param_2=True, param_3='No', param_4=[], param_5=False,
                  param_6=0.01, param_7=True, param_8=True, param_9=True,
                  param_10='LeftArm', param_11=True, param_12=None,
                  param_13=True, param_14=True, api_name='/pipeline')
print('RIG SUBMITTED once',flush=True)
previous=None
while not job.done():
    status=str(job.status())
    if status!=previous: print(status,flush=True); previous=status
    time.sleep(5)
try:
    result=job.result()
    (ROOT/'rig-result.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print('RIG COMPLETED',repr(result)[:1400],flush=True)
except Exception as exc:
    (ROOT/'rig-error.txt').write_text(str(exc),encoding='utf-8')
    print('RIG FAILED',str(exc),flush=True)
    raise
