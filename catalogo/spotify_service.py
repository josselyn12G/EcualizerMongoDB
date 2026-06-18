import requests
from django.conf import settings
from django.core.cache import cache

_token_cache = {'token': None, 'expires': 0}


def _ttl():
    """TTL de caché (segundos) para las secciones del oyente."""
    return getattr(settings, 'SPOTIFY_CACHE_TTL', 60 * 60)


def _cached(key, producer):
    """Devuelve el valor cacheado de `key`; si no existe, ejecuta
    `producer()`, cachea el resultado (solo si no está vacío) y lo
    devuelve. Así la primera carga consulta Spotify y las siguientes
    son instantáneas hasta que expire el TTL."""
    data = cache.get(key)
    if data is not None:
        return data
    data = producer()
    if data:                       # no cacheamos respuestas vacías/errores
        cache.set(key, data, _ttl())
    return data


def get_token():
    import time
    if _token_cache['token'] and time.time() < _token_cache['expires']:
        return _token_cache['token']

    resp = requests.post(
        'https://accounts.spotify.com/api/token',
        data={'grant_type': 'client_credentials'},
        auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET),
    )
    data = resp.json()
    _token_cache['token'] = data['access_token']
    _token_cache['expires'] = time.time() + data['expires_in'] - 30
    return _token_cache['token']


def _headers():
    return {'Authorization': f'Bearer {get_token()}'}


# IDs de artistas populares para tendencias globales
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


def get_tendencias(limit=20):
    """Top tracks de artistas globales (cacheado)."""
    return _cached(f'spotify:tendencias:{limit}', lambda: _fetch_tendencias(limit))


def _fetch_tendencias(limit=20):
    tracks = []
    try:
        for artist_id in ARTISTAS_TENDENCIAS:
            resp = requests.get(
                f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks',
                headers=_headers(),
                params={'market': 'US'}
            )
            artist_tracks = resp.json().get('tracks', [])[:4]
            tracks.extend(artist_tracks)
            if len(tracks) >= limit:
                break
        return tracks[:limit]
    except Exception as e:
        print(f"Spotify error tendencias: {e}")
        return []


def get_novedades(limit=10):
    """Álbumes nuevos (cacheado)."""
    return _cached(f'spotify:novedades:{limit}', lambda: _fetch_novedades(limit))


def _fetch_novedades(limit=10):
    try:
        resp = requests.get(
            'https://api.spotify.com/v1/browse/new-releases',
            headers=_headers(),
            params={'limit': limit, 'country': 'EC'}
        )
        return resp.json().get('albums', {}).get('items', [])
    except Exception:
        return []


def get_para_ti(limit=20):
    """Top tracks de artistas latinos (cacheado)."""
    return _cached(f'spotify:para_ti:{limit}', lambda: _fetch_para_ti(limit))


def _fetch_para_ti(limit=20):
    tracks = []
    try:
        for artist_id in ARTISTAS_PARA_TI:
            resp = requests.get(
                f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks',
                headers=_headers(),
                params={'market': 'US'}
            )
            artist_tracks = resp.json().get('tracks', [])[:4]
            tracks.extend(artist_tracks)
            if len(tracks) >= limit:
                break
        return tracks[:limit]
    except Exception as e:
        print(f"Spotify error para_ti: {e}")
        return []


def get_explorar(limit=12):
    """Categorías disponibles (cacheado)."""
    return _cached(f'spotify:explorar:{limit}', lambda: _fetch_explorar(limit))


def _fetch_explorar(limit=12):
    try:
        resp = requests.get(
            'https://api.spotify.com/v1/browse/categories',
            headers=_headers(),
            params={'limit': limit, 'country': 'EC', 'locale': 'es_EC'}
        )
        return resp.json().get('categories', {}).get('items', [])
    except Exception:
        return []