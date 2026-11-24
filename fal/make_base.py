"""Step 1 of Brief 10: three photoreal base candidates of Hrishikesh in his default look.

Identity references come from private/ (never committed). Outputs go to out/fal/base/ (gitignored).
Usage: uv run python fal/make_base.py MODEL_ID EST_USD_PER_IMAGE [N]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fal_call import data_uri, download, fal, ledger_total  # noqa: E402

PRIV = Path.home() / "code/hrishikesh-bluehost-vibeathon/private/refs"
OUT = Path.home() / "code/hrishikesh-bluehost-vibeathon/out/fal/base"
REFS = ["face-front-fullbody.jpg", "outfit-today-mirror.jpg", "face-glasses-34.jpg", "face-front-bw.jpg"]

PROMPT = (
    "Photorealistic full-length studio photograph of the same man shown in the reference photos. Keep his exact face, "
    "curly dark hair, light stubble, skin tone, glasses shape and slim athletic build so he is instantly recognisable. "
    "Full length, head to toe, feet fully visible, facing the camera, relaxed stance, arms hanging slightly away from the body. "
    "He wears: a black poplin shirt; a beige linen overshirt worn open over it; light-wash baggy jeans; clean white court "
    "sneakers; thin gold hexagonal glasses; a gold digital watch on his left wrist. "
    "He stands on a dark stage under a cobalt blue and violet colour wash, lit by a soft white key light from the front, "
    "against a plain dark background so he can be cut out cleanly. Sharp focus, natural skin texture, 50mm lens, "
    "camera at chest height, no text, no logos, no other people."
)


def main():
    model, est = sys.argv[1], float(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    payload = {"prompt": PROMPT, "image_urls": [data_uri(PRIV / r) for r in REFS], "num_images": n,
               "output_format": "png", "aspect_ratio": "9:16"}
    try:
        res = fal(model, payload, est * n, note=f"base x{n}")
    except RuntimeError as e:
        if "422" in str(e):  # unknown field: retry without aspect_ratio
            payload.pop("aspect_ratio")
            res = fal(model, payload, est * n, note=f"base x{n} (no aspect)")
        else:
            raise
    imgs = res.get("images") or []
    tag = model.replace("/", "_")
    for i, im in enumerate(imgs, 1):
        p = download(im["url"], OUT / f"{tag}-{i}.png")
        print("saved", p)
    print("ledger USD", ledger_total())


if __name__ == "__main__":
    main()
