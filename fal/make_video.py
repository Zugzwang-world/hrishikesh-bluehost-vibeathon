"""Brief 10 step 5: hero video from the Stage Ready composite (Kling image-to-video on fal)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from fal_call import data_uri, download, fal, ledger_total  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
START = Path.home() / "code/hrishikesh-bluehost-vibeathon/out/fal/video/start-composite.jpg"
OUT = Path.home() / "code/hrishikesh-bluehost-vibeathon/out/fal/video/hero-walk.mp4"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "fal-ai/kling-video/v3/pro/image-to-video"
PROMPT = ("The young man in the red cap steps forward two calm steps onto the glowing centre mark of the keynote stage, "
          "stops, and turns slowly to face the audience with a confident half smile. The moving-head stage beams sweep "
          "gently and the LED wall glows cobalt and violet. Static camera, realistic, cinematic, natural motion.")
NEG = "face change, different person, distorted hands, extra limbs, morphing clothes, text changes, camera shake, blur"
r = fal(MODEL, {"start_image_url": data_uri(START), "prompt": PROMPT, "negative_prompt": NEG, "duration": "5",
                "generate_audio": False}, 0.84, note="hero video", timeout=900)
url = (r.get("video") or {}).get("url")
download(url, OUT)
print("saved", OUT, OUT.stat().st_size, "ledger", ledger_total())
