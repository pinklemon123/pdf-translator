from diskcache import Cache

_cache = Cache(".cache_trans")


def get(key: str):
    return _cache.get(key)


def set_(key: str, val, expire=60 * 60 * 24 * 7):
    _cache.set(key, val, expire=expire)


def translate_with_cache(texts, translate_fn):
    """Translate a list of texts using translate_fn, with sentence-level caching.

    translate_fn: callable(list[str]) -> list[str]
    """
    res = []
    missing, idx = [], []
    for i, t in enumerate(texts):
        v = get(t)
        if v is None:
            idx.append(i)
            missing.append(t)
        else:
            res.append((i, v))
    if missing:
        got = translate_fn(missing)
        for i, t, tr in zip(idx, missing, got):
            set_(t, tr)
            res.append((i, tr))
    # sort results back to original order
    return [v for _, v in sorted(res, key=lambda x: x[0])]
