"""
Servicio MongoDB para la app `biblioteca`.

Colecciones:
  - Playlist  : playlistId, nombrePlaylist, fechaCreacion, tipoVisibilidad,
                tipoPlaylist, canciones[], colaboradores[]
  - Likes     : likeId, usuarioId, cancionId, fechaLike
  - Cancion   : (join para enriquecer canciones de la playlist / liked)
  - Albums    : (join para tituloAlbum / nombreArtistico)

Las funciones devuelven dicts con las MISMAS claves que usaban los SP /
SQL anteriores (idPlaylist, TotalCanciones, idCancion, …) para no tocar HTML.
"""

from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from usuarios.mongo_service import get_database


def _col(nombre):
    return get_database()[nombre]


def _oid(valor):
    v = str(valor) if valor is not None else ''
    return ObjectId(v) if ObjectId.is_valid(v) else None


def _playlist_id(doc):
    return doc.get('playlistId') or doc['_id']


def _fmt_fecha(value):
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')
    if isinstance(value, str):
        return value[:10]
    return None


# ══════════════════════════════════════════════════════════════════════
# PLAYLIST · CRUD
# ══════════════════════════════════════════════════════════════════════

def listar_playlists(usuario_id, visibilidad=None):
    """Playlists en las que el usuario participa (como Creador o Colaborador)."""
    oid = _oid(usuario_id)
    if not oid:
        return []
    filtro = {'colaboradores.userId': oid}
    if visibilidad:
        filtro['tipoVisibilidad'] = visibilidad
    cursor = _col('Playlist').find(filtro).sort('fechaCreacion', -1)
    salida = []
    for pl in cursor:
        salida.append({
            'idPlaylist': str(_playlist_id(pl)),
            'nombrePlaylist': pl.get('nombrePlaylist'),
            'descripcionPlaylist': pl.get('descripcionPlaylist'),
            'tipoVisibilidad': pl.get('tipoVisibilidad'),
            'tipoPlaylist': pl.get('tipoPlaylist'),
            'TotalCanciones': len(pl.get('canciones') or []),
        })
    return salida


def crear_playlist(usuario_id, nombre, descripcion, visibilidad='Privada', tipo='Personal'):
    oid = _oid(usuario_id)
    if not oid:
        return None
    doc = {
        'playlistId': ObjectId(),
        'nombrePlaylist': (nombre or '').strip(),
        'descripcionPlaylist': (descripcion or '').strip() or None,
        'fechaCreacion': datetime.now(timezone.utc),
        'tipoVisibilidad': visibilidad if visibilidad in ('Publica', 'Privada') else 'Privada',
        'tipoPlaylist': tipo if tipo in ('Personal', 'Colaborativa') else 'Personal',
        'duracionTotal': 0,
        'canciones': [],
        'colaboradores': [{
            'userId': oid,
            'fechaUnion': datetime.now(timezone.utc).isoformat(),
            'rolPlaylist': 'Creador',
        }],
    }
    _col('Playlist').insert_one(doc)
    return str(doc['playlistId'])


def _find_playlist(pk):
    oid = _oid(pk)
    if not oid:
        return None
    return _col('Playlist').find_one({'$or': [{'playlistId': oid}, {'_id': oid}]})


def _es_creador(pl_doc, usuario_id):
    oid = _oid(usuario_id)
    for c in (pl_doc.get('colaboradores') or []):
        if c.get('userId') == oid and c.get('rolPlaylist') == 'Creador':
            return True
    return False


def get_playlist_info(playlist_id, usuario_id):
    """Dict con info de la playlist (igual que el SP antiguo)."""
    pl = _find_playlist(playlist_id)
    if not pl:
        return None
    oid = _oid(usuario_id)
    participantes = [c.get('userId') for c in (pl.get('colaboradores') or [])]
    if oid not in participantes:
        return None
    return {
        'idPlaylist': str(_playlist_id(pl)),
        'nombrePlaylist': pl.get('nombrePlaylist'),
        'descripcionPlaylist': pl.get('descripcionPlaylist'),
        'tipoVisibilidad': pl.get('tipoVisibilidad'),
        'tipoPlaylist': pl.get('tipoPlaylist'),
    }


def actualizar_playlist(playlist_id, usuario_id, nombre, descripcion, visibilidad):
    pl = _find_playlist(playlist_id)
    if not pl or not _es_creador(pl, usuario_id):
        return False
    _col('Playlist').update_one({'_id': pl['_id']}, {'$set': {
        'nombrePlaylist': (nombre or '').strip(),
        'descripcionPlaylist': (descripcion or '').strip() or None,
        'tipoVisibilidad': visibilidad if visibilidad in ('Publica', 'Privada') else 'Privada',
    }})
    return True


def eliminar_playlist(playlist_id, usuario_id):
    pl = _find_playlist(playlist_id)
    if not pl or not _es_creador(pl, usuario_id):
        return False
    _col('Playlist').delete_one({'_id': pl['_id']})
    return True


# ══════════════════════════════════════════════════════════════════════
# PLAYLIST · Canciones embebidas
# ══════════════════════════════════════════════════════════════════════

def get_canciones_playlist(playlist_id):
    """Lista enriquecida de canciones de una playlist."""
    pl = _find_playlist(playlist_id)
    if not pl:
        return []
    canciones_emb = pl.get('canciones') or []
    if not canciones_emb:
        return []

    ids = [_oid(c.get('cancionId')) for c in canciones_emb if c.get('cancionId')]
    ids = [i for i in ids if i]
    cancion_docs = {
        str(d.get('cancionId') or d['_id']): d
        for d in _col('Cancion').find({'$or': [
            {'cancionId': {'$in': ids}}, {'_id': {'$in': ids}},
        ]})
    }
    album_ids = list({_oid(d.get('albumId')) for d in cancion_docs.values() if d.get('albumId')})
    album_docs = {
        str(a.get('albumId') or a['_id']): a
        for a in _col('Albums').find({'albumId': {'$in': album_ids}})
    }

    salida = []
    for i, emb in enumerate(canciones_emb):
        cid_str = str(_oid(emb.get('cancionId'))) if emb.get('cancionId') else None
        c = cancion_docs.get(cid_str) or {}
        aid_str = str(c.get('albumId')) if c.get('albumId') else None
        a = album_docs.get(aid_str) or {}
        salida.append({
            'idCancion': cid_str or '',
            'nombreCancion': c.get('tituloCancion') or emb.get('nombreCancion', ''),
            'duracion': c.get('duracion'),
            'totalReproducciones': c.get('totalReproducciones', 0),
            'tituloAlbum': a.get('tituloAlbum'),
            'nombreArtistico': (c.get('artistas') or [{}])[0].get('nombreArtistico'),
            'posicionPlaylist': i + 1,
            'fechaAgregada': _fmt_fecha(emb.get('fechaAgregada')),
        })
    return salida


def agregar_cancion_playlist(playlist_id, usuario_id, cancion_id):
    pl = _find_playlist(playlist_id)
    if not pl or not _es_creador(pl, usuario_id):
        return False
    coid = _oid(cancion_id)
    if not coid:
        return False
    canciones = pl.get('canciones') or []
    ya_existe = any(_oid(c.get('cancionId')) == coid for c in canciones)
    if ya_existe:
        return False
    cancion_doc = _col('Cancion').find_one(
        {'$or': [{'cancionId': coid}, {'_id': coid}]},
        {'tituloCancion': 1, 'duracion': 1},
    )
    nombre = (cancion_doc or {}).get('tituloCancion', '')
    duracion = (cancion_doc or {}).get('duracion', 0)
    emb = {
        'cancionId': coid,
        'nombreCancion': nombre,
        'fechaAgregada': datetime.now(timezone.utc),
    }
    _col('Playlist').update_one({'_id': pl['_id']}, {
        '$push': {'canciones': emb},
        '$inc': {'duracionTotal': duracion},
    })
    return True


def quitar_cancion_playlist(playlist_id, usuario_id, cancion_id):
    pl = _find_playlist(playlist_id)
    if not pl or not _es_creador(pl, usuario_id):
        return False
    coid = _oid(cancion_id)
    if not coid:
        return False
    cancion_doc = _col('Cancion').find_one(
        {'$or': [{'cancionId': coid}, {'_id': coid}]},
        {'duracion': 1},
    )
    duracion = (cancion_doc or {}).get('duracion', 0)
    _col('Playlist').update_one({'_id': pl['_id']}, {
        '$pull': {'canciones': {'cancionId': coid}},
        '$inc': {'duracionTotal': -duracion},
    })
    return True


# ══════════════════════════════════════════════════════════════════════
# LIKES
# ══════════════════════════════════════════════════════════════════════

def is_cancion_liked(usuario_id, cancion_id):
    uoid = _oid(usuario_id)
    coid = _oid(cancion_id)
    if not uoid or not coid:
        return False
    return _col('Likes').count_documents(
        {'usuarioId': uoid, 'cancionId': coid}, limit=1
    ) > 0


def toggle_like_cancion(usuario_id, cancion_id):
    """
    Alterna el like. Devuelve True si quedó ACTIVO (liked), False si quitado.
    """
    uoid = _oid(usuario_id)
    coid = _oid(cancion_id)
    if not uoid or not coid:
        return False
    if is_cancion_liked(usuario_id, cancion_id):
        _col('Likes').delete_one({'usuarioId': uoid, 'cancionId': coid})
        return False
    try:
        _col('Likes').insert_one({
            'likeId': ObjectId(),
            'usuarioId': uoid,
            'cancionId': coid,
            'fechaLike': datetime.now(timezone.utc),
        })
        return True
    except DuplicateKeyError:
        return True


def get_canciones_liked_ids(usuario_id):
    """Set de IDs de canciones (str) que el usuario tiene likeadas."""
    oid = _oid(usuario_id)
    if not oid:
        return set()
    cursor = _col('Likes').find({'usuarioId': oid}, {'cancionId': 1})
    return {str(d['cancionId']) for d in cursor if d.get('cancionId')}


def get_canciones_liked(usuario_id):
    """Lista enriquecida de canciones likeadas (mismas claves que el SP)."""
    oid = _oid(usuario_id)
    if not oid:
        return []
    pipeline = [
        {'$match': {'usuarioId': oid}},
        {'$sort': {'fechaLike': -1}},
        {'$lookup': {
            'from': 'Cancion',
            'localField': 'cancionId',
            'foreignField': 'cancionId',
            'as': '_c',
        }},
        {'$set': {'_c': {'$arrayElemAt': ['$_c', 0]}}},
        {'$lookup': {
            'from': 'Albums',
            'localField': '_c.albumId',
            'foreignField': 'albumId',
            'as': '_a',
        }},
        {'$set': {'_a': {'$arrayElemAt': ['$_a', 0]}}},
        {'$match': {'_c.estadoCancion': 'activa'}},
        {'$project': {
            '_id': 0,
            'idCancion': {'$toString': {'$ifNull': ['$_c.cancionId', '$_c._id']}},
            'nombreCancion': '$_c.tituloCancion',
            'duracion': '$_c.duracion',
            'calidadKbps': '$_c.calidadKbps',
            'totalReproducciones': {'$ifNull': ['$_c.totalReproducciones', 0]},
            'idAlbum': {'$toString': '$_c.albumId'},
            'tituloAlbum': '$_a.tituloAlbum',
            'nombreArtistico': {'$arrayElemAt': ['$_c.artistas.nombreArtistico', 0]},
            'fechaLike': 1,
        }},
    ]
    return list(_col('Likes').aggregate(pipeline))
