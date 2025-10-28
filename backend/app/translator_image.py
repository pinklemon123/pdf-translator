import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import os
from .ocr import get_ocr
from .nlp import translate_batch
from .cache import translate_with_cache


def _ensure_font(font_path=None, size=24):
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    except Exception:
        pass
    return ImageFont.load_default()


def translate_image_bytes(img_bytes: bytes, font_path: str | None = None) -> bytes:
    """Translate English text in an image to Chinese and return PNG bytes.

    - Uses easyocr for detection/recognition.
    - Translates detected lines with translate_with_cache -> translate_batch.
    - Draws white rectangle and writes translated text over each box.
    """
    # read into OpenCV BGR image
    arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")

    h, w = img.shape[:2]

    reader = get_ocr()
    # easyocr returns list of results: (bbox, text, confidence)
    try:
        results = reader.readtext(img)
    except Exception:
        # fallback: return original image bytes
        ok, buf = cv2.imencode('.png', img)
        return buf.tobytes() if ok else b''

    texts = []
    boxes = []
    for box, text, conf in results:
        t = (text or '').strip()
        if not t:
            continue
        boxes.append(np.array(box).astype(int))
        texts.append(t)

    if not texts:
        ok, buf = cv2.imencode('.png', img)
        return buf.tobytes() if ok else b''

    # translate with cache
    zh = translate_with_cache(texts, translate_batch)

    # convert to PIL for drawing
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    font = _ensure_font(font_path, size=max(16, int(min(w, h) / 40)))

    for box, t in zip(boxes, zh):
        x0, y0 = box.min(axis=0)
        x1, y1 = box.max(axis=0)
        # clamp
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w - 1, x1), min(h - 1, y1)
        # white background
        draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255))
        # write text
        draw.text((x0 + 2, y0 + 1), t, fill=(0, 0, 0), font=font)

    out = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode('.png', out)
    return buf.tobytes() if ok else b''
