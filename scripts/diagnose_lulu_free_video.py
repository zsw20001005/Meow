"""One anonymous official-client attempt to expose the service's real error."""
from pathlib import Path
import json, os

root = Path(__file__).resolve().parents[1]
os.environ["HF_HOME"] = str(root / ".build-tools" / "hf-anonymous")
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
from gradio_client import Client, handle_file

output = root / "build" / "lulu-video-free" / "nod"
request = json.loads((output / "request.json").read_text(encoding="utf-8-sig"))["data"]
request[0] = handle_file(str(root / "windows" / "Meow.Windows" / "Assets" / "Lulu" / "reference.png"))
try:
    client = Client("https://zerogpu-aoti-wan2-2-fp8da-aoti-faster.hf.space", token=False, verbose=False, download_files=False, analytics_enabled=False)
    result = client.submit(*request, api_name="/generate_video").result(timeout=80)
    report = {"success": True, "result": result}
except Exception as error:
    report = {"success": False, "error_type": type(error).__name__, "message": str(error)}
(output / "client-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
