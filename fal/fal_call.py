"""Minimal fal client with a spend ledger. Server-side only; reads FAL_KEY from the repo .env.

Hard cap 20 USD; every call refuses once the ledger reaches 18 USD (out/fal-spend.json).
Usage from other scripts: from fal_call import fal, ledger_total
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Worktrees don't carry .env; fall back to the main checkout.
ENV_CANDIDATES = [ROOT / ".env", Path.home() / "code/hrishikesh-bluehost-vibeathon/.env"]
LEDGER = Path.home() / "code/hrishikesh-bluehost-vibeathon/out/fal-spend.json"  # one shared ledger for every worktree
STOP_AT = 18.0
_LOCK = threading.RLock()
_PENDING = [0.0]  # USD reserved by in-flight calls


def _key() -> str:
    if os.environ.get("FAL_KEY"):
        return os.environ["FAL_KEY"]
    for p in ENV_CANDIDATES:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("FAL_KEY="):
                    return line.split("=", 1)[1].strip()
    raise SystemExit("FAL_KEY missing")


def _ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text())
    except Exception:
        return {"capUSD": 20.0, "stopAtUSD": STOP_AT, "totalUSD": 0.0, "calls": []}


def ledger_total() -> float:
    return round(_ledger()["totalUSD"], 4)


def _record(model: str, est: float, note: str, ok: bool):
  with _LOCK:
    d = _ledger()
    d["calls"].append({"t": time.strftime("%H:%M:%S"), "model": model, "estUSD": est, "ok": ok, "note": note})
    if ok:
        d["totalUSD"] = round(d["totalUSD"] + est, 4)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(d, indent=2))


def data_uri(path: str | Path) -> str:
    p = Path(path)
    mt = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return f"data:{mt};base64," + base64.b64encode(p.read_bytes()).decode()


def fal(model: str, payload: dict, est_usd: float, note: str = "", timeout: int = 300) -> dict:
    """Synchronous call to https://fal.run/<model>. Refuses past the stop line."""
    with _LOCK:
        if ledger_total() + _PENDING[0] + est_usd > STOP_AT:
            raise RuntimeError(f"fal budget stop: ledger {ledger_total()} + pending {_PENDING[0]} + {est_usd} > {STOP_AT}")
        _PENDING[0] += est_usd
    req = urllib.request.Request(
        f"https://fal.run/{model}", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Key {_key()}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read())
        _record(model, est_usd, note, True)
        return out
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:600]
        _record(model, 0.0, f"{note} HTTP {e.code}", False)
        raise RuntimeError(f"fal {model} HTTP {e.code}: {body}") from None
    except Exception as e:  # timeouts etc.: count it as spent to stay safe
        _record(model, est_usd, f"{note} ERR {type(e).__name__}", True)
        raise RuntimeError(f"fal {model} {type(e).__name__}: {e}") from None
    finally:
        with _LOCK:
            _PENDING[0] -= est_usd


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r:
        dest.write_bytes(r.read())
    return dest
