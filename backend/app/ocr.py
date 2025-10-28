import threading
import easyocr

_reader = None
_lock = threading.Lock()


def get_ocr(lang_list=None, gpu=False):
    """Return a singleton easyocr Reader.

    lang_list: list of language codes, default ['en']
    gpu: whether to use GPU (default False)
    """
    global _reader
    if lang_list is None:
        lang_list = ["en"]
    if _reader is None:
        with _lock:
            if _reader is None:
                # easyocr Reader will download model files on first use
                _reader = easyocr.Reader(lang_list, gpu=gpu)
    return _reader
