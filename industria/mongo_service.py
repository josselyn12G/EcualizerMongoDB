"""
Servicio MongoDB para la app `industria` (Discográficas y Contratos).

Colecciones:
  - Discograficas           : {discograficaId, nombreDiscografica, paisOrigen,
                               correoContacto, telefonoContacto}
  - ContratosDiscograficos  : {contratoId, fechaInicio(date), fechaFin(str|null),
                               porcentajeArtista, porcentajeDiscografica,
                               estadoContrato, discograficaAsociada{...},
                               artistaAsociado{...}}

Las funciones devuelven SimpleNamespace con la MISMA forma que el ORM anterior
(`c.artista.nombre_artistico`, `c.discografica.pais_origen`, `c.id_contrato`…)
para no tener que reescribir las plantillas.

Las consultas equivalen a las vistas de
`scripts/Vistas Mongo Db/Industria_Vistas_Compass.js` (puedes crearlas en
Compass para consultarlas directamente; el servicio funciona con o sin ellas).
"""

import re
from datetime import datetime, date, time, timezone
from types import SimpleNamespace

from bson import ObjectId

from usuarios.mongo_service import get_database, admin_list_users

ESTADOS_CONTRATO = ('Activo', 'Cancelado', 'Finalizado')


def _col(n):
    return get_database()[n]


def _oid(v):
    v = str(v) if v is not None else ''
    return ObjectId(v) if ObjectId.is_valid(v) else None


def _to_dt(value):
    """date / 'YYYY-MM-DD' → datetime (para fechaInicio, bsonType date)."""
    if isinstance(value, datetime):
        return value
    if hasattr(value, 'year') and not isinstance(value, str):
        return datetime.combine(value, time.min)
    if isinstance(value, str) and value:
        try:
            return datetime.combine(datetime.strptime(value[:10], '%Y-%m-%d').date(), time.min)
        except ValueError:
            return None
    return None


def _to_date(value):
    """datetime / 'YYYY-MM-DD' / None → date | None (para mostrar con |date)."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, 'year') and not isinstance(value, str):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


def _date_str(value):
    """date / 'YYYY-MM-DD' → 'YYYY-MM-DD' | None (fechaFin es string|null)."""
    d = _to_date(value)
    return d.isoformat() if d else None


# ══════════════════════════════════════════════════════════════════════
# DISCOGRÁFICAS
# ══════════════════════════════════════════════════════════════════════
def _find_disco(pk):
    oid = _oid(pk)
    if not oid:
        return None
    return _col('Discograficas').find_one({'$or': [{'discograficaId': oid}, {'_id': oid}]})


def _disco_id(doc):
    return doc.get('discograficaId') or doc['_id']


def _disco_ns(doc):
    pk = str(_disco_id(doc))
    return SimpleNamespace(
        pk=pk, id_discografica=pk,
        nombre_discografica=doc.get('nombreDiscografica'),
        pais_origen=doc.get('paisOrigen'),
        correo_contacto=doc.get('correoContacto'),
        telefono_contacto=doc.get('telefonoContacto'),
    )


def _disco_derivada_ns(did, nombre):
    """Discográfica que sólo existe embebida en los contratos (aún no está en
    la colección Discograficas). Campos de contacto vacíos hasta que se edite."""
    pk = str(did) if did else (nombre or '')
    return SimpleNamespace(
        pk=pk, id_discografica=pk,
        nombre_discografica=nombre, pais_origen='',
        correo_contacto='', telefono_contacto='')


def listar_discograficas(busqueda=None):
    """Discográficas de la colección Discograficas UNIDAS a las que aparecen
    embebidas en los contratos (para que el listado no quede vacío si sólo se
    migraron los contratos)."""
    filtro = {}
    if busqueda:
        filtro['nombreDiscografica'] = {'$regex': re.escape(busqueda), '$options': 'i'}
    docs = list(_col('Discograficas').find(filtro).sort('nombreDiscografica', 1))
    out = [_disco_ns(d) for d in docs]
    ids_existentes = {str(_disco_id(d)) for d in docs}
    nombres_existentes = {(d.get('nombreDiscografica') or '').lower() for d in docs}

    q = (busqueda or '').lower()
    for r in _col('ContratosDiscograficos').aggregate([
        {'$group': {'_id': '$discograficaAsociada.discograficaId',
                    'nombre': {'$first': '$discograficaAsociada.discograficaNombre'}}},
    ]):
        did, nombre = r['_id'], r.get('nombre')
        if not nombre:
            continue
        if q and q not in nombre.lower():
            continue
        if (did is not None and str(did) in ids_existentes) or nombre.lower() in nombres_existentes:
            continue
        out.append(_disco_derivada_ns(did, nombre))
    out.sort(key=lambda d: (d.nombre_discografica or '').lower())
    return out


def get_discografica(pk):
    doc = _find_disco(pk)
    if doc:
        return _disco_ns(doc)
    # Derivada: existe sólo embebida en algún contrato.
    oid = _oid(pk)
    if oid:
        c = _col('ContratosDiscograficos').find_one(
            {'discograficaAsociada.discograficaId': oid},
            {'discograficaAsociada': 1})
        if c:
            dis = c.get('discograficaAsociada') or {}
            return _disco_derivada_ns(dis.get('discograficaId') or oid,
                                      dis.get('discograficaNombre'))
    return None


def nombre_disco_existe(nombre, exclude_pk=None):
    nombre = (nombre or '').strip()
    filtro = {'nombreDiscografica': {'$regex': f'^{re.escape(nombre)}$', '$options': 'i'}}
    doc = _col('Discograficas').find_one(filtro, {'discograficaId': 1, '_id': 1})
    if not doc:
        return False
    if exclude_pk and str(_disco_id(doc)) == str(exclude_pk):
        return False
    return True


def crear_discografica(nombre, pais, correo, telefono):
    doc = {
        'discograficaId': ObjectId(),
        'nombreDiscografica': (nombre or '').strip(),
        'paisOrigen': (pais or '').strip(),
        'correoContacto': (correo or '').strip().lower(),
        'telefonoContacto': (telefono or '').strip(),
    }
    _col('Discograficas').insert_one(doc)
    return str(doc['discograficaId'])


def actualizar_discografica(pk, nombre, pais, correo, telefono):
    nombre = (nombre or '').strip()
    campos = {
        'nombreDiscografica': nombre,
        'paisOrigen': (pais or '').strip(),
        'correoContacto': (correo or '').strip().lower(),
        'telefonoContacto': (telefono or '').strip(),
    }
    doc = _find_disco(pk)
    if doc:
        did = _disco_id(doc)
        _col('Discograficas').update_one({'_id': doc['_id']}, {'$set': campos})
    else:
        # Discográfica derivada de contratos: la materializamos en la colección
        # usando el MISMO id que referencian los contratos.
        did = _oid(pk)
        if not did:
            return False
        _col('Discograficas').insert_one({'discograficaId': did, **campos})
    # Mantener el nombre desnormalizado en los contratos.
    _col('ContratosDiscograficos').update_many(
        {'discograficaAsociada.discograficaId': did},
        {'$set': {'discograficaAsociada.discograficaNombre': nombre}})
    return True


def eliminar_discografica(pk):
    """Devuelve (ok, mensaje). No elimina si tiene contratos asociados."""
    doc = _find_disco(pk)
    if not doc:
        return False, 'Discográfica no encontrada.'
    did = _disco_id(doc)
    if _col('ContratosDiscograficos').count_documents(
            {'discograficaAsociada.discograficaId': did}, limit=1):
        return False, 'No se puede eliminar: tiene contratos asociados.'
    _col('Discograficas').delete_one({'_id': doc['_id']})
    return True, doc.get('nombreDiscografica')


def discograficas_choices():
    return [(d.pk, d.nombre_discografica) for d in listar_discograficas()]


# ══════════════════════════════════════════════════════════════════════
# CONTRATOS
# ══════════════════════════════════════════════════════════════════════
def _find_contrato(pk):
    oid = _oid(pk)
    if not oid:
        return None
    return _col('ContratosDiscograficos').find_one(
        {'$or': [{'contratoId': oid}, {'_id': oid}]})


def _contrato_id(doc):
    return doc.get('contratoId') or doc['_id']


def _contrato_ns(doc, pais_map=None):
    pk = str(_contrato_id(doc))
    art = doc.get('artistaAsociado') or {}
    dis = doc.get('discograficaAsociada') or {}
    did = dis.get('discograficaId')
    pais = (pais_map or {}).get(did) if pais_map is not None else _pais_de_disco(did)
    return SimpleNamespace(
        pk=pk, id_contrato=pk,
        artista_id=str(art.get('artistaId') or ''),
        discografica_id=str(did or ''),
        fecha_inicio=_to_date(doc.get('fechaInicio')),
        fecha_fin=_to_date(doc.get('fechaFin')),
        porcentaje_artista=doc.get('porcentajeArtista') or 0,
        porcentaje_discografica=doc.get('porcentajeDiscografica') or 0,
        estado_contrato=doc.get('estadoContrato'),
        artista=SimpleNamespace(nombre_artistico=art.get('nombreArtistico') or '—'),
        discografica=SimpleNamespace(
            nombre_discografica=dis.get('discograficaNombre') or '—',
            pais_origen=pais or '—'),
    )


def _pais_de_disco(did):
    if not did:
        return None
    d = _col('Discograficas').find_one({'discograficaId': did}, {'paisOrigen': 1})
    return (d or {}).get('paisOrigen')


def _pais_map(dids):
    dids = [d for d in set(dids) if d is not None]
    if not dids:
        return {}
    m = {}
    for d in _col('Discograficas').find(
            {'discograficaId': {'$in': dids}}, {'discograficaId': 1, 'paisOrigen': 1}):
        m[d['discograficaId']] = d.get('paisOrigen')
    return m


def listar_contratos(estado=None, artista_id=None):
    filtro = {}
    if estado:
        filtro['estadoContrato'] = estado
    if artista_id:
        filtro['artistaAsociado.artistaId'] = _oid(artista_id)
    docs = list(_col('ContratosDiscograficos').find(filtro).sort('fechaInicio', -1))
    pais_map = _pais_map([(d.get('discograficaAsociada') or {}).get('discograficaId')
                          for d in docs])
    return [_contrato_ns(d, pais_map) for d in docs]


def get_contrato(pk):
    doc = _find_contrato(pk)
    return _contrato_ns(doc) if doc else None


def _nombre_artistico(artista_id):
    oid = _oid(artista_id)
    if not oid:
        return '—'
    u = _col('Usuarios').find_one(
        {'$or': [{'_id': oid}, {'usuarioId': oid}]},
        {'perfilArtista.nombreArtistico': 1})
    return (u or {}).get('perfilArtista', {}).get('nombreArtistico') or '—'


def _disco_asociada(discografica_id):
    """Snapshot {discograficaId, discograficaNombre} resolviendo el nombre desde
    la colección Discograficas o, si no está, desde los contratos existentes."""
    d = get_discografica(discografica_id)
    return {
        'discograficaId': _oid(discografica_id),
        'discograficaNombre': (d.nombre_discografica if d else None) or '—',
    }


def crear_contrato(artista_id, discografica_id, fecha_inicio, fecha_fin,
                   pct_artista, pct_disco, estado):
    doc = {
        'contratoId': ObjectId(),
        'fechaInicio': _to_dt(fecha_inicio) or datetime.now(timezone.utc),
        'fechaFin': _date_str(fecha_fin),
        'porcentajeArtista': float(pct_artista or 0),
        'porcentajeDiscografica': float(pct_disco or 0),
        'estadoContrato': estado if estado in ESTADOS_CONTRATO else 'Activo',
        'discograficaAsociada': _disco_asociada(discografica_id),
        'artistaAsociado': {
            'artistaId': _oid(artista_id),
            'nombreArtistico': _nombre_artistico(artista_id),
        },
    }
    _col('ContratosDiscograficos').insert_one(doc)
    return str(doc['contratoId'])


def actualizar_contrato(pk, artista_id, discografica_id, fecha_inicio, fecha_fin,
                        pct_artista, pct_disco, estado):
    doc = _find_contrato(pk)
    if not doc:
        return False
    _col('ContratosDiscograficos').update_one({'_id': doc['_id']}, {'$set': {
        'fechaInicio': _to_dt(fecha_inicio) or doc.get('fechaInicio'),
        'fechaFin': _date_str(fecha_fin),
        'porcentajeArtista': float(pct_artista or 0),
        'porcentajeDiscografica': float(pct_disco or 0),
        'estadoContrato': estado if estado in ESTADOS_CONTRATO else 'Activo',
        'discograficaAsociada': _disco_asociada(discografica_id),
        'artistaAsociado': {
            'artistaId': _oid(artista_id),
            'nombreArtistico': _nombre_artistico(artista_id),
        },
    }})
    return True


def eliminar_contrato(pk):
    doc = _find_contrato(pk)
    if not doc:
        return False
    _col('ContratosDiscograficos').delete_one({'_id': doc['_id']})
    return True


def contratos_kpis(artista_id=None):
    match = {}
    if artista_id:
        match['artistaAsociado.artistaId'] = _oid(artista_id)
    pipeline = [
        {'$match': match},
        {'$group': {'_id': '$estadoContrato', 'n': {'$sum': 1}}},
    ]
    counts = {r['_id']: r['n'] for r in _col('ContratosDiscograficos').aggregate(pipeline)}
    return {
        'total': sum(counts.values()),
        'activos': counts.get('Activo', 0),
        'finalizados': counts.get('Finalizado', 0),
        'cancelados': counts.get('Cancelado', 0),
    }


def artistas_choices():
    """[(pk, nombreArtistico)] de todos los artistas, para el form de contrato."""
    try:
        artistas = admin_list_users('artista')
    except Exception:
        artistas = []
    out = []
    for a in artistas:
        nombre = getattr(a, 'nombre_artistico', None) or '—'
        out.append((getattr(a, 'pk', ''), nombre))
    out.sort(key=lambda x: (x[1] or '').lower())
    return out
