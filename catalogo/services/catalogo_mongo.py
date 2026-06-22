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


# ══════════════════════════════════════════════════════════════════════
# GÉNEROS EMBEBIDOS (admin)
# ══════════════════════════════════════════════════════════════════════
def listar_generos_mongo(busqueda=None):
    """Lista todos los géneros distintos con conteo de canciones."""
    pipeline = [
        {'$unwind': '$generos'},
        {'$group': {
            '_id': '$generos.nombreGenero',
            'total_canciones': {'$sum': 1},
        }},
        {'$sort': {'_id': 1}},
    ]
    items = list(_col('Cancion').aggregate(pipeline))
    if busqueda:
        q = busqueda.lower()
        items = [i for i in items if q in (i['_id'] or '').lower()]
    return [{
        'idGeneroMusical': i['_id'],
        'nombreGenero':    i['_id'],
        'totalCanciones':  i['total_canciones'],
    } for i in items]


def renombrar_genero_mongo(nombre_actual, nombre_nuevo):
    """Renombra un género en todos los documentos Cancion."""
    nombre_nuevo = (nombre_nuevo or '').strip()
    if not nombre_nuevo:
        return False
    _col('Cancion').update_many(
        {'generos.nombreGenero': nombre_actual},
        {'$set': {'generos.$[g].nombreGenero': nombre_nuevo}},
        array_filters=[{'g.nombreGenero': nombre_actual}],
    )
    return True


def eliminar_genero_mongo(nombre):
    """Elimina un género de todos los documentos Cancion."""
    _col('Cancion').update_many(
        {'generos.nombreGenero': nombre},
        {'$pull': {'generos': {'nombreGenero': nombre}}},
    )
    return True


# ══════════════════════════════════════════════════════════════════════
# TIPOS DE ÁLBUM EMBEBIDOS (admin)
# ══════════════════════════════════════════════════════════════════════
def listar_tipos_album_mongo(busqueda=None):
    """Lista todos los tipos de álbum distintos con conteo."""
    pipeline = [
        {'$group': {
            '_id': '$tipoAlbum.nombreTipo',
            'descripcion': {'$first': '$tipoAlbum.descripcionTipo'},
            'total_albumes': {'$sum': 1},
        }},
        {'$sort': {'_id': 1}},
    ]
    items = list(_col('Albums').aggregate(pipeline))
    if busqueda:
        q = busqueda.lower()
        items = [i for i in items if q in (i['_id'] or '').lower()]
    return [{
        'idTipoAlbum':   i['_id'],
        'nombreTipo':    i['_id'],
        'descripcionTipo': i.get('descripcion') or '',
        'totalAlbumes':  i['total_albumes'],
    } for i in items]


def renombrar_tipo_album_mongo(nombre_actual, nombre_nuevo):
    """Renombra un tipo de álbum en todos los documentos Albums."""
    nombre_nuevo = (nombre_nuevo or '').strip()
    if not nombre_nuevo:
        return False
    _col('Albums').update_many(
        {'tipoAlbum.nombreTipo': nombre_actual},
        {'$set': {'tipoAlbum.nombreTipo': nombre_nuevo}},
    )
    return True


def agregar_tipo_album_mongo(nombre, descripcion=''):
    """Crea un nuevo tipo de álbum (se usará al crear/editar álbumes)."""
    # En MongoDB los tipos son strings embebidos; solo validamos que no exista.
    existentes = _col('Albums').distinct('tipoAlbum.nombreTipo')
    nombre = (nombre or '').strip()
    if not nombre or nombre in existentes:
        return False
    return True  # El tipo se usará al siguiente álbum que se cree con ese nombre
