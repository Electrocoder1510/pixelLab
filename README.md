# PixelLab — NumPy Image Studio

A Flask web app for image manipulation, built with NumPy, Pillow, HTML, CSS and JavaScript.

## Features

- Upload PNG, JPG/JPEG, WEBP or BMP images (12 MB max)
- Before/after preview and PNG export
- Eight filters: grayscale, saturation, brightness, contrast, negative, threshold, box blur and Sobel edge detection
- Adjustable filter parameters
- Image dimensions, data type, pixel range, average intensity and array memory
- RGB histogram
- Responsive dark interface

## Run locally

Python 3.10+ is recommended.

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies and start the app:

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

## Project structure

```text
PixelLab/
├── app.py                  # Flask routes, uploads and downloads
├── image_ops.py            # NumPy image-processing functions
├── requirements.txt
├── templates/index.html    # Web interface
├── static/css/style.css   # Styling
├── static/js/app.js       # UI interactions and chart rendering
└── instance/
    ├── uploads/            # Temporary original images
    └── outputs/            # Processed PNGs
```

## NumPy concepts demonstrated

- RGB images as height × width × 3 arrays
- Vectorized array arithmetic, channel indexing and `np.stack`
- `astype` conversions to prevent unsigned integer overflow
- `np.clip` to constrain channel values to 0–255
- Padding and cumulative sums for box blur
- Sobel gradients for edge detection
- `np.histogram`, array shape, dtype and `nbytes`

Pillow handles image loading/saving and RGB/HSV conversion; pixel operations are implemented with NumPy.

## Notes

Uploads and outputs are local to the running app and are excluded from Git. This is a learning/demo project: before public deployment, add authentication, rate limiting, CSRF protections where applicable, file cleanup, and a production WSGI server. Do not use Flask's development server in production.
