"""NumPy image operations for PixelLab."""

from __future__ import annotations

import numpy as np
from PIL import Image

FILTERS = {
    "grayscale": {"label": "Grayscale", "description": "Classic monochrome using luminance weights.", "icon": "◐", "controls": []},
    "saturation": {"label": "Saturation", "description": "Mute or intensify the image's colors.", "icon": "◉", "controls": [{"key": "factor", "label": "Intensity", "min": 0, "max": 3, "step": 0.1, "default": 1.5, "display": "×"}]},
    "brightness": {"label": "Brightness", "description": "Lighten or darken the image.", "icon": "☼", "controls": [{"key": "amount", "label": "Brightness", "min": -100, "max": 100, "step": 1, "default": 20, "display": ""}]},
    "contrast": {"label": "Contrast", "description": "Adjust separation between light and dark.", "icon": "◑", "controls": [{"key": "factor", "label": "Contrast", "min": 0, "max": 3, "step": 0.1, "default": 1.3, "display": "×"}]},
    "invert": {"label": "Negative", "description": "Invert RGB channels like a photographic negative.", "icon": "◒", "controls": []},
    "threshold": {"label": "Threshold", "description": "Create a high-contrast monochrome mask.", "icon": "◧", "controls": [{"key": "level", "label": "Threshold level", "min": 0, "max": 255, "step": 1, "default": 128, "display": ""}]},
    "blur": {"label": "Box Blur", "description": "Smooth detail with a NumPy box kernel.", "icon": "▦", "controls": [{"key": "radius", "label": "Blur radius", "min": 1, "max": 5, "step": 1, "default": 1, "display": " px"}]},
    "edges": {"label": "Edge Detection", "description": "Highlight intensity changes with Sobel gradients.", "icon": "⌁", "controls": [{"key": "strength", "label": "Edge strength", "min": 0.5, "max": 3, "step": 0.1, "default": 1.2, "display": "×"}]},
}


def _value(params: dict, key: str, default: float, low: float, high: float) -> float:
    try:
        value = float(params.get(key, default))
    except (TypeError, ValueError):
        raise ValueError(f"Invalid value for {key}.")
    if not np.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}.")
    return value


def grayscale(pixels: np.ndarray) -> np.ndarray:
    rgb = pixels.astype(np.float32)
    gray = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    gray = np.clip(gray, 0, 255).astype(np.uint8)
    return np.stack((gray, gray, gray), axis=2)


def saturation(pixels: np.ndarray, factor: float) -> np.ndarray:
    hsv = np.asarray(Image.fromarray(pixels, "RGB").convert("HSV"), dtype=np.uint8).copy()
    hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * factor, 0, 255).astype(np.uint8)
    return np.asarray(Image.fromarray(hsv, "HSV").convert("RGB"), dtype=np.uint8)


def brightness(pixels: np.ndarray, amount: float) -> np.ndarray:
    return np.clip(pixels.astype(np.int16) + int(amount), 0, 255).astype(np.uint8)


def contrast(pixels: np.ndarray, factor: float) -> np.ndarray:
    values = pixels.astype(np.float32)
    return np.clip((values - 127.5) * factor + 127.5, 0, 255).astype(np.uint8)


def invert(pixels: np.ndarray) -> np.ndarray:
    return 255 - pixels


def threshold(pixels: np.ndarray, level: float) -> np.ndarray:
    mask = np.where(grayscale(pixels)[:, :, 0] >= level, 255, 0).astype(np.uint8)
    return np.stack((mask, mask, mask), axis=2)


def box_blur(pixels: np.ndarray, radius: int) -> np.ndarray:
    """Box blur based on NumPy padding and an integral image."""
    radius = int(radius)
    padded = np.pad(pixels.astype(np.float32), ((radius, radius), (radius, radius), (0, 0)), mode="edge")
    integral = np.pad(padded, ((1, 0), (1, 0), (0, 0)), mode="constant").cumsum(0).cumsum(1)
    size = 2 * radius + 1
    sums = (integral[size:, size:] - integral[:-size, size:] - integral[size:, :-size] + integral[:-size, :-size])
    return np.clip(sums / (size * size), 0, 255).astype(np.uint8)


def edge_detection(pixels: np.ndarray, strength: float) -> np.ndarray:
    gray = grayscale(pixels)[:, :, 0].astype(np.float32)
    p = np.pad(gray, ((1, 1), (1, 1)), mode="edge")
    gx = (-p[:-2, :-2] + p[:-2, 2:] - 2*p[1:-1, :-2] + 2*p[1:-1, 2:] - p[2:, :-2] + p[2:, 2:])
    gy = (-p[:-2, :-2] - 2*p[:-2, 1:-1] - p[:-2, 2:] + p[2:, :-2] + 2*p[2:, 1:-1] + p[2:, 2:])
    edges = np.clip(np.sqrt(gx*gx + gy*gy) * strength, 0, 255).astype(np.uint8)
    return np.stack((edges, edges, edges), axis=2)


def apply_filter(pixels: np.ndarray, name: str, params: dict | None = None) -> np.ndarray:
    if pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ValueError("Expected an RGB image array.")
    params = params or {}
    if name == "grayscale":
        result = grayscale(pixels)
    elif name == "saturation":
        result = saturation(pixels, _value(params, "factor", 1.5, 0, 3))
    elif name == "brightness":
        result = brightness(pixels, _value(params, "amount", 20, -100, 100))
    elif name == "contrast":
        result = contrast(pixels, _value(params, "factor", 1.3, 0, 3))
    elif name == "invert":
        result = invert(pixels)
    elif name == "threshold":
        result = threshold(pixels, _value(params, "level", 128, 0, 255))
    elif name == "blur":
        result = box_blur(pixels, int(_value(params, "radius", 1, 1, 5)))
    elif name == "edges":
        result = edge_detection(pixels, _value(params, "strength", 1.2, 0.5, 3))
    else:
        raise ValueError("Unknown filter.")
    return np.ascontiguousarray(result, dtype=np.uint8)


def image_stats(pixels: np.ndarray) -> dict:
    return {
        "width": int(pixels.shape[1]), "height": int(pixels.shape[0]),
        "channels": int(pixels.shape[2]), "dtype": str(pixels.dtype),
        "min": int(pixels.min()), "max": int(pixels.max()),
        "mean": round(float(pixels.mean()), 2),
        "memory_kb": round(pixels.nbytes / 1024, 1),
    }


def make_histogram(pixels: np.ndarray) -> dict:
    histograms = {}
    for channel, name in enumerate(("red", "green", "blue")):
        counts, _ = np.histogram(pixels[:, :, channel], bins=32, range=(0, 256))
        histograms[name] = counts.astype(int).tolist()
    return {"channels": histograms}
