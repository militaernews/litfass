"""Resolve a public Telegram channel post to a playable media URL.

Telegram's public post page exposes the media in og:video (videos) or og:image
(animated GIFs). The browser cannot read t.me because of CORS, so this runs on
the server and caches the result for a few minutes.
"""

from __future__ import annotations

import html
import re
import time
from urllib.request import Request, urlopen

from aiohttp import web

CACHE_SECONDS = 300
_cache: dict[str, tuple[float, tuple[str, str] | None]] = {}
POST = re.compile(r"^https://t\.me/(?:s/)?[A-Za-z0-9_]{4,}/[0-9]+/?$")
OG_VIDEO = re.compile(r'<meta[^>]+property="og:video"[^>]+content="([^"]+)"')
OG_IMAGE = re.compile(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"')


def resolve(post_url: str) -> tuple[str, str] | None:
    """(media URL, 'video' | 'gif') or None for a link without playable media."""
    if not POST.match(post_url):
        return None
    cached = _cache.get(post_url)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]
    result: tuple[str, str] | None = None
    try:
        request = Request(post_url, headers={"User-Agent": "Mozilla/5.0"})
        page = urlopen(request, timeout=10).read().decode("utf-8", "replace")
        video = OG_VIDEO.search(page)
        image = OG_IMAGE.search(page)
        if video:
            result = (html.unescape(video.group(1)), "video")
        elif image:
            result = (html.unescape(image.group(1)), "gif")
    except Exception:
        result = None
    _cache[post_url] = (time.time(), result)
    return result


async def serve(request: web.Request) -> web.Response:
    """GET /v1/video?url=<telegram post> — CORS open, like the feed."""
    url = request.query.get("url", "")
    found = resolve(url)
    if not found:
        return web.json_response({"error": "no media found"}, status=404, headers={"Access-Control-Allow-Origin": "*"})
    return web.json_response(
        {"url": found[0], "kind": found[1]},
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=300"},
    )
