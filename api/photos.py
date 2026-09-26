"""Photo sanitising: strip EXIF (including GPS) and downscale to 1600 px.

The web client already does this before upload; the server repeats it so a
photo can never be stored with metadata even if a client skips the step.
"""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

MAX_EDGE = 1600
PHOTO_DIR = Path(os.environ.get("PHOTO_DIR", "var/photos"))


@dataclass(frozen=True)
class SanitisedPhoto:
    data: bytes
    width: int
    height: int
    sha256: str


def sanitise(raw: bytes, max_edge: int = MAX_EDGE) -> SanitisedPhoto:
    """Return a JPEG with no metadata, longest edge at most ``max_edge``."""
    with Image.open(io.BytesIO(raw)) as img:
        img = ImageOps.exif_transpose(img)  # keep orientation before dropping EXIF
        img = img.convert("RGB")
        img.thumbnail((max_edge, max_edge))
        clean = Image.new("RGB", img.size)
        clean.paste(img)  # new image carries pixel data only, no info dict
        out = io.BytesIO()
        clean.save(out, format="JPEG", quality=85, optimize=True)
    data = out.getvalue()
    return SanitisedPhoto(data, clean.width, clean.height, hashlib.sha256(data).hexdigest())


def store(photo: SanitisedPhoto, directory: Path = PHOTO_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{photo.sha256}.jpg"
    path.write_bytes(photo.data)
    return path
