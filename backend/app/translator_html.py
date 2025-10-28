from bs4 import BeautifulSoup, NavigableString
from .nlp import translate_batch
from .cache import translate_with_cache

_SKIP_PARENTS = {"script", "style", "noscript", "code", "pre", "kbd", "template"}


def translate_html(html: str) -> str:
    """Translate visible text nodes in an HTML document.

    - Skips blacklisted parent tags (script/style/pre/etc.).
    - Collects contiguous text nodes and translates them in batches via
      translate_with_cache + translate_batch.
    """
    soup = BeautifulSoup(html, "html.parser")
    texts = []
    nodes = []

    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString):
            continue
        s = (node or "").strip()
        if not s:
            continue
        parent = node.parent.name.lower() if node.parent and node.parent.name else ""
        if parent in _SKIP_PARENTS:
            continue
        # simple heuristic: skip nodes that look like URLs or short tokens like punctuation
        texts.append(s)
        nodes.append(node)

    if not texts:
        return str(soup)

    # Use sentence-level cache to avoid re-translating repeated fragments
    zh = translate_with_cache(texts, translate_batch)

    # replace nodes in-place
    for node, t in zip(nodes, zh):
        try:
            node.replace_with(t)
        except Exception:
            # best-effort: if replacement fails, leave original
            pass

    return str(soup)


if __name__ == "__main__":
    sample = "<html><body><h1>Hello world</h1><p>This is a test.</p></body></html>"
    print(translate_html(sample))
