"""
image_compress.py - In-memory image compression used just before encryption.

Pixel dimensions are NEVER changed. Only the encoded file size is reduced.

Modes:
  "none"    - no compression, original bytes are encrypted as-is.
  "lossless"- zero quality loss (PNG optimize / lossless WebP). Safe for
              documents, screenshots, OCR targets - always use this for text.
  "visual"  - "visually lossless": high-quality WebP/JPEG re-encode (quality
              75 by default, adjustable). Dimensions identical, perceptually
              identical, but not byte-identical. Gives the biggest size
              reduction on already-compressed camera JPEGs.
  "jp2"     - convert to JPEG 2000 (.jp2), targeting a specific output file
              size (e.g. under 1 MB), regardless of the source format.
              Dimensions are never changed. JPEG 2000's rate control lets us
              hit a target size directly in one pass (no trial and error),
              by computing the compression ratio relative to the image's
              raw (uncompressed) bitmap size: ratio = (w*h*channels) / target.

Multi-frame formats (GIF, multi-page TIFF) are always left uncompressed to
avoid breaking animation/pages.
"""

from io import BytesIO
from typing import Tuple
import os
from PIL import Image

# Let OpenJPEG use multiple CPU cores internally when encoding a single
# JPEG 2000 image (tile-level parallelism). This is separate from - and
# in addition to - the app's own multi-threaded batch processing across
# different images. JPEG 2000 encoding is inherently much slower than
# JPEG/WebP (wavelet transform vs DCT), so this helps make use of all
# available cores on real hardware.
os.environ.setdefault("OPJ_NUM_THREADS", str(os.cpu_count() or 4))

# Formats it's safe to re-encode (single-frame, no animation/pages risk)
_COMPRESSIBLE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".pnm"}

# Below this many bits-per-pixel-per-channel, JPEG 2000's wavelet
# quantization starts to show visibly (blur/ringing on edges, blocky
# gradients, softened text) - even at normal (non-zoomed) viewing.
# 2.0 bpp/channel sits in the "visually lossless" range used in imaging
# workflows: still a lossy re-encode (not pixel-exact like PNG/lossless
# WebP), but at ordinary viewing distance/zoom it looks the same as the
# original, and OCR/text legibility is preserved.
DEFAULT_MIN_JP2_BPP = 2.0


def compute_min_safe_jp2_kb(width: int, height: int, channels: int, min_bpp: float = DEFAULT_MIN_JP2_BPP) -> int:
    """
    The smallest target size (in KB) this image can be pushed to via
    compress_to_jp2() while staying at/above the min_bpp quality floor.
    Requesting a target below this returns a clamped result instead of
    silently over-compressing.
    """
    min_bytes = (width * height * channels * min_bpp) / 8.0
    return max(1, int(min_bytes / 1024) + 1)


def _is_multi_frame(img: Image.Image) -> bool:
    return getattr(img, "n_frames", 1) > 1


def compress_bytes(image_bytes: bytes, original_ext: str, mode: str, quality: int = 90) -> Tuple[bytes, str, int, int]:
    """
    Compress raw image bytes in memory before they're encrypted.

    Returns: (output_bytes, output_ext, original_size, compressed_size)
    Falls back to the original bytes untouched if compression isn't safe,
    isn't smaller, or the mode is "none".
    """
    original_size = len(image_bytes)
    ext = (original_ext or "").lower()

    if mode not in ("lossless", "visual") or ext not in _COMPRESSIBLE_EXTS:
        return image_bytes, original_ext, original_size, original_size

    try:
        img = Image.open(BytesIO(image_bytes))
        img.load()
    except Exception:
        # Not a decodable image (or corrupted) - leave untouched
        return image_bytes, original_ext, original_size, original_size

    buf = BytesIO()
    try:
        if mode == "lossless":
            if ext == ".png":
                img.save(buf, format="PNG", optimize=True, compress_level=9)
                new_ext = ".png"
            else:
                img.save(buf, format="WEBP", lossless=True, quality=100, method=2)
                new_ext = ".webp"
        else:  # visual
            if img.mode in ("RGBA", "P"):
                # Keep transparency intact - JPEG can't do alpha
                img.save(buf, format="WEBP", quality=quality, method=6)
                new_ext = ".webp"
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
                new_ext = ".jpg"
    except Exception:
        return image_bytes, original_ext, original_size, original_size

    new_bytes = buf.getvalue()
    compressed_size = len(new_bytes)

    # Safety net: only keep the compressed version if it's actually smaller
    if compressed_size >= original_size:
        return image_bytes, original_ext, original_size, original_size

    return new_bytes, new_ext, original_size, compressed_size


def compress_to_jp2_lossless(
    image_bytes: bytes,
    original_ext: str,
    raw_codestream: bool = False,
) -> Tuple[bytes, str, int, int]:
    """
    Convert any single-frame image to JPEG 2000 using the REVERSIBLE (5,3)
    wavelet transform - mathematically lossless. Unlike compress_to_jp2(),
    there is no target size and no quality floor: every pixel decodes back
    exactly as it was, so it looks identical to the original even zoomed in.

    Compression here comes purely from JP2's lossless entropy coding, so
    size reduction is modest (comparable to optimized PNG/lossless WebP) -
    there is no way to hit an aggressive small target size without giving
    up some pixel data, which is exactly what this function refuses to do.

    raw_codestream=True writes a bare .j2k codestream instead of a .jp2
    file (smaller header, no JP2 box wrapper).

    Returns: (output_bytes, output_ext, original_size, compressed_size)
    Falls back to the original bytes untouched if the image can't be
    decoded, is multi-frame (GIF/animated), or JPEG 2000 isn't available.
    """
    original_size = len(image_bytes)

    try:
        img = Image.open(BytesIO(image_bytes))
        img.load()
    except Exception:
        return image_bytes, original_ext, original_size, original_size

    if _is_multi_frame(img):
        # Don't touch animated GIFs / multi-page TIFFs
        return image_bytes, original_ext, original_size, original_size

    if img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    # irreversible=False => 5,3 reversible wavelet => bit-exact lossless.
    # No quality_layers/rate constraint, so nothing gets truncated.
    save_kwargs = dict(format="JPEG2000", irreversible=False)
    if raw_codestream:
        save_kwargs["no_jp2"] = True

    try:
        buf = BytesIO()
        img.save(buf, **save_kwargs)
        out_bytes = buf.getvalue()
    except Exception:
        # JPEG 2000 plugin unavailable or encode failed - leave untouched
        return image_bytes, original_ext, original_size, original_size

    out_ext = ".j2k" if raw_codestream else ".jp2"

    # Safety net: keep the original if JP2's overhead makes it bigger.
    if len(out_bytes) >= original_size:
        return image_bytes, original_ext, original_size, original_size

    return out_bytes, out_ext, original_size, len(out_bytes)


def compress_to_jp2(
    image_bytes: bytes,
    original_ext: str,
    target_kb: int = 1024,
    min_bpp: float = DEFAULT_MIN_JP2_BPP,
    raw_codestream: bool = False,
) -> Tuple[bytes, str, int, int, bool, int]:
    """
    Convert any single-frame image to JPEG 2000, targeting a specific
    output size (target_kb, in KB). Dimensions/pixels are never resized -
    only the wavelet compression ratio is adjusted to hit the target size.

    JPEG 2000's rate control is applied relative to the RAW (uncompressed)
    bitmap size, not the source file's size, so the target is hit precisely
    in a single encode pass - no iterative quality search needed.

    Quality floor: if target_kb would push the image below min_bpp
    bits-per-pixel-per-channel (visible degradation territory), the target
    is clamped UP to the safe minimum instead of honoring the smaller
    request - was_clamped tells the caller this happened so it can alert
    the user rather than silently under-delivering on quality.

    raw_codestream=True writes a bare .j2k codestream (no JP2 box wrapper)
    instead of a .jp2 file - a smaller header, useful when squeezing close
    to the floor. raw_codestream=False (default) writes standard .jp2.

    Returns: (output_bytes, output_ext, original_size, compressed_size,
              was_clamped, safe_min_kb)
    Falls back to the original bytes untouched if the image can't be
    decoded, is multi-frame (GIF/animated), or JPEG 2000 isn't available.
    """
    original_size = len(image_bytes)

    try:
        img = Image.open(BytesIO(image_bytes))
        img.load()
    except Exception:
        return image_bytes, original_ext, original_size, original_size, False, 0

    if _is_multi_frame(img):
        # Don't touch animated GIFs / multi-page TIFFs
        return image_bytes, original_ext, original_size, original_size, False, 0

    # JPEG 2000 needs a concrete pixel mode - RGBA/RGB are both supported,
    # keeping transparency if the source has it.
    if img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    channels = len(img.getbands())
    w, h = img.size
    raw_bitmap_size = w * h * channels

    safe_min_kb = compute_min_safe_jp2_kb(w, h, channels, min_bpp)
    was_clamped = target_kb < safe_min_kb
    effective_target_kb = safe_min_kb if was_clamped else target_kb
    target_bytes = max(1, effective_target_kb) * 1024

    # Compression ratio needed (relative to the raw bitmap) to hit the
    # target size, with a small safety margin so we land just under it.
    ratio = max(1.0, raw_bitmap_size / target_bytes) * 1.04

    save_kwargs = dict(format="JPEG2000", quality_mode="rates", quality_layers=[ratio], irreversible=True)
    if raw_codestream:
        # Forces Pillow to emit the bare J2K codestream instead of the
        # JP2 box-format container (no ISO box/metadata overhead).
        save_kwargs["no_jp2"] = True

    try:
        buf = BytesIO()
        img.save(buf, **save_kwargs)
        out_bytes = buf.getvalue()

        # If still slightly over target (rare), retry once with a bigger margin
        if len(out_bytes) > target_bytes:
            ratio2 = ratio * (len(out_bytes) / target_bytes) * 1.05
            buf2 = BytesIO()
            img.save(buf2, **{**save_kwargs, "quality_layers": [ratio2]})
            retry_bytes = buf2.getvalue()
            if len(retry_bytes) < len(out_bytes):
                out_bytes = retry_bytes
    except Exception:
        # JPEG 2000 plugin unavailable or encode failed - leave untouched
        return image_bytes, original_ext, original_size, original_size, False, safe_min_kb

    out_ext = ".j2k" if raw_codestream else ".jp2"

    # Safety net: if the format overhead makes small images bigger than
    # the original, keep the original instead (matches the "never bigger"
    # guarantee used by the lossless/visual modes).
    if len(out_bytes) >= original_size:
        return image_bytes, original_ext, original_size, original_size, was_clamped, safe_min_kb

    return out_bytes, out_ext, original_size, len(out_bytes), was_clamped, safe_min_kb