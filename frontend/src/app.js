// Import pdfjs as an ESM bundle from CDN and set worker dynamically using a blob URL.
// This avoids browser dynamic-import CORS errors when pdf.js tries to load the worker module.
import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.min.mjs";

(async () => {
  try {
  // use the ESM worker entry (.mjs) which pdf.js expects for dynamic import
  const resp = await fetch("https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.worker.min.mjs");
    const code = await resp.text();
    const blob = new Blob([code], { type: "application/javascript" });
    pdfjsLib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(blob);
  } catch (err) {
    // Fallback: try pointing to CDN directly (may still fail in some environments)
    pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.6.82/build/pdf.worker.min.js";
    console.warn("Failed to fetch pdf.worker as blob, falling back to CDN URL:", err);
  }
})();

const el = (id) => document.getElementById(id);

const inpPdf = el("inp-pdf");
const metaPages = el("meta-pages");
const rangeDpi = el("range-dpi");
const txtDpi = el("txt-dpi");
const rangeBatch = el("range-batch");
const txtBatch = el("txt-batch");
const inpFont = el("inp-font");
const btnTranslate = el("btn-translate");
const progressArea = el("progress-area");
const preview = el("preview");
const placeholder = el("placeholder");
const txtRendering = el("txt-rendering");
const txtRenderError = el("txt-render-error");

let currentFile = null;
let currentURL = null;
let rendering = false;
// Keep track of last blob URL so we can revoke it before creating a new one
let lastObjectUrl = null;

function setBusy(b) {
  rendering = b;
  inpPdf.disabled = b;
  rangeDpi.disabled = b;
  rangeBatch.disabled = b;
  inpFont.disabled = b;
  btnTranslate.disabled = b || !currentFile;
}

function clearPreview() {
  preview.innerHTML = "";
}

function revokeURL() {
  if (currentURL) {
    URL.revokeObjectURL(currentURL);
    currentURL = null;
  }
}

async function renderPreview(url) {
  setBusy(true);
  txtRenderError.style.display = "none";
  txtRendering.style.display = "inline";
  clearPreview();
  placeholder.style.display = currentFile ? "none" : "block";
  try {
    const pdf = await pdfjsLib.getDocument({ url }).promise;
    metaPages.textContent = `页面数：${pdf.numPages}`;
    metaPages.style.display = "block";
    const pagesToRender = Math.min(2, pdf.numPages);
    const scale = (parseInt(rangeDpi.value, 10) / 72) * 0.8;
    for (let i = 1; i <= pagesToRender; i++) {
      const page = await pdf.getPage(i);
      const viewport = page.getViewport({ scale });
      const canvas = document.createElement("canvas");
      canvas.className = "pdf-canvas";
      const ctx = canvas.getContext("2d");
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      preview.appendChild(canvas);
      await page.render({ canvasContext: ctx, viewport }).promise;
    }
  } catch (e) {
    console.error(e);
    txtRenderError.textContent = String(e);
    txtRenderError.style.display = "block";
  } finally {
    txtRendering.style.display = "none";
    setBusy(false);
  }
}

rangeDpi.addEventListener("input", () => {
  txtDpi.textContent = String(rangeDpi.value);
});
rangeBatch.addEventListener("input", () => {
  txtBatch.textContent = String(rangeBatch.value);
});

inpPdf.addEventListener("change", () => {
  currentFile = inpPdf.files && inpPdf.files[0] ? inpPdf.files[0] : null;
  btnTranslate.disabled = !currentFile || rendering;
  revokeURL();
  if (currentFile) {
    currentURL = URL.createObjectURL(currentFile);
    renderPreview(currentURL);
  } else {
    metaPages.style.display = "none";
    clearPreview();
    placeholder.style.display = "block";
  }
});

btnTranslate.addEventListener("click", async () => {
  if (!currentFile) return;
  setBusy(true);
  progressArea.innerHTML = `<div class="text">正在上传…</div>`;

  const form = new FormData();
  form.append("pdf", currentFile);
  form.append("direction", "en2zh");
  form.append("dpi", String(parseInt(rangeDpi.value, 10)));
  form.append("batch_size", String(parseInt(rangeBatch.value, 10)));
  if (inpFont.files && inpFont.files[0]) form.append("font_ttf", inpFont.files[0]);

  try {
  // 改为本地后端地址以便直接联通测试（使用 127.0.0.1 避免 localhost/127.0.0.1 不一致导致的 CORS 问题）
  const res = await fetch("http://127.0.0.1:8000/api/translate", { method: "POST", body: form, cache: "no-store" });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    progressArea.innerHTML = `<div class="text">服务器处理中…</div>`;
  const blob = await res.blob();
  const dlURL = URL.createObjectURL(blob);
  // try to obtain filename from Content-Disposition header
  const disposition = res.headers.get("Content-Disposition") || "";
  let filename = "translated.pdf";
  const m = /filename="?([^";]+)"?/.exec(disposition);
  if (m && m[1]) filename = m[1];
  console.log(`Downloaded blob size=${blob.size}, using filename=${filename}`);
    // revoke prior blob URL to avoid pointing to stale content
    if (lastObjectUrl) {
      try { URL.revokeObjectURL(lastObjectUrl); } catch (e) {}
      lastObjectUrl = null;
    }
    progressArea.innerHTML = `<a id="dl-link" class="btn btn-success" download="${filename}" href="${dlURL}">下载已翻译 PDF</a>`;
    lastObjectUrl = dlURL;
    // 自动触发下载（在用户点击事件处理器内触发，浏览器通常允许同源的用户发起的点击）
    try {
      const dl = document.getElementById('dl-link');
      dl.click();
    } catch (e) {
      console.warn('Auto-download failed, please click the link to download.', e);
    }
    // revoke blob on page unload to avoid leaking object URLs
    window.addEventListener('beforeunload', () => {
      if (lastObjectUrl) {
        try { URL.revokeObjectURL(lastObjectUrl); } catch (e) {}
      }
    });
  } catch (e) {
    console.error(e);
    progressArea.innerHTML = `<div class="text error">${e?.message || String(e)}</div>`;
  } finally {
    setBusy(false);
  }
});

// initialize text values
txtDpi.textContent = String(rangeDpi.value);
txtBatch.textContent = String(rangeBatch.value);

