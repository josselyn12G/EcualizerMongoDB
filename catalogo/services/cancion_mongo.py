"""
Servicio de CANCIONES y REPRODUCCION sobre MongoDB.

Colecciones:
  - Cancion      : tituloCancion, duracion, fechaLanzamiento, estadoCancion,
                   calidadKbps, totalReproducciones, letraCancion, albumId,
                   numeroPista, generos[], artistas[]
  - Albums       : (join para tituloAlbum / nombreArtistico)
  - Reproduccion : append-only; cada doc = un evento de escucha

Las funciones de LIST devuelven dicts con las MISMAS claves que esperaban
los Stored Procedures (idCancion, nombreCancion, …) para no tocar plantillas.
"""

import re
from datetime import datetime, time, timezone

from bson import ObjectId
from types import SimpleNamespace

from usuarios.mongo_service import get_database


def _col(nombre):
    return get_database()[nombre]


def _oid(valor):
    v = str(valor) if valor is not None else ''
    return ObjectId(v) if ObjectId.is_valid(v) else None


def _to_dt(value):
    if isinstance(value, datetime):
        return value
    if hasattr(value, 'year') and not isinstance(value, str):
        return datetime.combine(value, time.min)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value[:19])
        except ValueError:
            try:
                return datetime.combine(
                    datetime.strptime(value[:10], '%Y-%m-%d').date(), time.min
                )
            except ValueError:
                return None
    return None


def _cancion_id(doc):
    return doc.get('cancionId') or doc['_id']


# ══════════════════════════════════════════════════════════════════════
# LISTAR  (compatible con plantillas)
# ══════════════════════════════════════════════════════════════════════
def listar_canciones(artista_id=None, album_id=None, estado=None, busqueda=None):
    """Devuelve list[dict] con las mismas claves que SP_ListarCanciones."""
    match = {}
    if estado:
        match['estadoCancion'] = estado
    if album_id:
        match['albumId'] = _oid(album_id)
    if artista_id:
        match['artistas.artistaId'] = _oid(artista_id)
    if busqueda:
        match['tituloCancion'] = {'$regex': re.escape(busqueda), '$options': 'i'}

    pipeline = [
        {'$match': match},
        {'$lookup': {
            'from': 'Albums',
            'localField': 'albumId',
            'foreignField': 'albumId',
            'as': '_album',
        }},
        {'$set': {'_album': {'$arrayElemAt': ['$_album', 0]}}},
        {'$sort': {'_album.tituloAlbum': 1, 'numeroPista': 1}},
        {'$project': {
            '_id': 0,
            'idCancion': {'$toString': {'$ifNull': ['$cancionId', '$_id']}},
            'nombreCancion': '$tituloCancion',
            'duracion': 1,
            'calidadKbps': 1,
            'totalReproducciones': {'$ifNull': ['$totalReproducciones', 0]},
            'estadoCancion': 1,
            'letraCancion': 1,
            'numeroPista': 1,
            'tituloAlbum': '$_album.tituloAlbum',
            'nombreArtistico': {'$arrayElemAt': ['$artistas.nombreArtistico', 0]},
            'idAlbum': {'$toString': '$albumId'},
        }},
    ]
    return list(_col('Cancion').aggregate(pipeline))


def filtrar_canciones_genero(nombre_genero):
    """Canciones activas de un género (géneros embebidos, no ID entero)."""
    pipeline = [
        {'$match': {
            'estadoCancion': 'activa',
            'generos.nombreGenero': nombre_genero,
        }},
        {'$lookup': {
            'from': 'Albums',
            'localField': 'albumId',
            'foreignField': 'albumId',
            'as': '_album',
        }},
        {'$set': {'_album': {'$arrayElemAt': ['$_album', 0]}}},
        {'$sort': {'totalReproducciones': -1}},
        {'$project': {
            '_id': 0,
            'idCancion': {'$toString': {'$ifNull': ['$cancionId', '$_id']}},
            'nombreCancion': '$tituloCancion',
            'duracion': 1,
            'calidadKbps': 1,
            'totalReproducciones': {'$ifNull': ['$totalReproducciones', 0]},
            'estadoCancion': 1,
            'tituloAlbum': '$_album.tituloAlbum',
            'nombreArtistico': {'$arrayElemAt': ['$artistas.nombreArtistico', 0]},
            'idAlbum': {'$toString': '$albumId'},
        }},
    ]
    return list(_col('Cancion').aggregate(pipeline))


def listar_generos_disponibles():
    """Devuelve lista de SimpleNamespace(pk, nombre_genero) desde Cancion.generos."""
    nombres = _col('Cancion').distinct('generos.nombreGenero')
    return [
        SimpleNamespace(pk=n, nombre_genero=n)
        for n in sorted(nombres) if n
    ]


# ══════════════════════════════════════════════════════════════════════
# DETAIL
# ══════════════════════════════════════════════════════════════════════
def _find_cancion(pk):
    oid = _oid(pk)
    if not oid:
        return None
    return _col('Cancion').find_one({'$or': [{'cancionId': oid}, {'_id': oid}]})


def get_cancion_ns(pk):
    """Namespace compatible con las plantillas de detalle."""
    doc = _find_cancion(pk)
    if not doc:
        return None
    cid = str(_cancion_id(doc))
    album_doc = None
    if doc.get('albumId'):
        album_doc = _col('Albums').find_one({'albumId': doc['albumId']})
    return SimpleNamespace(
        pk=cid,
        idCancion=cid,
        nombre_cancion=doc.get('tituloCancion'),
        duracion=doc.get('duracion'),
        calidad_kbps=doc.get('calidadKbps'),
        total_reproducciones=doc.get('totalReproducciones', 0),
        estado_cancion=doc.get('estadoCancion'),
        letra_cancion=doc.get('letraCancion'),
        numero_pista=doc.get('numeroPista'),
        generos=[SimpleNamespace(nombre_genero=g.get('nombreGenero'))
                 for g in (doc.get('generos') or [])],
        album=SimpleNamespace(
            pk=str(album_doc.get('albumId') or album_doc['_id']) if album_doc else None,
            titulo_album=album_doc.get('tituloAlbum') if album_doc else None,
            artista=SimpleNamespace(
                nombre_artistico=album_doc.get('nombreArtistico') if album_doc else None
            ),
        ) if album_doc else SimpleNamespace(pk=None, titulo_album=None,
                                            artista=SimpleNamespace(nombre_artistico=None)),
    )


# ══════════════════════════════════════════════════════════════════════
# CRUD  (Artista)
# ══════════════════════════════════════════════════════════════════════
def _nombre_artistico(artista_id):
    oid = _oid(artista_id)
    if not oid:
        return '—'
    u = _col('Usuarios').find_one(
        {'$or': [{'_id': oid}, {'usuarioId': oid}]},
        {'perfilArtista.nombreArtistico': 1},
    )
    return (u or {}).get('perfilArtista', {}).get('nombreArtistico') or '—'


def crear_cancion(artista_id, album_id, nombre, duracion, fecha, calidad,
                  numero_pista, letra=None, generos=None):
    """
    generos: list[str] de nombres de género.
    """
    artista_oid = _oid(artista_id)
    nombre_artistico = _nombre_artistico(artista_id)
    generos_docs = [{'nombreGenero': g} for g in (generos or [])]
    doc = {
        'cancionId': ObjectId(),
        'tituloCancion': (nombre or '').strip(),
        'duracion': int(duracion),
        'fechaLanzamiento': _to_dt(fecha),
        'estadoCancion': 'activa',
        'calidadKbps': int(calidad),
        'totalReproducciones': 0,
        'letraCancion': (letra or '').strip() or None,
        'albumId': _oid(album_id),
        'numeroPista': int(numero_pista),
        'generos': generos_docs,
        'artistas': [{'artistaId': artista_oid, 'nombreArtistico': nombre_artistico}],
    }
    _col('Cancion').insert_one(doc)
    return str(doc['cancionId'])


def actualizar_cancion(pk, nombre=None, duracion=None, fecha=None,
                       calidad=None, numero_pista=None, letra=None,
                       estado=None, generos=None, artista_id=None):
    doc = _find_cancion(pk)
    if not doc:
        return False
    if artista_id:
        artistas = doc.get('artistas') or []
        ids = [a.get('artistaId') for a in artistas]
        if _oid(artista_id) not in ids:
            return False

    update = {}
    if nombre is not None:
        update['tituloCancion'] = nombre.strip()
    if duracion is not None:
        update['duracion'] = int(duracion)
    if fecha is not None:
        update['fechaLanzamiento'] = _to_dt(fecha)
    if calidad is not None:
        update['calidadKbps'] = int(calidad)
    if numero_pista is not None:
        update['numeroPista'] = int(numero_pista)
    if letra is not None:
        update['letraCancion'] = letra.strip() or None
    if estado is not None:
        update['estadoCancion'] = estado
    if generos is not None:
        update['generos'] = [{'nombreGenero': g} for g in generos]

    _col('Cancion').update_one({'_id': doc['_id']}, {'$set': update})
    return True


def desactivar_cancion(pk, artista_id=None):
    doc = _find_cancion(pk)
    if not doc:
        return None
    if artista_id:
        artistas = doc.get('artistas') or []
        ids = [a.get('artistaId') for a in artistas]
        if _oid(artista_id) not in ids:
            return None
    _col('Cancion').update_one({'_id': doc['_id']}, {'$set': {'estadoCancion': 'inactiva'}})
    return doc.get('tituloCancion')


def incrementar_reproducciones(pk):
    """Incrementa en 1 el contador totalReproducciones."""
    doc = _find_cancion(pk)
    if doc:
        _col('Cancion').update_one({'_id': doc['_id']}, {'$inc': {'totalReproducciones': 1}})


# ══════════════════════════════════════════════════════════════════════
# REPRODUCCION
# ══════════════════════════════════════════════════════════════════════
def registrar_reproduccion(usuario_id, cancion_id, pais='Ecuador',
                           duracion_escuchada=0, fue_saltada=False):
    """
    Inserta un evento inmutable en la colección Reproduccion.
    También incrementa totalReproducciones en Cancion.
    Devuelve el ID del evento creado.
    """
    doc = {
        'reproduccionId': ObjectId(),
        'usuarioId': _oid(usuario_id),
        'cancionId': _oid(cancion_id),
        'fechaHora': datetime.now(timezone.utc),
        'pais': pais or 'Ecuador',
        'duracionEscuchada': max(1, int(duracion_escuchada or 1)),
        'fueSaltada': bool(fue_saltada) if isinstance(fue_saltada, bool)
                      else (str(fue_saltada).upper() in ('S', 'TRUE', '1')),
    }
    _col('Reproduccion').insert_one(doc)
    incrementar_reproducciones(cancion_id)
    return str(doc['reproduccionId'])


def historial_reproduccion(usuario_id, limit=50):
    """Historial de reproducciones de un oyente (las más recientes primero)."""
    oid = _oid(usuario_id)
    if not oid:
        return []
    pipeline = [
        {'$match': {'usuarioId': oid}},
        {'$sort': {'fechaHora': -1}},
        {'$limit': limit},
        {'$lookup': {
            'from': 'Cancion',
            'localField': 'cancionId',
            'foreignField': 'cancionId',
            'as': '_c',
        }},
        {'$set': {'_c': {'$arrayElemAt': ['$_c', 0]}}},
        {'$project': {
            '_id': 0,
            'reproduccionId': {'$toString': '$reproduccionId'},
            'fechaHora': 1,
            'pais': 1,
            'duracionEscuchada': 1,
            'fueSaltada': 1,
            'nombreCancion': '$_c.tituloCancion',
            'nombreArtistico': {'$arrayElemAt': ['$_c.artistas.nombreArtistico', 0]},
        }},
    ]
    return list(_col('Reproduccion').aggregate(pipeline))


def top_canciones(limit=10):
    """Top N canciones activas por reproducciones totales."""
    pipeline = [
        {'$match': {'estadoCancion': 'activa'}},
        {'$sort': {'totalReproducciones': -1}},
        {'$limit': limit},
        {'$project': {
            '_id': 0,
            'idCancion': {'$toString': {'$ifNull': ['$cancionId', '$_id']}},
            'nombreCancion': '$tituloCancion',
            'totalReproducciones': 1,
            'nombreArtistico': {'$arrayElemAt': ['$artistas.nombreArtistico', 0]},
        }},
    ]
    return list(_col('Cancion').aggregate(pipeline))


# ══════════════════════════════════════════════════════════════════════
# GESTIÓN DE GÉNEROS EMBEBIDOS (admin)
# ══════════════════════════════════════════════════════════════════════
def agregar_genero_cancion(pk, nombre_genero):
    """Agrega un género embebido si no existe ya (por nombre, case-insensitive)."""
    doc = _find_cancion(pk)
    if not doc:
        return False
    nombre = (nombre_genero or '').strip()
    if not nombre:
        return False
    existentes = [g.get('nombreGenero', '').lower() for g in doc.get('generos', [])]
    if nombre.lower() in existentes:
        return False
    _col('Cancion').update_one(
        {'_id': doc['_id']},
        {'$push': {'generos': {'nombreGenero': nombre, 'descripcionGenero': ''}}}
    )
    return True


def quitar_genero_cancion(pk, nombre_genero):
    """Elimina un género embebido por nombre exacto."""
    doc = _find_cancion(pk)
    if not doc:
        return False
    _col('Cancion').update_one(
        {'_id': doc['_id']},
        {'$pull': {'generos': {'nombreGenero': nombre_genero}}}
    )
    return True
