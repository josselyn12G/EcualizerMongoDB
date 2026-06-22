"""
Servicio de Spotify para las secciones del oyente.

Mejoras de rendimiento:
  - Las llamadas a múltiples artistas se hacen EN PARALELO con ThreadPoolExecutor.
    Antes: 5 llamadas secuenciales ≈ 1.5 s.  Ahora: todas a la vez ≈ 300 ms.
  - El caché persiste en disco (FileBasedCache), así que la primera visita
    después de un reinicio del servidor sigue siendo rápida.
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from django.core.cache import cache

_token_cache = {'token': None, 'expires': 0}


def _ttl():
    return getattr(settings, 'SPOTIFY_CACHE_TTL', 60 * 60 * 6)


def _cached(key, producer):
    """Devuelve el valor cacheado; si no existe llama a producer() y lo guarda."""
    data = cache.get(key)
    if data is not None:
        return data
    data = producer()
    if data:
        cache.set(key, data, _ttl())
    return data


def get_token():
    if _token_cache['token'] and time.time() < _token_cache['expires']:
        return _token_cache['token']
    resp = requests.post(
        'https://accounts.spotify.com/api/token',
        data={'grant_type': 'client_credentials'},
        auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET),
        timeout=10,
    )
    data = resp.json()
    _token_cache['token'] = data['access_token']
    _token_cache['expires'] = time.time() + data['expires_in'] - 30
    return _token_cache['token']


def _headers():
    return {'Authorization': f'Bearer {get_token()}'}


def _top_tracks_artist(artist_id: str, n: int = 4) -> list:
    """Descarga las top-tracks de un artista (usada en hilos paralelos)."""
    try:
        resp = requests.get(
            f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks',
            headers=_headers(),
            params={'market': 'US'},
            timeout=8,
        )
        return resp.json().get('tracks', [])[:n]
    except Exception:
        return []


def _fetch_parallel(artist_ids: list[str], limit: int, tracks_per_artist: int = 4) -> list:
    """Descarga top-tracks de varios artistas EN PARALELO y devuelve hasta `limit`."""
    results: dict[str, list] = {}
    with ThreadPoolExecutor(max_workers=min(len(artist_ids), 6)) as pool:
        futures = {pool.submit(_top_tracks_artist, aid, tracks_per_artist): aid
                   for aid in artist_ids}
        for fut in as_completed(futures):
            artist_id = futures[fut]
            try:
                results[artist_id] = fut.result()
            except Exception:
                results[artist_id] = []

    # Reconstruye en el mismo orden que la lista original
    tracks = []
    for aid in artist_ids:
        tracks.extend(results.get(aid, []))
        if len(tracks) >= limit:
            break
    return tracks[:limit]


# ── Artistas por sección ──────────────────────────────────────────────

ARTISTAS_TENDENCIAS = [
    '3TVXtAsR1Inumwj472S9r4',  # Drake
    '1uNFoZAHBGtllmzznpCI3s',  # Justin Bieber
    '06HL4z0CvFAxyc27GXpf02',  # Taylor Swift
    '4q3ewBCX7sLwd24euuV69X',  # Bad Bunny
    '1McMsnEElThX1knmY4oliG',  # Ozuna
]

ARTISTAS_PARA_TI = [
    '4q3ewBCX7sLwd24euuV69X',  # Bad Bunny
    '790FomKkXshlbRYZFtlgla',  # Karol G
    '1McMsnEElThX1knmY4oliG',  # Ozuna
    '2ymNvselectSOnREhJFJ7oV',  # Maluma
    '6l3HvQ5sa6mXTsMTB6T5D',   # J Balvin
]


# ── API pública ───────────────────────────────────────────────────────

def get_tendencias(limit=20):
    return _cached(f'spotify:tendencias:{limit}',
                   lambda: _fetch_parallel(ARTISTAS_TENDENCIAS, limit))


def get_para_ti(limit=20):
    return _cached(f'spotify:para_ti:{limit}',
                   lambda: _fetch_parallel(ARTISTAS_PARA_TI, limit))


def get_novedades(limit=10):
    return _cached(f'spotify:novedades:{limit}', lambda: _fetch_novedades(limit))


def _fetch_novedades(limit=10):
    try:
        resp = requests.get(
            'https://api.spotify.com/v1/browse/new-releases',
            headers=_headers(),
            params={'limit': limit, 'country': 'EC'},
            timeout=8,
        )
        return resp.json().get('albums', {}).get('items', [])
    except Exception:
        return []


def get_explorar(limit=12):
    return _cached(f'spotify:explorar:{limit}', lambda: _fetch_explorar(limit))


def _fetch_explorar(limit=12):
    try:
        resp = requests.get(
            'https://api.spotify.com/v1/browse/categories',
            headers=_headers(),
            params={'limit': limit, 'country': 'EC', 'locale': 'es_EC'},
            timeout=8,
        )
        return resp.json().get('categories', {}).get('items', [])
    except Exception:
        return []
