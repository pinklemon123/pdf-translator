from fastapi import FastAPI, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .translator import translate_pdf_en2zh
from .translator_html import translate_html
from .translator_image import translate_image_bytes

app = FastAPI(title="PDF EN->ZH Translator")

# If a frontend build is present in the repository, mount it at the root so
# visiting http://<host>:<port>/ serves the web UI instead of the OpenAPI docs.
BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = str(BASE_DIR / "frontend")
if (Path(FRONTEND_DIR) / "index.html").exists():
    # Mount frontend static files under /static to avoid shadowing API routes.
    # Serve index.html explicitly at GET / so the web UI is reachable at root,
    # while POST/PUT/etc routes (like /api/translate) are handled by FastAPI.
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend_static")

    @app.get("/", include_in_schema=False)
    async def root_index():
        # Serve the SPA entrypoint for GET / requests only.
        return FileResponse(Path(FRONTEND_DIR) / "index.html")

# Allow local front-end (http://localhost:8080) to call this API during development
# During local development it's often easiest to allow all origins to avoid
# subtle origin-matching issues between localhost/127.0.0.1 and different
# ports. Change this to a specific list before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DEV ONLY: allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/translate")
async def translate(
    pdf: UploadFile = File(...),
    direction: str = Form("en2zh"),  # 固定 en2zh
    dpi: int = Form(144),
    batch_size: int = Form(12),
    font_ttf: UploadFile | None = File(None),
):
    # quick debug logging to help diagnose 422 / missing field issues
    print(f"[translate] Received request: direction={direction}, dpi={dpi}, batch_size={batch_size}")
    print(f"[translate] pdf: filename={getattr(pdf, 'filename', None)}, content_type={getattr(pdf, 'content_type', None)}")
    if font_ttf:
        print(f"[translate] font_ttf: filename={getattr(font_ttf, 'filename', None)}, content_type={getattr(font_ttf, 'content_type', None)}")

    if direction != "en2zh":
        return Response("Only en2zh is supported.", status_code=400)

    # read uploaded bytes
    pdf_bytes = await pdf.read()
    font_bytes = await font_ttf.read() if font_ttf else None

    out_pdf = await translate_pdf_en2zh(
        pdf_bytes=pdf_bytes,
        dpi=dpi,
        batch_size=batch_size,
        font_bytes=font_bytes,
    )
    out_name = f"translated-{pdf.filename or 'translated.pdf'}"
    headers = {
        "Content-Disposition": f'attachment; filename="{out_name}"',
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    # Return a full Response with explicit no-cache headers to ensure browsers don't reuse old files
    return Response(content=out_pdf, media_type="application/pdf", headers=headers)


@app.post("/api/translate_html")
async def api_translate_html(html: UploadFile = File(...)):
    """Accept an uploaded HTML file and return a translated HTML document."""
    data = await html.read()
    out = translate_html(data.decode("utf-8", errors="ignore"))
    return Response(content=out.encode("utf-8"), media_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "no-store"})


@app.post("/api/translate_image")
async def api_translate_image(image: UploadFile = File(...), font_path: str = Form(None)):
    """Accept an uploaded image and return a translated PNG image."""
    img = await image.read()
    out = translate_image_bytes(img, font_path)
    return Response(content=out, media_type="image/png", headers={"Cache-Control": "no-store"})
