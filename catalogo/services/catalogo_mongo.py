"""
Servicio de CATÁLOGO sobre MongoDB (colecciones Albums y Cancion).

Las colecciones ya vienen desnormalizadas:
  - Albums:  tipoAlbum {nombreTipo,...} y nombreArtistico embebidos.
  - Cancion: generos[] y artistas[{artistaId,nombreArtistico}] embebidos.

Las vistas de LIST devuelven dicts con las MISMAS claves que esperaban los
SP (idAlbum, tituloAlbum, …); las de DETAIL devuelven namespaces con la forma
del ORM (album.titulo_album, c.numero_pista, …) para no tocar las plantillas.
"""

import re
from datetime import datetime, time
from types import SimpleNamespace

from bson import ObjectId

from usuarios.mongo_service import get_database

TIPOS_ALBUM = ('Single', 'EP', 'Album')


def _col(n):
    return get_database()[n]


def _oid(v):
    v = str(v) if v is not None else ''
    return ObjectId(v) if ObjectId.is_valid(v) else None


def _to_dt(value):
    """Normaliza date/'YYYY-MM-DD' a datetime (el validador exige date)."""
    if isinstance(value, datetime):
        return value
    if hasattr(value, 'year') and not isinstance(value, str):  # date
        return datetime.combine(value, time.min)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value[:19])
        except ValueError:
            try:
                return datetime.combine(datetime.strptime(value[:10], '%Y-%m-%d').date(), time.min)
            except ValueError:
                return None
    return None


# ══════════════════════════════════════════════════════════════════════
# ALBUMS
# ══════════════════════════════════════════════════════════════════════
def _find_album(pk):
    oid = _oid(pk)
    if not oid:
        return None
    return _col('Albums').find_one({'$or': [{'albumId': oid}, {'_id': oid}]})


def _album_join_id(doc):
    """Id por el que las canciones referencian al álbum (albumId o _id)."""
    return doc.get('albumId') or doc['_id']


def listar_albumes(artista_id=None, estado=None, busqueda=None):
    """LIST (dicts) para admin (sin artista) o artista (con su id)."""
    filtro = {}
    if artista_id:
        filtro['artistaId'] = _oid(artista_id)
    if estado:
        filtro['estadoAlbum'] = estado
    if busqueda:
        filtro['tituloAlbum'] = {'$regex': re.escape(busqueda), '$options': 'i'}

    salida = []
    for a in _col('Albums').find(filtro).sort('fechaLanzamiento', -1):
        salida.append({
            'idAlbum': str(a.get('albumId') or a['_id']),
            'tituloAlbum': a.get('tituloAlbum'),
            'nombreArtistico': a.get('nombreArtistico'),
            'nombreTipo': (a.get('tipoAlbum') or {}).get('nombreTipo'),
            'fechaLanzamientoAlbum': a.get('fechaLanzamiento'),
            'estadoAlbum': a.get('estadoAlbum'),
        })
    return salida


def _album_ns(doc):
    pk = str(doc.get('albumId') or doc['_id'])
    return SimpleNamespace(
        pk=pk,
        idAlbum=pk,
        titulo_album=doc.get('tituloAlbum'),
        descripcion_album=doc.get('descripcionAlbum'),
        fecha_lanzamiento_album=doc.get('fechaLanzamiento'),
        estado_album=doc.get('estadoAlbum'),
        artista=SimpleNamespace(nombre_artistico=doc.get('nombreArtistico')),
        tipo_album=SimpleNamespace(nombre_tipo=(doc.get('tipoAlbum') or {}).get('nombreTipo')),
    )


def _canciones_de_album(doc):
    join = _album_join_id(doc)
    cur = _col('Cancion').find({'albumId': join}).sort('numeroPista', 1)
    return [SimpleNamespace(
        numero_pista=c.get('numeroPista'),
        nombre_cancion=c.get('tituloCancion'),
        duracion=c.get('duracion'),
        calidad_kbps=c.get('calidadKbps'),
        total_reproducciones=c.get('totalReproducciones'),
        estado_cancion=c.get('estadoCancion'),
    ) for c in cur]


def get_album_detalle(pk, artista_id=None):
    """DETAIL (namespace + canciones). Si artista_id se da, valida propiedad."""
    doc = _find_album(pk)
    if not doc:
        return None
    if artista_id and doc.get('artistaId') != _oid(artista_id):
        return None
    return _album_ns(doc), _canciones_de_album(doc)


def get_album_ns(pk, artista_id=None):
    doc = _find_album(pk)
    if not doc:
        return None
    if artista_id and doc.get('artistaId') != _oid(artista_id):
        return None
    return _album_ns(doc)


def _nombre_artistico(artista_id):
    u = _col('Usuarios').find_one(
        {'$or': [{'_id': _oid(artista_id)}, {'usuarioId': _oid(artista_id)}]},
        {'perfilArtista.nombreArtistico': 1})
    return (u or {}).get('perfilArtista', {}).get('nombreArtistico') or '—'


def crear_album(artista_id, titulo, fecha, descripcion, tipo):
    doc = {
        'albumId': ObjectId(),
        'tituloAlbum': (titulo or '').strip(),
        'fechaLanzamiento': _to_dt(fecha),
        'descripcionAlbum': (descripcion or '').strip() or None,
        'estadoAlbum': 'activo',
        'artistaId': _oid(artista_id),
        'nombreArtistico': _nombre_artistico(artista_id),
        'tipoAlbum': {'nombreTipo': tipo if tipo in TIPOS_ALBUM else 'Album',
                      'descripcionTipo': None},
    }
    _col('Albums').insert_one(doc)
    return doc


def actualizar_album(pk, titulo, fecha, descripcion, tipo, estado=None, artista_id=None):
    doc = _find_album(pk)
    if not doc:
        return False
    if artista_id and doc.get('artistaId') != _oid(artista_id):
        return False
    update = {
        'tituloAlbum': (titulo or '').strip(),
        'fechaLanzamiento': _to_dt(fecha),
        'descripcionAlbum': (descripcion or '').strip() or None,
        'tipoAlbum.nombreTipo': tipo if tipo in TIPOS_ALBUM else 'Album',
    }
    if estado:
        update['estadoAlbum'] = estado
    _col('Albums').update_one({'_id': doc['_id']}, {'$set': update})
    return True


def desactivar_album(pk, artista_id=None):
    doc = _find_album(pk)
    if not doc:
        return None
    if artista_id and doc.get('artistaId') != _oid(artista_id):
        return None
    _col('Albums').update_one({'_id': doc['_id']}, {'$set': {'estadoAlbum': 'inactivo'}})
    return doc.get('tituloAlbum')


def eliminar_album(pk, artista_id=None):
    """Elimina el álbum y sus canciones."""
    doc = _find_album(pk)
    if not doc:
        return None
    if artista_id and doc.get('artistaId') != _oid(artista_id):
        return None
    _col('Cancion').delete_many({'albumId': _album_join_id(doc)})
    _col('Albums').delete_one({'_id': doc['_id']})
    return doc.get('tituloAlbum')
