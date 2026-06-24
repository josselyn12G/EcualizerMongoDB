"""
Servicio de REGALÍAS del artista sobre MongoDB.

Consume las vistas definidas en `scripts/Vistas Mongo Db/Regalias_Vistas.js`:
  - vw_regalias_artista          → histórico de regalías cerradas (detalle)
  - vw_regalias_mensual_artista  → evolución mes a mes (gráfico)
  - vw_reproducciones_artista    → reproducciones explotadas por artista (pendiente)

Si una vista AÚN no existe en Atlas, se usa automáticamente el pipeline
equivalente sobre la colección base, por lo que la página funciona aunque
todavía no se hayan creado las vistas.
"""

from datetime import datetime

from bson import ObjectId
from django.core.cache import cache

from usuarios.mongo_service import get_database


MESES_ABBR = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
              'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


# ── Pipelines de las vistas (idénticos al .js) — usados como fallback ──
_PIPE_REGALIAS = [
    {'$lookup': {'from': 'Cancion', 'localField': 'cancionId', 'foreignField': 'cancionId', 'as': '_c'}},
    {'$set': {'_c': {'$arrayElemAt': ['$_c', 0]}}},
    {'$lookup': {'from': 'Albums', 'localField': '_c.albumId', 'foreignField': 'albumId', 'as': '_a'}},
    {'$set': {'_a': {'$arrayElemAt': ['$_a', 0]}}},
    {'$project': {
        '_id': 0, 'artistaId': 1, 'periodo': 1,
        'anio': {'$toInt': {'$substrBytes': ['$periodo', 0, 4]}},
        'mes': {'$toInt': {'$substrBytes': ['$periodo', 5, 2]}},
        'pais': '$paisReproduccion',
        'reproducciones': '$cantidadReproducciones',
        'montoBruto': '$montoTotalGenerado',
        'montoArtista': '$montoArtista',
        'montoDiscografica': '$montoDiscografica',
        'cancion': {'$ifNull': ['$_c.tituloCancion', '—']},
        'album': {'$ifNull': ['$_a.tituloAlbum', '—']},
        'estadoPago': {'$ifNull': ['$estadoPago', 'Pendiente']},
    }},
]

_PIPE_MENSUAL = [
    {'$group': {
        '_id': {'artistaId': '$artistaId', 'periodo': '$periodo'},
        'reproducciones': {'$sum': '$cantidadReproducciones'},
        'montoBruto': {'$sum': '$montoTotalGenerado'},
        'montoArtista': {'$sum': '$montoArtista'},
    }},
    {'$project': {
        '_id': 0, 'artistaId': '$_id.artistaId', 'periodo': '$_id.periodo',
        'reproducciones': 1, 'montoBruto': 1, 'montoArtista': 1,
    }},
    {'$sort': {'periodo': 1}},
]

_PIPE_REPROS = [
    {'$lookup': {'from': 'Cancion', 'localField': 'cancionId', 'foreignField': 'cancionId', 'as': '_c'}},
    {'$set': {'_c': {'$arrayElemAt': ['$_c', 0]}}},
    {'$unwind': '$_c.artistas'},
    {'$project': {
        '_id': 0,
        'artistaId': '$_c.artistas.artistaId',
        'cancionId': 1,
        'cancion': '$_c.tituloCancion',
        'pais': 1,
        'fechaHora': 1,
        'liquidada': {'$ifNull': ['$liquidada', False]},
    }},
]


def _oid(value):
    value = str(value) if value is not None else ''
    return ObjectId(value) if ObjectId.is_valid(value) else None


def _vista_existe(view_name):
    """¿La vista existe en Atlas? (cacheado 5 min). Agregar sobre una vista
    inexistente NO lanza error, devuelve vacío — por eso hay que comprobarlo."""
    key = f'mongoview_existe:{view_name}'
    val = cache.get(key)
    if val is None:
        try:
            val = bool(get_database().list_collection_names(filter={'name': view_name}))
        except Exception:
            val = False
        cache.set(key, val, 300)
    return val


def _run(view_name, base_name, view_pipeline, query_pipeline):
    """Ejecuta el query sobre la VISTA si existe; si no, sobre la colección
    base aplicando el pipeline equivalente."""
    db = get_database()
    if _vista_existe(view_name):
        return list(db[view_name].aggregate(query_pipeline))
    return list(db[base_name].aggregate(view_pipeline + query_pipeline))


# ── Histórico de regalías cerradas ────────────────────────────────────
def historial_regalias(artista_id, desde=None, hasta=None):
    aid = _oid(artista_id)
    if not aid:
        return []
    d = (desde or '0000-00')[:7]
    h = (hasta or '9999-99')[:7]
    query = [
        {'$match': {'artistaId': aid, 'periodo': {'$gte': d, '$lte': h}}},
        {'$sort': {'periodo': -1, 'cancion': 1}},
    ]
    rows = _run('vw_regalias_artista', 'Regalias', _PIPE_REGALIAS, query)
    return [{
        'Mes': r.get('mes'),
        'Anio': r.get('anio'),
        'Cancion': r.get('cancion'),
        'Album': r.get('album'),
        'Pais': r.get('pais'),
        'Reproducciones': r.get('reproducciones') or 0,
        'MontoBruto': r.get('montoBruto') or 0,
        'MontoDiscografica': r.get('montoDiscografica') or 0,
        'MontoNetoArtista': r.get('montoArtista') or 0,
        'EstadoPago': r.get('estadoPago') or 'Pendiente',
    } for r in rows]


# ── Evolución mensual (gráfico) ───────────────────────────────────────
def evolucion_regalias(artista_id, meses=12):
    aid = _oid(artista_id)
    if not aid:
        return []
    query = [{'$match': {'artistaId': aid}}, {'$sort': {'periodo': 1}}]
    rows = _run('vw_regalias_mensual_artista', 'Regalias', _PIPE_MENSUAL, query)
    if meses:
        rows = rows[-meses:]
    salida = []
    for r in rows:
        periodo = r.get('periodo', '') or ''
        try:
            anio, mes = periodo.split('-')
            etiqueta = f'{MESES_ABBR[int(mes)]} {anio}'
        except (ValueError, IndexError):
            etiqueta = periodo
        salida.append({
            'Etiqueta': etiqueta,
            'Reproducciones': r.get('reproducciones') or 0,
            'MontoBruto': r.get('montoBruto') or 0,
            'MontoNetoArtista': r.get('montoArtista') or 0,
        })
    return salida


def _porcentaje_discografica(aid):
    db = get_database()
    ct = (db['ContratosDiscograficos'].find_one(
              {'artistaAsociado.artistaId': aid, 'estadoContrato': 'Activo'},
              {'porcentajeDiscografica': 1})
          or db['ContratosDiscograficos'].find_one(
              {'artistaAsociado.artistaId': aid}, {'porcentajeDiscografica': 1}))
    return float((ct or {}).get('porcentajeDiscografica') or 0)


# ── Pendiente de cierre (cálculo en vivo desde reproducciones) ────────
def pendiente_regalias(artista_id, desde=None, hasta=None, tarifa=0.004):
    aid = _oid(artista_id)
    if not aid:
        return []

    def _fecha(value, default):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return default

    d = _fecha(desde, datetime(2000, 1, 1))
    h = _fecha(hasta, datetime(2100, 1, 1)).replace(hour=23, minute=59, second=59)

    query = [
        {'$match': {'artistaId': aid, 'fechaHora': {'$gte': d, '$lte': h},
                    'liquidada': {'$ne': True}}},
        {'$group': {'_id': {'cancion': '$cancion', 'pais': '$pais'},
                    'reproducciones': {'$sum': 1}}},
        {'$sort': {'reproducciones': -1}},
    ]
    rows = _run('vw_reproducciones_artista', 'Reproduccion', _PIPE_REPROS, query)

    pct = _porcentaje_discografica(aid) / 100.0
    tarifa = float(tarifa or 0)
    salida = []
    for r in rows:
        repro = r.get('reproducciones') or 0
        bruto = repro * tarifa
        deduccion = bruto * pct
        salida.append({
            'Cancion': (r.get('_id') or {}).get('cancion'),
            'Pais': (r.get('_id') or {}).get('pais'),
            'TotalReproducciones': repro,
            'MontoBruto': round(bruto, 4),
            'DeduccionDiscografica': round(deduccion, 4),
            'MontoNetoArtista': round(bruto - deduccion, 4),
        })
    return salida
