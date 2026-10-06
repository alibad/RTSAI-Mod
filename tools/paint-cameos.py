#!/usr/bin/env python3
"""Paint the modern-faction build-palette cameos with the local Qwen-Image model.

Each cameo starts from a text prompt (the unit's identity in tools/cameo-subjects.json, wrapped in
one shared style), is generated as a 800x640 master by a local Qwen-Image server, and is reduced to
the native 60x48 RGB PNG the sidebar uses (ProductionPalette IconSize 60, 48).

    python tools/paint-cameos.py generate --work <dir> [--only r2m1a2s,...] [--variant 1]
    python tools/paint-cameos.py install  --work <dir> [--pick r2m1a2s=2,...]

`generate` POSTs to a Qwen-Image HTTP server (hq/quote-forge/server/qwen_image.py, default
http://localhost:8021) and writes <work>/<actor>-v<n>.png plus a .json record of the exact request
and the model identity the server reports. `--backend local` loads the same model with the same fp8
quantization in this process instead, with sequential CPU offload (steady when the GPU is shared).
Masters stay outside the repository.

`install` turns the chosen master of every actor (variant 1 unless --pick says otherwise) into
mods/rtsai/modern-factions/icons/<actor>.png and records the prompt, seed, model, crop and hashes in
tools/cameo-generation.json. SUPERSEDED on 2026-10-06: the game's cameos are now rendered from the project's
3D models by RTSAI-Art tools/cameo_render.py; `install` refuses unless --legacy. The Qwen cameos and their
record are archived in RTSAI-Art history/ (and history/_records/ART-PROVENANCE.json).

No reference images are given to the model: every cameo is text-to-image. Needs Pillow, numpy and
requests (e.g. OpenRA-AI/.venv).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "mods/rtsai/modern-factions/icons"
SUBJECTS = ROOT / "tools/cameo-subjects.json"
RECORD = ROOT / "tools/cameo-generation.json"
ENDPOINT = "http://localhost:8021"
SIZE = (60, 48)
MASTER = {"width": 800, "height": 640, "steps": 28, "cfg": 4.0}

STYLE = ("Painted unit portrait for a real-time strategy game build menu icon. {subject}, {framing}. "
         "Dramatic cinematic lighting: warm key light from the upper left, cool rim light, deep shadows. "
         "Detailed semi-realistic digital painting with painterly brushwork and crisp edges, strong readable silhouette, "
         "muted military colors, dark smoky teal-charcoal studio background with a soft vignette. No text.")
FRAMING = {
    "vehicle": "three-quarter front view from slightly above, the whole vehicle centered and filling most of the frame",
    "aircraft": "three-quarter view in flight, the whole aircraft centered and filling most of the frame",
    "ship": "three-quarter bow view from slightly above, the whole vessel centered and filling most of the frame",
    "structure": "three-quarter view from slightly above, the whole structure centered and filling most of the frame",
    "infantry": "knee-up portrait of one person in three-quarter view, centered and filling most of the frame",
}
NEGATIVE = ("text, letters, words, numbers, caption, logo, emblem, insignia, national flag, watermark, signature, "
            "frame, border, user interface, multiple subjects, duplicate, collage, cropped, cut off, out of frame, "
            "blurry, low quality, jpeg artifacts, cartoon, anime, toy, plastic model, lowres, deformed")
POSTPROCESS = ("subject-aware 5:4 crop (edge-energy bounding box, 7% margin, 55-92% of the master width), "
               "Lanczos downscale to 60x48, contrast x1.12, colour x1.08, unsharp mask r0.8/55%/2, RGB PNG")


def seed_for(actor: str, variant: int) -> int:
    return zlib.crc32(actor.encode()) % 1_000_000_000 + variant - 1


def prompt_for(kind: str, subject: str) -> str:
    return STYLE.format(subject=subject[0].upper() + subject[1:], framing=FRAMING[kind])


def subjects() -> dict[str, list[str]]:
    return json.loads(SUBJECTS.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ServerBackend:
    """The shared Qwen-Image HTTP server (hq/quote-forge/server/qwen_image.py)."""

    def __init__(self, endpoint: str):
        import requests

        self.requests, self.endpoint = requests, endpoint
        health = requests.get(endpoint + "/health", timeout=10).json()
        print("server", health.get("model"), health.get("revision"), "loaded" if health.get("loaded") else "loading", flush=True)

    def __call__(self, request: dict) -> tuple[bytes, dict]:
        for _ in range(12):
            response = self.requests.post(self.endpoint + "/generate", json=request, timeout=3600,
                                          headers={"X-Source": "rtsai-cameos"})
            if response.status_code != 503:
                break
            time.sleep(int(response.headers.get("Retry-After", "10")))
        response.raise_for_status()
        health = self.requests.get(self.endpoint + "/health", timeout=10).json()
        return response.content, {"model": health.get("model"), "revision": health.get("revision"),
                                  "mode": health.get("mode")}


class LocalBackend:
    """The same model, quantization and call as the server, loaded in this process.

    Block-level group offloading streams one transformer block at a time onto the GPU, so it keeps
    a steady pace when other work holds most of the card (whole-model offload then pages through shared
    memory). accelerate's sequential offload cannot move torchao fp8 tensors. Needs torch, diffusers,
    transformers and torchao, as the server does.
    """

    def __init__(self, model: str, stream: bool = True):
        import torch
        from diffusers import DiffusionPipeline, PipelineQuantizationConfig, TorchAoConfig as DiffTorchAo
        from huggingface_hub import snapshot_download
        from torchao.quantization import Float8WeightOnlyConfig
        from transformers import TorchAoConfig as HfTorchAo

        self.torch, self.model = torch, model
        self.revision = Path(snapshot_download(model, local_files_only=True)).name
        quant = PipelineQuantizationConfig(quant_mapping={"transformer": DiffTorchAo(Float8WeightOnlyConfig()),
                                                          "text_encoder": HfTorchAo(Float8WeightOnlyConfig())})
        from diffusers.hooks import apply_group_offloading

        print("loading", model, self.revision, "(fp8 weight-only, group offload)", flush=True)
        self.pipe = DiffusionPipeline.from_pretrained(model, quantization_config=quant, torch_dtype=torch.bfloat16)
        cuda, cpu = torch.device("cuda"), torch.device("cpu")
        blocks = 1 if stream else 2  # diffusers streams one block group at a time
        for module in (self.pipe.transformer, self.pipe.text_encoder):
            apply_group_offloading(module, onload_device=cuda, offload_device=cpu, offload_type="block_level",
                                   num_blocks_per_group=blocks, use_stream=stream)
        self.pipe.vae.to(cuda)
        self.mode = f"group_offload block_level/{blocks}{' stream' if stream else ''} (paint-cameos --backend local)"
        self.pipe.set_progress_bar_config(disable=True)

    def __call__(self, request: dict) -> tuple[bytes, dict]:
        import io

        generator = self.torch.Generator(device="cuda").manual_seed(request["seed"])
        image = self.pipe(prompt=request["prompt"], negative_prompt=request["negative_prompt"],
                          width=request["width"], height=request["height"], num_inference_steps=request["steps"],
                          true_cfg_scale=request["cfg"], generator=generator).images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue(), {"model": self.model, "revision": self.revision, "mode": self.mode}


def generate(args) -> None:
    table = subjects()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    backend = LocalBackend(args.model, not args.no_stream) if args.backend == "local" else ServerBackend(args.endpoint)
    for actor in (args.only.split(",") if args.only else sorted(table)):
        kind, subject = table[actor]
        out = work / f"{actor}-v{args.variant}.png"
        if out.exists() and not args.force:
            continue
        request = {"prompt": prompt_for(kind, subject), "negative_prompt": NEGATIVE, **MASTER,
                   "seed": seed_for(actor, args.variant)}
        started = time.time()
        png, identity = backend(request)
        if png[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"{actor}: the backend did not return a PNG")
        out.write_bytes(png)
        meta = {"actor": actor, "variant": args.variant, "kind": kind, "subject": subject, "request": request,
                "sha256": sha256(png), "seconds": round(time.time() - started, 1), **identity,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        out.with_suffix(".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        print(actor, args.variant, meta["seconds"], "s", flush=True)


def subject_box(image, margin=0.07, min_frac=0.55, max_frac=0.92):
    import numpy as np
    from PIL import ImageFilter

    grey = np.asarray(image.convert("L").filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    energy = np.abs(np.diff(grey, axis=1))[:-1, :] + np.abs(np.diff(grey, axis=0))[:, :-1]
    energy[energy < np.percentile(energy, 80)] = 0

    def span(profile):
        cumulative = np.cumsum(profile) / max(profile.sum(), 1e-6)
        return int(np.searchsorted(cumulative, 0.02)), int(np.searchsorted(cumulative, 0.98))

    x0, x1 = span(energy.sum(axis=0))
    y0, y1 = span(energy.sum(axis=1))
    width, height = image.size
    aspect = SIZE[0] / SIZE[1]
    # never keep the outer border: the model sometimes scribbles a pseudo-signature in a corner
    box_w = min(max((x1 - x0) * (1 + 2 * margin), (y1 - y0) * (1 + 2 * margin) * aspect, width * min_frac),
                width * max_frac)
    box_h = box_w / aspect
    if box_h > height:
        box_w, box_h = height * aspect, height
    cx = min(max((x0 + x1) / 2, box_w / 2), width - box_w / 2)
    cy = min(max((y0 + y1) / 2, box_h / 2), height - box_h / 2)
    return [round(cx - box_w / 2), round(cy - box_h / 2), round(cx + box_w / 2), round(cy + box_h / 2)]


def cameo(master):
    from PIL import Image, ImageEnhance, ImageFilter

    image = master.convert("RGB")
    box = subject_box(image)
    small = image.crop(box).resize(SIZE, Image.Resampling.LANCZOS, reducing_gap=3.0)
    small = ImageEnhance.Contrast(small).enhance(1.12)
    small = ImageEnhance.Color(small).enhance(1.08)
    small = small.filter(ImageFilter.UnsharpMask(radius=0.8, percent=55, threshold=2))
    return small, box


def install(args) -> None:
    from PIL import Image

    if not getattr(args, "legacy", False):
        raise SystemExit("The Qwen-Image cameos were superseded on 2026-10-06 by the rendered cameos (RTSAI-Art "
                         "tools/cameo_render.py install) and are archived in RTSAI-Art history/. Installing would "
                         "overwrite the approved icons; pass --legacy to do it anyway.")

    table = subjects()
    work = Path(args.work)
    picks = dict(item.split("=") for item in args.pick.split(",")) if args.pick else {}
    record = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    for actor in sorted(table):
        variant = int(picks.get(actor, record.get(actor, {}).get("variant", 1)))
        master = work / f"{actor}-v{variant}.png"
        meta = json.loads(master.with_suffix(".json").read_text(encoding="utf-8"))
        data = master.read_bytes()
        if sha256(data) != meta["sha256"]:
            raise ValueError(f"{master} does not match its generation record")
        with Image.open(master) as image:
            icon, box = cameo(image)
        target = ICONS / f"{actor}.png"
        icon.save(target, optimize=True)
        record[actor] = {
            "variant": variant, "kind": meta["kind"], "subject": meta["subject"],
            "prompt": meta["request"]["prompt"], "negative_prompt": meta["request"]["negative_prompt"],
            "seed": meta["request"]["seed"], "steps": meta["request"]["steps"], "cfg": meta["request"]["cfg"],
            "master_size": [meta["request"]["width"], meta["request"]["height"]],
            "model": meta["model"], "model_revision": meta["revision"], "runtime": meta["mode"],
            "generated_at": meta["generated_at"], "master_sha256": meta["sha256"],
            "crop_box": box, "postprocess": POSTPROCESS, "icon_sha256": sha256(target.read_bytes()),
        }
    RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"installed {len(table)} cameos; record: {RECORD.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--work", required=True)
    gen.add_argument("--only")
    gen.add_argument("--variant", type=int, default=1)
    gen.add_argument("--force", action="store_true")
    gen.add_argument("--endpoint", default=ENDPOINT)
    gen.add_argument("--backend", choices=("server", "local"), default="server",
                     help="server: the Qwen-Image HTTP server; local: load the model here with sequential offload")
    gen.add_argument("--model", default="Qwen/Qwen-Image", help="--backend local only")
    gen.add_argument("--no-stream", action="store_true", help="--backend local: synchronous block transfers")
    inst = sub.add_parser("install")
    inst.add_argument("--work", required=True)
    inst.add_argument("--legacy", action="store_true", help="overwrite the approved rendered cameos (pre-2026-10-06 flow)")
    inst.add_argument("--pick", help="actor=variant,... (default: the recorded or first variant)")
    args = parser.parse_args()
    generate(args) if args.command == "generate" else install(args)


if __name__ == "__main__":
    main()
