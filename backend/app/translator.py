import io
import fitz
import torch
import tempfile
import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_NAME = "Helsinki-NLP/opus-mt-en-zh"  # 固定英→中

def _get_translator():
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    return tok, mdl

def _translate_batch(texts, tok, mdl, batch_size=12, max_new_tokens=512):
    outs = []
    device = next(mdl.parameters()).device
    with torch.inference_mode():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            enc = tok(batch, return_tensors="pt", padding=True, truncation=True).to(device)
            gen = mdl.generate(**enc, max_new_tokens=max_new_tokens, num_beams=4)
            outs += tok.batch_decode(gen, skip_special_tokens=True)
    return outs

def _extract_blocks(page: fitz.Page):
    data = page.get_text("dict")
    blocks = []
    for b in data.get("blocks", []):
        if b.get("type", 0) != 0:
            continue
        bbox = b["bbox"]
        text = " ".join(
            span["text"]
            for line in b.get("lines", [])
            for span in line.get("spans", [])
            if span.get("text","").strip()
        ).strip()
        if text:
            blocks.append({"bbox": bbox, "text": text})
    return blocks

async def translate_pdf_en2zh(pdf_bytes: bytes, dpi: int = 144, batch_size: int = 12, font_bytes: bytes | None = None) -> bytes:
    tok, mdl = _get_translator()
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    out = fitz.open()

    # 可选：将上传字体写临时文件供 insert_textbox 使用（PyMuPDF 对 fontfile 更可靠地接受文件路径）
    fontfile = None
    tmp_font_path = None
    if font_bytes:
        # 写入一个临时 ttf 文件，然后把路径传给 insert_textbox
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
        try:
            tmp.write(font_bytes)
            tmp.flush()
            tmp.close()
            tmp_font_path = tmp.name
            fontfile = tmp_font_path
        except Exception:
            # 若写入失败，确保临时文件被清理
            try:
                tmp.close()
            except Exception:
                pass
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            raise

    for page in src:
        blocks = _extract_blocks(page)
        texts = [b["text"] for b in blocks]
        zh = _translate_batch(texts, tok, mdl, batch_size=batch_size)

        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        pix = page.get_pixmap(alpha=False, dpi=dpi)
        new_page.insert_image(page.rect, stream=pix.tobytes("png"))

        for (b, t) in zip(blocks, zh):
            rect = fitz.Rect(*b["bbox"])
            try:
                new_page.insert_textbox(
                    rect, t,
                    fontsize=10, align=0, color=(0,0,0),
                    fontname="custom",
                    fontfile=fontfile  # None 时用内置字体，建议传 CJK 字体避免方块字
                )
            except ValueError as e:
                # 更清晰的错误信息，便于调试上传的字体文件问题
                raise ValueError(f"insert_textbox failed for fontfile={fontfile}: {e}") from e

    buf = io.BytesIO()
    try:
        out.save(buf)
        out.close()
        src.close()
        return buf.getvalue()
    finally:
        # 清理临时字体文件（如果有）
        if tmp_font_path:
            try:
                os.unlink(tmp_font_path)
            except Exception:
                pass
