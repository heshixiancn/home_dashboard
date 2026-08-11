from app.cache import TTLCache


def test_cache_invalidate_prefix():
    cache = TTLCache(30)
    cache.set("dashboard", {"ok": True})
    cache.set("devices", [])
    cache.invalidate("dash")
    assert cache.get("dashboard") is None
    assert cache.get("devices") == []

