"""Test PyMuPDF insert_textbox accepts a system TTF when passed as a file path.
This avoids loading the translation model and only validates font handling (the source of "bad fontfile").

Saves no files if failing; prints PASS/FAIL and any exception.
"""
import os
import sys
from pathlib import Path
import tempfile

# ensure backend directory is on sys.path so `app` package imports work if needed
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fitz

# candidates for fonts on Windows / Linux
font_candidates = [
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\ARIAL.TTF",
    r"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    r"/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
font_path = None
for p in font_candidates:
    if os.path.isfile(p):
        font_path = p
        break

if not font_path:
    print("No system TTF found in candidates; cannot run font insertion test.")
    sys.exit(2)

print(f"Using font for test: {font_path}")

# read font bytes and write to a temp file to simulate uploaded font
try:
    with open(font_path, "rb") as f:
        font_bytes = f.read()
except Exception as e:
    print("Failed to read font file:", e)
    sys.exit(3)

tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
try:
    tmp.write(font_bytes)
    tmp.flush()
    tmp.close()
    tmp_path = tmp.name
    print("Wrote temporary font to:", tmp_path)

    # create a simple PDF page and try insert_textbox with fontfile=tmp_path
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    rect = fitz.Rect(20, 20, 180, 80)
    text = "测试中文 text"
    try:
        page.insert_textbox(rect, text, fontsize=12, align=0, color=(0, 0, 0), fontname="custom", fontfile=tmp_path)
        print("PASS: insert_textbox accepted the font file.")
        # optionally save to verify visually
        out = HERE / "font_test_out.pdf"
        doc.save(out)
        print("Wrote preview PDF:", out)
        doc.close()
    except Exception as e:
        print("FAIL: insert_textbox raised:", repr(e))
        doc.close()
        raise
finally:
    # cleanup
    try:
        os.unlink(tmp_path)
        print("Cleaned up temporary font file.")
    except Exception:
        pass

print("Test finished.")
