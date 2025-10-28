import io
import os
import tempfile
import fitz
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_NAME = "Helsinki-NLP/opus-mt-en-zh"


def _get_translator():
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    return tok, mdl


def _translate_batch(texts, tok, mdl, batch_size=12, max_new_tokens=512):
    outs, device = [], next(mdl.parameters()).device
    with torch.inference_mode():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            enc = tok(batch, return_tensors="pt", padding=True, truncation=True).to(device)
            gen = mdl.generate(**enc, max_new_tokens=max_new_tokens, num_beams=4)
            outs += tok.batch_decode(gen, skip_special_tokens=True)
    return outs


def _extract_blocks(page: fitz.Page):
    data, blocks = page.get_text("dict"), []
    for b in data.get("blocks", []):
        if b.get("type", 0) != 0:  # 只要文本块
            continue
        text = " ".join(
            s.get("text", "").strip()
            for line in b.get("lines", [])
            for s in line.get("spans", [])
            if s.get("text", "").strip()
        ).strip()
        if text:
            blocks.append({"bbox": b["bbox"], "text": text})
    return blocks


def _resolve_font_bytes(uploaded_font_bytes: bytes | None) -> bytes | None:
    if uploaded_font_bytes:
        return uploaded_font_bytes
    p = os.environ.get("DEFAULT_FONT_FILE")
    if p and os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    return None


# --- 新增：规范化矩形，避免太小写不进 ---
def _normalized_rect(page: fitz.Page, rect: fitz.Rect, min_w=40, min_h=16, pad=1.0) -> fitz.Rect:
    r = fitz.Rect(rect)
    # 加一点内边距
    r.x0 -= pad
    r.y0 -= pad
    r.x1 += pad
    r.y1 += pad
    # 宽高下限
    if r.width < min_w:
        r.x1 = r.x0 + min_w
    if r.height < min_h:
        r.y1 = r.y0 + min_h
    # 限制在页面范围内
    return r & page.rect


# --- 新增：写入文本（多级兜底） ---
def _write_block(new_page: fitz.Page, rect: fitz.Rect, text: str, fontfile: bytes | None,
                 base_font=11, min_font=7, lineheight=1.05) -> None:
    # 先规范化矩形
    rect = _normalized_rect(new_page, rect)
    # 盖白底
    new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

    # 尝试从大到小缩放字号
    fontsize = base_font
    while fontsize >= min_font:
        status = new_page.insert_textbox(
            rect, text, fontsize=fontsize, align=0, color=(0, 0, 0),
            fontname="custom", fontfile=fontfile, lineheight=lineheight
        )
        if status == 0:  # 全部写入
            return
        # 擦掉后重试
        new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
        fontsize -= 1

    # 兜底 1：扩展矩形再试一次
    bigger = rect.inflate(4) & new_page.rect
    new_page.draw_rect(bigger, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
    status = new_page.insert_textbox(
        bigger, text, fontsize=min_font, align=0, color=(0, 0, 0),
        fontname="custom", fontfile=fontfile, lineheight=lineheight
    )
    if status == 0:
        return

    # 兜底 2：在原位置下方放一个“浮动框”
    float_w = max(120, rect.width + 20)
    float_h = max(24, rect.height + 8)
    x0 = rect.x0
    y0 = min(rect.y1 + 4, new_page.rect.y1 - float_h - 2)
    floater = fitz.Rect(x0, y0, min(x0 + float_w, new_page.rect.x1 - 2), y0 + float_h)
    new_page.draw_rect(floater, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
    new_page.insert_textbox(
        floater, text, fontsize=min_font, align=0, color=(0, 0, 0),
        fontname="custom", fontfile=fontfile, lineheight=lineheight
    )


# --- 替换你的主函数 ---
async def translate_pdf_en2zh(pdf_bytes: bytes, dpi: int = 144, batch_size: int = 12,
                              font_bytes: bytes | None = None) -> bytes:
    tok, mdl = _get_translator()
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    out = fitz.open()

    font_bytes = _resolve_font_bytes(font_bytes)
    fontfile = None
    tmp_font_path = None
    if font_bytes:
        # write uploaded or resolved font bytes to a temporary file and pass its path
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
        try:
            tmp.write(font_bytes)
            tmp.flush()
            tmp.close()
            tmp_font_path = tmp.name
            fontfile = tmp_font_path
        except Exception:
            try:
                tmp.close()
            except Exception:
                pass
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            fontfile = None

    for page in src:
        blocks = _extract_blocks(page)
        # 背景：整页栅格化后贴到底图
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        pix = page.get_pixmap(alpha=False, dpi=dpi)
        new_page.insert_image(page.rect, stream=pix.tobytes("png"))

        if not blocks:  # 没有可翻译文本
            continue

        texts = [b["text"] for b in blocks]
        zh = _translate_batch(texts, tok, mdl, batch_size=batch_size)

        # 逐块写入（含最小尺寸规范 + 扩展 + 浮动框兜底）
        for b, t in zip(blocks, zh):
            rect = fitz.Rect(*b["bbox"])
            try:
                _write_block(new_page, rect, t, fontfile)
            except Exception:
                # 最终兜底（极端情况下至少放在可视区域左上角）
                fallback = fitz.Rect(20, 20, min(320, new_page.rect.x1 - 20), 80)
                new_page.draw_rect(fallback, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
                new_page.insert_textbox(
                    fallback, t, fontsize=10, align=0, color=(0, 0, 0),
                    fontname="custom", fontfile=fontfile, lineheight=1.05
                )

    buf = io.BytesIO()
    try:
        out.save(buf)
        return buf.getvalue()
    finally:
        out.close()
        src.close()
        if tmp_font_path:
            try:
                os.unlink(tmp_font_path)
            except Exception:
                pass
