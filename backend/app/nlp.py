import logging
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

_MODEL = "Helsinki-NLP/opus-mt-en-zh"
_tok = None
_mdl = None
_dev = None

logger = logging.getLogger("nlp")


def get_mt():
    """Load and cache the tokenizer and model. Returns (tokenizer, model, device)."""
    global _tok, _mdl, _dev
    if _mdl is None:
        logger.info("Loading MT model %s", _MODEL)
        _tok = AutoTokenizer.from_pretrained(_MODEL)
        _mdl = AutoModelForSeq2SeqLM.from_pretrained(_MODEL)
        _dev = "cuda" if torch.cuda.is_available() else "cpu"
        _mdl = _mdl.to(_dev)
        logger.info("Model loaded to device: %s", _dev)
    return _tok, _mdl, _dev


def translate_batch(texts, max_new=512, batch_size=16, num_beams=4):
    """Translate a list of strings using the loaded model.

    This is a synchronous function. For async use, call it via run_in_executor.
    """
    if not texts:
        return []
    tok, mdl, dev = get_mt()
    outs = []
    with torch.inference_mode():
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            enc = tok(batch, return_tensors="pt", padding=True, truncation=True).to(dev)
            gen = mdl.generate(**enc, max_new_tokens=max_new, num_beams=num_beams)
            decoded = tok.batch_decode(gen, skip_special_tokens=True)
            outs.extend(decoded)
    return outs


if __name__ == "__main__":
    # quick smoke test (only when running directly)
    print(translate_batch(["Hello world", "This is a test."]))
