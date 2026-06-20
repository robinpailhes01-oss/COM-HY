#!/usr/bin/env python3
"""
Génération d'images Harmonie via Nano Banana (Google) sur l'API KIE.

Chaîne complète :
  1. (optionnel) upload des photos de référence locales -> URLs temporaires KIE
  2. createTask (texte->image, ou image->image si des références sont fournies)
  3. polling de recordInfo jusqu'à success/fail
  4. téléchargement du/des résultat(s) dans --out

Aucune dépendance externe (stdlib uniquement).

Pré-requis : variable d'environnement KIE_API_KEY.

Exemples :
  # Texte -> image (atmosphère, mer, émotion)
  python3 scripts/generate_image.py \
      --prompt "open Mediterranean horizon, golden hour, soft wake, quiet luxury" \
      --aspect-ratio 4:5 --out photos/generated/horizon.png

  # Image -> image (fidèle au vrai bateau, Pilier 7)
  python3 scripts/generate_image.py \
      --prompt "the 12m yacht deck set for sunset, elegant, sign of life" \
      --ref photos/reference/pont.jpg --ref photos/reference/proue.jpg \
      --aspect-ratio 4:5 --out photos/generated/pont_juillet.png
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UPLOAD_URL = "https://kieai.redpandaai.co/api/file-base64-upload"
CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
RECORD_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"

MODEL_T2I = "google/nano-banana"
MODEL_I2I = "google/nano-banana-edit"

# Negative prompt constant (cf. 04_IMAGE_GENERATION.md §7)
DEFAULT_NEGATIVE = (
    "no people in swimwear posing, no party, no champagne spray, no jet-ski, "
    "no flashy gold, no navy-and-white nautical stripes, no anchor/wheel/rope/"
    "porthole motifs, no stock-photo feel, no harsh flash, no oversaturation, "
    "no HDR, no glossy 3D render, no logos/watermark/text, no front-facing "
    "identifiable faces, no catalogue product shot, no megayacht, no crowded composition"
)


def _api_key() -> str:
    key = os.environ.get("KIE_API_KEY", "").strip()
    if not key:
        sys.exit("ERREUR : variable d'environnement KIE_API_KEY absente.")
    return key


# UA navigateur : certains endpoints KIE sont derrière Cloudflare et rejettent
# l'User-Agent par défaut de Python (erreur 1010).
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _post(url: str, payload: dict, key: str) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", _UA)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("User-Agent", _UA)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_url(obj) -> str | None:
    """Cherche récursivement la première URL http(s) plausible dans une réponse."""
    if isinstance(obj, str):
        return obj if obj.startswith("http") else None
    if isinstance(obj, dict):
        # clés probables en priorité
        for k in ("downloadUrl", "fileUrl", "url", "fileURL", "downloadURL", "path"):
            v = obj.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
        for v in obj.values():
            found = _find_url(v)
            if found:
                return found
    if isinstance(obj, list):
        for v in obj:
            found = _find_url(v)
            if found:
                return found
    return None


def upload_reference(path: Path, key: str) -> str:
    raw = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    b64 = base64.b64encode(raw).decode("ascii")
    payload = {
        "base64Data": f"data:{mime};base64,{b64}",
        "uploadPath": "harmonie/reference",
        "fileName": path.name,
    }
    resp = _post(UPLOAD_URL, payload, key)
    url = _find_url(resp.get("data", resp))
    if not url:
        sys.exit(f"ERREUR upload {path.name} : URL introuvable dans la réponse :\n{resp}")
    print(f"  ↑ {path.name} -> {url}")
    return url


def create_task(prompt: str, image_urls: list[str], aspect_ratio: str,
                output_format: str, key: str) -> str:
    model = MODEL_I2I if image_urls else MODEL_T2I
    payload = {
        "model": model,
        "input": {
            "prompt": prompt,
            "output_format": output_format,
            "aspect_ratio": aspect_ratio,
        },
    }
    if image_urls:
        payload["input"]["image_urls"] = image_urls
    print(f"  → createTask ({model}, {aspect_ratio})")
    resp = _post(CREATE_URL, payload, key)
    task_id = (resp.get("data") or {}).get("taskId")
    if not task_id:
        sys.exit(f"ERREUR createTask : pas de taskId :\n{resp}")
    print(f"  taskId = {task_id}")
    return task_id


def poll(task_id: str, key: str, timeout_s: int = 300) -> list[str]:
    deadline = time.time() + timeout_s
    delay = 3
    while time.time() < deadline:
        resp = _get(f"{RECORD_URL}?taskId={task_id}", key)
        data = resp.get("data") or {}
        state = data.get("state")
        if state == "success":
            result = json.loads(data.get("resultJson") or "{}")
            urls = result.get("resultUrls") or []
            if not urls:
                sys.exit(f"ERREUR : success mais aucune resultUrls :\n{data}")
            return urls
        if state == "fail":
            sys.exit(f"ERREUR génération : {data.get('failCode')} {data.get('failMsg')}")
        print(f"  … {state}")
        time.sleep(delay)
        delay = min(delay + 2, 10)
    sys.exit("ERREUR : délai de génération dépassé.")


def download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", _UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        out.write_bytes(resp.read())
    print(f"  ✓ enregistré : {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="Génération d'images Harmonie (Nano Banana / KIE)")
    p.add_argument("--prompt", required=True, help="Brique [A·SUJET] (le reste de la charte est ajouté)")
    p.add_argument("--ref", action="append", default=[], help="Photo de référence locale (répétable)")
    p.add_argument("--aspect-ratio", default="4:5", help="4:5 (feed), 9:16 (story/réel), 1:1…")
    p.add_argument("--output-format", default="png", choices=["png", "jpeg"])
    p.add_argument("--out", default="photos/generated/harmonie.png", help="Chemin de sortie")
    p.add_argument("--no-charte", action="store_true",
                   help="Ne PAS injecter automatiquement style/lumière/négatif (prompt brut)")
    args = p.parse_args()

    key = _api_key()

    # Assemblage charte (cf. 04 §4) — sauf si --no-charte
    if args.no_charte:
        prompt = args.prompt
    else:
        prompt = (
            f"{args.prompt}. "
            "Editorial travel photography, quiet luxury Mediterranean, authentic candid "
            "moment, fine-art, soft film grain, premium magazine aesthetic. "
            "French Languedoc Mediterranean coast near Carnon/Montpellier. "
            "Natural golden-hour light, warm and soft, airy bright palette of off-white, "
            "sand, linen, soft terracotta, faded Mediterranean blue, olive, warm gold. "
            "Generous negative space, off-center composition, shallow depth of field. "
            f"NEGATIVE: {DEFAULT_NEGATIVE}."
        )

    print("Génération Harmonie —", args.aspect_ratio)
    image_urls: list[str] = []
    for ref in args.ref:
        rp = Path(ref)
        if rp.exists():
            image_urls.append(upload_reference(rp, key))
        elif ref.startswith("http"):
            image_urls.append(ref)  # déjà une URL
        else:
            sys.exit(f"ERREUR : référence introuvable : {ref}")

    task_id = create_task(prompt, image_urls, args.aspect_ratio, args.output_format, key)
    urls = poll(task_id, key)

    out = Path(args.out)
    if len(urls) == 1:
        download(urls[0], out)
    else:
        for i, u in enumerate(urls, 1):
            download(u, out.with_name(f"{out.stem}_{i}{out.suffix}"))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        sys.exit(f"ERREUR HTTP {e.code} : {e.read().decode('utf-8', 'ignore')}")
    except urllib.error.URLError as e:
        sys.exit(f"ERREUR réseau : {e.reason}")
