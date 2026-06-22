"""
Regalías del ADMINISTRADOR sobre MongoDB (colección Regalias).

Provee los datos del panel admin de Regalías (resumen, por artista, por país,
tarifa implícita por país, consolidado por período e histórico) y la acción de
CANCELAR regalías (eliminar los registros de un período / artista / país).
"""

from calendar import monthrange
from datetime import date, datetime

from bson import ObjectId

from usuarios.mongo_service import get_database


def _col(n):
    return get_database()[n]


def _oid(v):
    v = str(v) if v is not None else ''
    return ObjectId(v) if ObjectId.is_valid(v) else None


def _split_periodo(periodo):
    try:
        a, m = (periodo or '').split('-')
        return int(m), int(a)
    except (ValueError, AttributeError):
        return None, None


def _artistas_map(ids):
    ids = [i for i in set(ids) if i is not None]
    if not ids:
        return {}
    cur = _col('Usuarios').find(
        {'$or': [{'_id': {'$in': ids}}, {'usuarioId': {'$in': ids}}]},
        {'usuarioId': 1, 'perfilArtista.nombreArtistico': 1})
    m = {}
    for d in cur:
        nombre = (d.get('perfilArtista') or {}).get('nombreArtistico') or '—'
        m[d['_id']] = nombre
        if d.get('usuarioId') is not None:
            m[d['usuarioId']] = nombre
    return m


def _discograficas_map(ids):
    ids = [i for i in set(ids) if i is not None]
    if not ids:
        return {}
    cur = _col('ContratosDiscograficos').find(
        {'artistaAsociado.artistaId': {'$in': ids}},
        {'artistaAsociado.artistaId': 1, 'discograficaAsociada.discograficaNombre': 1})
    m = {}
    for d in cur:
        aid = (d.get('artistaAsociado') or {}).get('artistaId')
        nombre = (d.get('discograficaAsociada') or {}).get('discograficaNombre')
        if aid is not None and nombre:
            m.setdefault(aid, nombre)
    return m


# ── KPIs / resumen ────────────────────────────────────────────────────
def resumen():
    pipe = [{'$group': {
        '_id': None,
        'MontoTotalGenerado': {'$sum': '$montoTotalGenerado'},
        'ReproduccionesTotales': {'$sum': '$cantidadReproducciones'},
        'TotalRegistros': {'$sum': 1},
    }}]
    res = list(_col('Regalias').aggregate(pipe))
    if not res:
        return {'MontoTotalGenerado': 0, 'ReproduccionesTotales': 0,
                'TotalRegistros': 0, 'MontoPromedio': 0}
    r = res[0]
    total = r.get('TotalRegistros') or 0
    monto = r.get('MontoTotalGenerado') or 0
    return {
        'MontoTotalGenerado': monto,
        'ReproduccionesTotales': r.get('ReproduccionesTotales') or 0,
        'TotalRegistros': total,
        'MontoPromedio': (monto / total) if total else 0,
    }


def por_artista(limite=20):
    pipe = [
        {'$group': {
            '_id': '$artistaId',
            'PagosRegistrados': {'$sum': 1},
            'ReproduccionesTotales': {'$sum': '$cantidadReproducciones'},
            'MontoTotalGenerado': {'$sum': '$montoTotalGenerado'},
        }},
        {'$sort': {'MontoTotalGenerado': -1}},
        {'$limit': int(limite)},
    ]
    rows = list(_col('Regalias').aggregate(pipe))
    nombres = _artistas_map([r['_id'] for r in rows])
    return [{
        'Artista': nombres.get(r['_id'], '—'),
        'PagosRegistrados': r.get('PagosRegistrados') or 0,
        'ReproduccionesTotales': r.get('ReproduccionesTotales') or 0,
        'MontoTotalGenerado': r.get('MontoTotalGenerado') or 0,
    } for r in rows]


def por_pais():
    pipe = [
        {'$group': {
            '_id': '$paisReproduccion',
            'Registros': {'$sum': 1},
            'Reproducciones': {'$sum': '$cantidadReproducciones'},
            'MontoTotal': {'$sum': '$montoTotalGenerado'},
        }},
        {'$sort': {'MontoTotal': -1}},
    ]
    return [{
        'Pais': r.get('_id') or '—',
        'Registros': r.get('Registros') or 0,
        'Reproducciones': r.get('Reproducciones') or 0,
        'MontoTotal': r.get('MontoTotal') or 0,
    } for r in _col('Regalias').aggregate(pipe)]


def tarifas_por_pais():
    """Tarifa implícita por país = monto generado / reproducciones."""
    pipe = [
        {'$group': {
            '_id': '$paisReproduccion',
            'monto': {'$sum': '$montoTotalGenerado'},
            'repro': {'$sum': '$cantidadReproducciones'},
        }},
        {'$sort': {'_id': 1}},
    ]
    out = []
    for r in _col('Regalias').aggregate(pipe):
        repro = r.get('repro') or 0
        out.append({
            'Pais': r.get('_id') or '—',
            'Tarifa': (r.get('monto') or 0) / repro if repro else 0,
        })
    return out


# ── Consolidado por período (cancelable) ──────────────────────────────
def por_periodo():
    pipe = [
        {'$group': {
            '_id': {'periodo': '$periodo', 'artistaId': '$artistaId', 'pais': '$paisReproduccion'},
            'TotalReproduccionesPeriodo': {'$sum': '$cantidadReproducciones'},
            'MontoBrutoTotal': {'$sum': '$montoTotalGenerado'},
            'PagoADiscografica': {'$sum': '$montoDiscografica'},
            'PagoNetoArtista': {'$sum': '$montoArtista'},
            'estados': {'$addToSet': {'$ifNull': ['$estadoPago', 'Pendiente']}},
        }},
        {'$sort': {'_id.periodo': -1}},
    ]
    rows = list(_col('Regalias').aggregate(pipe))
    art_ids = [r['_id'].get('artistaId') for r in rows]
    nombres = _artistas_map(art_ids)
    discos = _discograficas_map(art_ids)
    out = []
    for r in rows:
        k = r['_id']
        mes, anio = _split_periodo(k.get('periodo'))
        repro = r.get('TotalReproduccionesPeriodo') or 0
        bruto = r.get('MontoBrutoTotal') or 0
        estados = r.get('estados') or []
        estado = 'Pagado' if estados == ['Pagado'] else 'Pendiente'
        out.append({
            'MesPeriodo': mes,
            'AnioPeriodo': anio,
            'artistaId': str(k.get('artistaId')) if k.get('artistaId') else '',
            'BeneficiarioArtista': nombres.get(k.get('artistaId'), '—'),
            'Discografica': discos.get(k.get('artistaId'), 'Independiente'),
            'Pais': k.get('pais') or '—',
            'TarifaPais': (bruto / repro) if repro else 0,
            'TotalReproduccionesPeriodo': repro,
            'MontoBrutoTotal': bruto,
            'PagoADiscografica': r.get('PagoADiscografica') or 0,
            'PagoNetoArtista': r.get('PagoNetoArtista') or 0,
            'Estado': estado,
        })
    return out


# ── Histórico de registros ────────────────────────────────────────────
def listar_registros(desde=None, hasta=None):
    d = (desde or '0000-00')[:7]
    h = (hasta or '9999-99')[:7]
    pipe = [
        {'$match': {'periodo': {'$gte': d, '$lte': h}}},
        {'$lookup': {'from': 'Cancion', 'localField': 'cancionId',
                     'foreignField': 'cancionId', 'as': '_c'}},
        {'$set': {'_c': {'$arrayElemAt': ['$_c', 0]}}},
        {'$sort': {'periodo': -1}},
        {'$limit': 500},
    ]
    rows = list(_col('Regalias').aggregate(pipe))
    nombres = _artistas_map([r.get('artistaId') for r in rows])
    out = []
    for r in rows:
        mes, anio = _split_periodo(r.get('periodo'))
        ini = fin = None
        if mes and anio:
            ini = date(anio, mes, 1)
            fin = date(anio, mes, monthrange(anio, mes)[1])
        out.append({
            'idRegalia': str(r.get('regaliaId') or r['_id']),
            'fechaInicioPeriodo': ini,
            'fechaFinPeriodo': fin,
            'Artista': nombres.get(r.get('artistaId'), '—'),
            'Cancion': (r.get('_c') or {}).get('tituloCancion', '—'),
            'paisReproduccion': r.get('paisReproduccion'),
            'cantidadReproducciones': r.get('cantidadReproducciones') or 0,
            'montoTotalGenerado': r.get('montoTotalGenerado') or 0,
        })
    return out


def info_periodos():
    """Resumen ligero de períodos (para la cabecera informativa)."""
    periodos = sorted(_col('Regalias').distinct('periodo'))
    ultimo = periodos[-1] if periodos else None
    mes, anio = _split_periodo(ultimo) if ultimo else (None, None)
    return {
        'UltimoMesCerrado': mes,
        'UltimoAnioCerrado': anio,
        'UltimoPeriodoFin': None,
        'ProximoMesACerrar': None,
        'ProximoAnioACerrar': None,
        'PuedeCerrarseAhora': False,
        'ProximaFechaCierre': None,
        'TotalPeriodos': len(periodos),
    }


# ── CONFIRMAR pago de regalías ────────────────────────────────────────
def confirmar_periodo(mes, anio, artista_id=None, pais=None):
    """Confirma el PAGO de las regalías de un período (opcionalmente de un
    artista/país): marca estadoPago='Pagado' y registra fechaPago. El artista
    verá ese pago reflejado en su sección de monetización."""
    try:
        periodo = f'{int(anio):04d}-{int(mes):02d}'
    except (TypeError, ValueError):
        return 0
    filtro = {'periodo': periodo}
    aid = _oid(artista_id)
    if aid:
        filtro['artistaId'] = aid
    if pais:
        filtro['paisReproduccion'] = pais
    res = _col('Regalias').update_many(
        filtro,
        {'$set': {'estadoPago': 'Pagado', 'fechaPago': datetime.utcnow()}})
    return res.matched_count


def confirmar_rango(desde=None, hasta=None):
    """Confirma el pago de TODAS las regalías cuyo período cae en el rango."""
    d = (desde or '0000-00')[:7]
    h = (hasta or '9999-99')[:7]
    res = _col('Regalias').update_many(
        {'periodo': {'$gte': d, '$lte': h}},
        {'$set': {'estadoPago': 'Pagado', 'fechaPago': datetime.utcnow()}})
    return res.matched_count
