"""
Servicio Deezer — solo trae IMÁGENES (artista / álbum / canción).

Deezer no exige autenticación para búsquedas públicas (es REST simple
y sin OAuth), así que no hay credenciales que configurar.

Endpoints usados:
  - GET https://api.deezer.com/search/artist?q={name}&limit=1
  - GET https://api.deezer.com/search/album?q={album} artist:{artist}&limit=1
  - GET https://api.deezer.com/search/track?q={title} artist:{artist}&limit=1

Cache en memoria (TTL configurable) para no martillar la API.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
import urllib.error


# ───────────────────────────────────────────────────────────
# Defaults — placeholders cuando Deezer no encuentra match
# ───────────────────────────────────────────────────────────
DEFAULT_ARTIST_IMAGE = 'https://placehold.co/500x500/1a1a1a/f97316?text=Artista'
DEFAULT_ALBUM_IMAGE  = 'https://placehold.co/500x500/1a1a1a/f97316?text=Album'
DEFAULT_TRACK_IMAGE  = 'https://placehold.co/500x500/1a1a1a/f97316?text=Cancion'

_CACHE_TTL_SECONDS = 60 * 60 * 24   # 24 h

# ───────────────────────────────────────────────────────────
# Cache compartido (thread-safe)
# ───────────────────────────────────────────────────────────
_cache: dict[tuple, tuple[str, float]] = {}
_cache_lock = threading.Lock()


def _cache_get(key: tuple) -> str | None:
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        url, exp = entry
        if time.time() > exp:
            _cache.pop(key, None)
            return None
        return url


def _cache_put(key: tuple, url: str) -> None:
    with _cache_lock:
        _cache[key] = (url, time.time() + _CACHE_TTL_SECONDS)


# ───────────────────────────────────────────────────────────
# Llamada genérica al endpoint /search/{type}
# ───────────────────────────────────────────────────────────
def _deezer_search(kind: str, query: str) -> dict | None:
    """
    kind:  '' → /search general (recomendado para tracks)
           'artist' | 'album' | 'track' → /search/<kind>
    Devuelve el primer item o None.
    """
    if not query:
        return None
    path = f'search/{kind}' if kind else 'search'
    url = f'https://api.deezer.com/{path}?q={urllib.parse.quote(query)}&limit=1'
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, ValueError):
        return None
    data = (payload or {}).get('data') or []
    return data[0] if data else None


# ───────────────────────────────────────────────────────────
# API pública
# ───────────────────────────────────────────────────────────
def deezer_get_artist_image(artist_name: str) -> str:
    """Foto del artista (tamaño grande). Default si no hay match."""
    if not artist_name:
        return DEFAULT_ARTIST_IMAGE

    key = ('artist', artist_name.lower().strip())
    cached = _cache_get(key)
    if cached:
        return cached

    item = _deezer_search('artist', artist_name)
    url = (
        (item or {}).get('picture_big')
        or (item or {}).get('picture_medium')
        or (item or {}).get('picture_xl')
        or DEFAULT_ARTIST_IMAGE
    )
    _cache_put(key, url)
    return url


def deezer_get_album_image(album_name: str,
                           artist_name: str | None = None) -> str:
    """
    Portada del álbum. Estrategia:
      1. /search/album con album:"X" artist:"Y" → cover_xl/big.
      2. Si no hay match → busca por track (cualquier track del álbum),
         que da `track.album.cover_*` muy confiable.
      3. Foto del artista (peor caso).
      4. Placeholder.
    """
    if not album_name:
        return DEFAULT_ALBUM_IMAGE

    key = ('album', album_name.lower().strip(),
           (artist_name or '').lower().strip())
    cached = _cache_get(key)
    if cached:
        return cached

    # 1. Búsqueda estricta de álbum
    parts = [f'album:"{album_name}"']
    if artist_name:
        parts.append(f'artist:"{artist_name}"')
    item = _deezer_search('album', ' '.join(parts))
    url = (
        (item or {}).get('cover_xl')
        or (item or {}).get('cover_big')
        or (item or {}).get('cover_medium')
        or (item or {}).get('cover')
    )

    # 2. Fallback: usar el álbum del primer track encontrado
    if not url:
        track_parts = []
        if artist_name:
            track_parts.append(f'artist:"{artist_name}"')
        track_parts.append(f'album:"{album_name}"')
        track = _deezer_search('', ' '.join(track_parts))
        ab = (track or {}).get('album') or {}
        url = (
            ab.get('cover_xl') or ab.get('cover_big')
            or ab.get('cover_medium') or ab.get('cover')
        )

    # 3. Foto del artista como último recurso
    if not url and artist_name:
        url = deezer_get_artist_image(artist_name)
    if not url:
        url = DEFAULT_ALBUM_IMAGE

    _cache_put(key, url)
    return url


def deezer_get_track_preview(track_name: str,
                             artist_name: str | None = None) -> str | None:
    """
    URL del preview MP3 (~30s) de Deezer para esa canción.
    Devuelve None si no hay match o no hay preview disponible.

    Usa la sintaxis estricta de Deezer:
        q=artist:"<artista>" track:"<cancion>"
    para evitar que devuelva una canción distinta del mismo artista.
    """
    if not track_name:
        return None

    key = ('preview', track_name.lower().strip(),
           (artist_name or '').lower().strip())
    cached = _cache_get(key)
    if cached is not None:
        return cached or None      # '' = miss cacheado

    item = _deezer_search_track_strict(track_name, artist_name)
    preview = (item or {}).get('preview') or ''
    _cache_put(key, preview)
    return preview or None


def _deezer_search_track_strict(track_name: str,
                                artist_name: str | None) -> dict | None:
    """
    Búsqueda de track con operadores estrictos contra `/search` (universal).
    Si no hay match con artist+track, intenta solo con track (degradado).
    NUNCA caemos a "primer track del artista" para evitar resultados confusos.

    Endpoint: https://api.deezer.com/search?q=artist:"X" track:"Y"
    """
    parts = []
    if artist_name:
        parts.append(f'artist:"{artist_name}"')
    parts.append(f'track:"{track_name}"')
    # Usamos /search (general) en lugar de /search/track porque los operadores
    # `artist:"X" track:"Y"` se aplican igual y el endpoint general es más
    # tolerante a tipografía/acentos.
    item = _deezer_search('', ' '.join(parts))
    if item:
        return item
    return _deezer_search('', f'track:"{track_name}"')


def deezer_get_track_image(track_name: str,
                           artist_name: str | None = None,
                           album_name: str | None = None) -> str:
    """
    Imagen para una canción. Deezer no tiene cover propio por track:
    usa el cover del álbum al que pertenece. Si no encontramos el track
    exacto (artist + track), caemos al álbum, después al artista, y por
    último al placeholder.
    """
    if not track_name:
        return DEFAULT_TRACK_IMAGE

    key = ('track', track_name.lower().strip(),
           (artist_name or '').lower().strip())
    cached = _cache_get(key)
    if cached:
        return cached

    # Misma búsqueda estricta que para el preview: artist:"X" track:"Y".
    # IMPORTANTE: usamos `track.album.cover_*`, NUNCA `track.artist.picture`,
    # porque la portada que queremos es la del álbum al que pertenece la canción.
    item = _deezer_search_track_strict(track_name, artist_name)
    album_block = (item or {}).get('album') or {}
    url = (
        album_block.get('cover_xl')
        or album_block.get('cover_big')
        or album_block.get('cover_medium')
        or album_block.get('cover')
    )
    if not url and album_name:
        url = deezer_get_album_image(album_name, artist_name)
    if not url and artist_name:
        url = deezer_get_artist_image(artist_name)
    if not url:
        url = DEFAULT_TRACK_IMAGE

    _cache_put(key, url)
    return url


# ───────────────────────────────────────────────────────────
# Helpers para enriquecer listas que vienen de SPs
# ───────────────────────────────────────────────────────────
def deezer_enrich_canciones(canciones: list[dict],
                             with_preview: bool = False) -> list[dict]:
    """Añade `coverUrl` a cada dict-canción (filas SP_ListarCanciones).

    Si `with_preview=True` también agrega `previewUrl` (MP3 ~30s de Deezer).
    Lo dejamos opt-in porque el preview duplica las llamadas a la API.
    """
    for c in canciones or []:
        if not isinstance(c, dict):
            continue
        c['coverUrl'] = deezer_get_track_image(
            c.get('nombreCancion') or '',
            c.get('nombreArtistico') or '',
            c.get('tituloAlbum') or '',
        )
        if with_preview:
            c['previewUrl'] = deezer_get_track_preview(
                c.get('nombreCancion') or '',
                c.get('nombreArtistico') or '',
            ) or ''
    return canciones


def deezer_enrich_albumes(albumes: list[dict]) -> list[dict]:
    """Añade `coverUrl` a cada dict-álbum (filas SP_ListarAlbumes)."""
    for a in albumes or []:
        if not isinstance(a, dict):
            continue
        a['coverUrl'] = deezer_get_album_image(
            a.get('tituloAlbum') or '',
            a.get('nombreArtistico') or '',
        )
    return albumes
