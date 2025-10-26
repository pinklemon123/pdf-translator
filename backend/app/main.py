from fastapi import FastAPI, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .translator import translate_pdf_en2zh

app = FastAPI(title="PDF EN->ZH Translator")

# Allow local front-end (http://localhost:8080) to call this API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
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
    if direction != "en2zh":
        return Response("Only en2zh is supported.", status_code=400)

    pdf_bytes = await pdf.read()
    font_bytes = await font_ttf.read() if font_ttf else None

    out_pdf = await translate_pdf_en2zh(
        pdf_bytes=pdf_bytes,
        dpi=dpi,
        batch_size=batch_size,
        font_bytes=font_bytes,
    )
    return StreamingResponse(iter([out_pdf]), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{pdf.filename or "translated.pdf"}"'})
