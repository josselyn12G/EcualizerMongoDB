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
    from datetime import timezone as _tz
    from pymongo.errors import WriteError
    doc = {
        'albumId': ObjectId(),
        'tituloAlbum': (titulo or '').strip(),
        'fechaLanzamiento': _to_dt(fecha),
        'fechaCreacion': datetime.now(_tz.utc),
        'descripcionAlbum': (descripcion or '').strip() or None,
        'estadoAlbum': 'activo',
        'artistaId': _oid(artista_id),
        'nombreArtistico': _nombre_artistico(artista_id),
        'tipoAlbum': {'nombreTipo': (tipo or '').strip() or 'Album',
                      'descripcionTipo': None},
    }
    try:
        _col('Albums').insert_one(doc)
    except WriteError:
        # El esquema sólo admite Single/EP/Album en el enum: si se eligió un
        # tipo personalizado y la validación es estricta, lo guardamos como
        # 'Album' para garantizar que el álbum SÍ quede registrado en la base.
        doc['tipoAlbum']['nombreTipo'] = 'Album'
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
        'tipoAlbum.nombreTipo': (tipo or '').strip() or 'Album',
    }
    if estado:
        update['estadoAlbum'] = estado
    from pymongo.errors import WriteError
    try:
        _col('Albums').update_one({'_id': doc['_id']}, {'$set': update})
    except WriteError:
        update['tipoAlbum.nombreTipo'] = 'Album'
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
# CATÁLOGO CANÓNICO DE GÉNEROS / TIPOS  (fuente única para artista/admin/oyente)
#
# Los géneros y tipos viven embebidos en Cancion/Albums, pero para que el
# catálogo sea COHERENTE entre el artista (al crear), el administrador (CRUD)
# y el oyente (filtros), mantenemos además dos colecciones canónicas:
#   - GenerosMusicales: {nombreGenero, descripcionGenero}
#   - TiposAlbum:       {nombreTipo, descripcionTipo}
# El "catálogo" expuesto = colección canónica ∪ lo realmente usado en datos.
# ══════════════════════════════════════════════════════════════════════
def catalogo_generos():
    """Lista ordenada de nombres de género (canónicos + usados en canciones)."""
    nombres = set()
    for d in _col('GenerosMusicales').find({}, {'nombreGenero': 1}):
        if d.get('nombreGenero'):
            nombres.add(d['nombreGenero'])
    for n in _col('Cancion').distinct('generos.nombreGenero'):
        if n:
            nombres.add(n)
    return sorted(nombres)


def catalogo_tipos_album():
    """Lista ordenada de tipos de álbum (defaults + canónicos + usados)."""
    nombres = set(TIPOS_ALBUM)
    for d in _col('TiposAlbum').find({}, {'nombreTipo': 1}):
        if d.get('nombreTipo'):
            nombres.add(d['nombreTipo'])
    for n in _col('Albums').distinct('tipoAlbum.nombreTipo'):
        if n:
            nombres.add(n)
    return sorted(nombres)


# ══════════════════════════════════════════════════════════════════════
# GÉNEROS (admin)
# ══════════════════════════════════════════════════════════════════════
def crear_genero_mongo(nombre, descripcion=''):
    """Registra un género en el catálogo canónico. False si ya existía."""
    nombre = (nombre or '').strip()
    if not nombre:
        return False
    if _col('GenerosMusicales').count_documents({'nombreGenero': nombre}, limit=1):
        return False
    _col('GenerosMusicales').insert_one({
        'nombreGenero': nombre,
        'descripcionGenero': (descripcion or '').strip() or None,
    })
    return True


def listar_generos_mongo(busqueda=None):
    """Lista TODOS los géneros (canónicos + usados) con su conteo de canciones."""
    conteos = {}
    for i in _col('Cancion').aggregate([
        {'$unwind': '$generos'},
        {'$group': {'_id': '$generos.nombreGenero', 'n': {'$sum': 1}}},
    ]):
        if i['_id']:
            conteos[i['_id']] = i['n']
    nombres = catalogo_generos()
    if busqueda:
        q = busqueda.lower()
        nombres = [n for n in nombres if q in (n or '').lower()]
    return [{
        'idGeneroMusical': n,
        'nombreGenero':    n,
        'totalCanciones':  conteos.get(n, 0),
    } for n in nombres]


def renombrar_genero_mongo(nombre_actual, nombre_nuevo):
    """Renombra un género en las canciones y en el catálogo canónico."""
    nombre_nuevo = (nombre_nuevo or '').strip()
    if not nombre_nuevo:
        return False
    _col('Cancion').update_many(
        {'generos.nombreGenero': nombre_actual},
        {'$set': {'generos.$[g].nombreGenero': nombre_nuevo}},
        array_filters=[{'g.nombreGenero': nombre_actual}],
    )
    _col('GenerosMusicales').update_many(
        {'nombreGenero': nombre_actual},
        {'$set': {'nombreGenero': nombre_nuevo}},
    )
    return True


def eliminar_genero_mongo(nombre):
    """Elimina un género de las canciones y del catálogo canónico."""
    _col('Cancion').update_many(
        {'generos.nombreGenero': nombre},
        {'$pull': {'generos': {'nombreGenero': nombre}}},
    )
    _col('GenerosMusicales').delete_many({'nombreGenero': nombre})
    return True


# ══════════════════════════════════════════════════════════════════════
# TIPOS DE ÁLBUM EMBEBIDOS (admin)
# ══════════════════════════════════════════════════════════════════════
def listar_tipos_album_mongo(busqueda=None):
    """Lista TODOS los tipos de álbum (defaults + canónicos + usados) con conteo."""
    conteos, descrs = {}, {}
    for i in _col('Albums').aggregate([
        {'$group': {
            '_id': '$tipoAlbum.nombreTipo',
            'descripcion': {'$first': '$tipoAlbum.descripcionTipo'},
            'n': {'$sum': 1},
        }},
    ]):
        if i['_id']:
            conteos[i['_id']] = i['n']
            descrs[i['_id']] = i.get('descripcion') or ''
    for d in _col('TiposAlbum').find({}, {'nombreTipo': 1, 'descripcionTipo': 1}):
        if d.get('nombreTipo') and not descrs.get(d['nombreTipo']):
            descrs[d['nombreTipo']] = d.get('descripcionTipo') or ''
    nombres = catalogo_tipos_album()
    if busqueda:
        q = busqueda.lower()
        nombres = [n for n in nombres if q in (n or '').lower()]
    return [{
        'idTipoAlbum':   n,
        'nombreTipo':    n,
        'descripcionTipo': descrs.get(n, ''),
        'totalAlbumes':  conteos.get(n, 0),
    } for n in nombres]


def renombrar_tipo_album_mongo(nombre_actual, nombre_nuevo):
    """Renombra un tipo de álbum en los álbumes y en el catálogo canónico."""
    nombre_nuevo = (nombre_nuevo or '').strip()
    if not nombre_nuevo:
        return False
    _col('Albums').update_many(
        {'tipoAlbum.nombreTipo': nombre_actual},
        {'$set': {'tipoAlbum.nombreTipo': nombre_nuevo}},
    )
    _col('TiposAlbum').update_many(
        {'nombreTipo': nombre_actual},
        {'$set': {'nombreTipo': nombre_nuevo}},
    )
    return True


def agregar_tipo_album_mongo(nombre, descripcion=''):
    """Registra un tipo de álbum en el catálogo canónico. False si ya existía."""
    nombre = (nombre or '').strip()
    if not nombre or nombre in catalogo_tipos_album():
        return False
    _col('TiposAlbum').insert_one({
        'nombreTipo': nombre,
        'descripcionTipo': (descripcion or '').strip() or None,
    })
    return True
