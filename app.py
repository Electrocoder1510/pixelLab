from __future__ import annotations

import base64
import io
import os
import uuid
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, render_template, request, send_file, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from image_ops import FILTERS, apply_filter, image_stats, make_histogram

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "instance" / "uploads"
OUTPUT_DIR = BASE_DIR / "instance" / "outputs"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
MAX_UPLOAD_BYTES = 12 * 1024 * 1024

for folder in (UPLOAD_DIR, OUTPUT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
app.config["SECRET_KEY"] = os.environ.get("PIXELLAB_SECRET_KEY", "local-dev-only")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def read_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def image_data_url(pixels: np.ndarray) -> str:
    buffer = io.BytesIO()
    Image.fromarray(pixels, mode="RGB").save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


@app.get("/")
def index():
    return render_template("index.html", filters=FILTERS)


@app.post("/api/upload")
def upload():
    file = request.files.get("image")
    if file is None or not file.filename:
        return jsonify(error="Choose an image first."), 400
    if not allowed_file(file.filename):
        return jsonify(error="Unsupported format. Use PNG, JPG, WEBP or BMP."), 400

    original_name = secure_filename(file.filename) or "image"
    image_id = uuid.uuid4().hex
    path = UPLOAD_DIR / f"{image_id}_{original_name}"
    try:
        raw = file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            return jsonify(error="Image exceeds the 12 MB limit."), 413
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.convert("RGB").save(path, format="PNG")
        pixels = read_rgb(path)
    except (UnidentifiedImageError, OSError, ValueError):
        path.unlink(missing_ok=True)
        return jsonify(error="The uploaded file is not a readable image."), 400

    return jsonify(
        image_id=image_id,
        filename=original_name,
        preview=image_data_url(pixels),
        stats=image_stats(pixels),
        histogram=make_histogram(pixels),
    )


@app.post("/api/process")
def process():
    data = request.get_json(silent=True) or {}
    image_id = str(data.get("image_id", ""))
    filter_name = str(data.get("filter", ""))
    params = data.get("params") or {}

    if len(image_id) != 32 or not image_id.isalnum():
        return jsonify(error="Upload an image before applying a filter."), 400
    if filter_name not in FILTERS:
        return jsonify(error="Choose a supported filter."), 400

    sources = list(UPLOAD_DIR.glob(f"{image_id}_*"))
    if not sources:
        return jsonify(error="The original image was not found. Upload it again."), 404

    try:
        original = read_rgb(sources[0])
        processed = apply_filter(original, filter_name, params)
        output_id = uuid.uuid4().hex
        output_path = OUTPUT_DIR / f"{output_id}.png"
        Image.fromarray(processed, mode="RGB").save(output_path, format="PNG")
    except (TypeError, ValueError, KeyError) as error:
        return jsonify(error=str(error)), 400
    except OSError:
        app.logger.exception("Image processing failed")
        return jsonify(error="Could not process this image."), 500

    return jsonify(
        output_id=output_id,
        preview=image_data_url(processed),
        download_url=url_for("download", output_id=output_id),
        stats=image_stats(processed),
        histogram=make_histogram(processed),
        filter_label=FILTERS[filter_name]["label"],
    )


@app.get("/api/download/<output_id>")
def download(output_id: str):
    if len(output_id) != 32 or not output_id.isalnum():
        return jsonify(error="Invalid download ID."), 400
    path = OUTPUT_DIR / f"{output_id}.png"
    if not path.is_file():
        return jsonify(error="Output not found. Apply the filter again."), 404
    return send_file(path, mimetype="image/png", as_attachment=True, download_name="pixellab-output.png")


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="Image exceeds the 12 MB upload limit."), 413


if __name__ == "__main__":
    app.run(debug=True)
