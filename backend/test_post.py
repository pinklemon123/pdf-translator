"""Simple test script to POST a small PDF and a system TTF to the backend translate endpoint.
Saves response to translated.pdf
"""
import os
import sys
import mimetypes
from pathlib import Path

OUT_PDF = Path(__file__).with_name("test.pdf")
OUT_RESP = Path(__file__).with_name("translated.pdf")

# Create a minimal one-page PDF (very small) to upload
minimal_pdf = b"%PDF-1.1\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n4 0 obj << /Length 44 >> stream\nBT /F1 24 Tf 20 100 Td (Hello) Tj ET\nendstream endobj\n5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000100 00000 n\n0000000221 00000 n\n0000000290 00000 n\ntrailer << /Root 1 0 R /Size 6 >>\nstartxref\n360\n%%EOF\n"

OUT_PDF.write_bytes(minimal_pdf)
print(f"Wrote test PDF: {OUT_PDF} ({OUT_PDF.stat().st_size} bytes)")

# Try to locate a TTF on Windows or common paths
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

if font_path:
    print(f"Using font: {font_path}")
else:
    print("No system TTF found in candidates; proceeding without font upload.")

url = "http://127.0.0.1:8000/api/translate"

# Try to use requests if available, else fallback to urllib
try:
    import requests
    # backend expects the PDF field to be named 'pdf' and the font field 'font_ttf'
    files = {"pdf": (OUT_PDF.name, OUT_PDF.open("rb"), "application/pdf")}
    if font_path:
        files["font_ttf"] = (os.path.basename(font_path), open(font_path, "rb"), "font/ttf")
    print(f"Posting to {url} ...")
    r = requests.post(url, files=files, timeout=120)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        OUT_RESP.write_bytes(r.content)
        print(f"Saved translated PDF to {OUT_RESP} ({OUT_RESP.stat().st_size} bytes)")
    else:
        print("Response text:")
        print(r.text)
    # close file objects
    for v in files.values():
        try:
            v[1].close()
        except Exception:
            pass

except Exception as e:
    print("requests not available or failed, falling back to urllib. Error:", e)
    # build multipart form manually
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    def encode_field(name, value):
        return (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
            f"{value}\r\n"
        ).encode()

    def encode_file(name, filename, content, content_type):
        return (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + content + b"\r\n"

    parts = []
    parts.append(encode_file("file", OUT_PDF.name, OUT_PDF.read_bytes(), "application/pdf"))
    if font_path:
        parts.append(encode_file("font_ttf", os.path.basename(font_path), open(font_path, "rb").read(), "font/ttf"))
    parts.append((f"--{boundary}--\r\n").encode())
    body = b"".join(parts)

    import urllib.request
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.add_header('Content-Length', str(len(body)))
    print(f"Posting to {url} using urllib ...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            code = resp.getcode()
            print(f"Status: {code}")
            if code == 200:
                OUT_RESP.write_bytes(data)
                print(f"Saved translated PDF to {OUT_RESP} ({OUT_RESP.stat().st_size} bytes)")
            else:
                print("Response length:", len(data))
    except Exception as err:
        print("Upload failed:", err)

print("Test complete.")
