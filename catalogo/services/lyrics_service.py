"""
Servicio de letras — usa la API pública gratuita api.lyrics.ovh.

Endpoint: GET https://api.lyrics.ovh/v1/{artist}/{title}
Respuesta: { "lyrics": "..." }   (o { "error": "..." } si no hay match)

Sin claves; sin dependencias externas (urllib). Cache en memoria por TTL.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
import urllib.error


_TTL_SECONDS = 60 * 60 * 24      # 24 h
_cache: dict[tuple[str, str], tuple[str | None, float]] = {}
_lock = threading.Lock()


def _cache_get(key):
    with _lock:
        entry = _cache.get(key)
        if not entry:
            return None
        value, exp = entry
        if time.time() > exp:
            _cache.pop(key, None)
            return None
        return value


def _cache_put(key, value):
    with _lock:
        _cache[key] = (value, time.time() + _TTL_SECONDS)


def obtener_letra(artista: str, cancion: str) -> str | None:
    """
    Devuelve la letra de la canción para (artista, canción) o None si no hay.

    Captura cualquier fallo de red/timeout y devuelve None para que el
    template muestre el fallback ("Letra no disponible").
    """
    if not artista or not cancion:
        return None

    key = (artista.lower().strip(), cancion.lower().strip())
    cached = _cache_get(key)
    if cached is not None:
        # Cacheamos también los misses ('') para no martillar la API
        return cached or None

    artist_enc = urllib.parse.quote(artista.strip(), safe='')
    title_enc = urllib.parse.quote(cancion.strip(), safe='')
    url = f'https://api.lyrics.ovh/v1/{artist_enc}/{title_enc}'

    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, ValueError):
        _cache_put(key, '')
        return None

    letra = (payload.get('lyrics') or '').strip()
    _cache_put(key, letra)
    return letra or None
