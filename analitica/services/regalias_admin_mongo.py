"""
Regalías del ADMINISTRADOR sobre MongoDB (colección Regalias).

Provee los datos del panel admin de Regalías (resumen, por artista, por país,
tarifa implícita por país, consolidado por período e histórico) y la acción de
CANCELAR regalías (eliminar los registros de un período / artista / país).
"""

from calendar import monthrange
from datetime import date, datetime

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

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


# Tarifa por defecto (USD por reproducción) cuando un país aún no tiene
# tarifa implícita en regalías ya registradas.
DEFAULT_TARIFA = 0.005


def _tarifas_map():
    """Tarifa implícita por país a partir de las regalías ya registradas."""
    m = {}
    for t in tarifas_por_pais():
        if t.get('Tarifa'):
            m[t['Pais']] = t['Tarifa']
    return m


def _pct_discografica(aid):
    """Porcentaje (0..1) que se lleva la discográfica del artista, si tiene
    contrato activo."""
    if not aid:
        return 0.0
    db = get_database()
    ct = (db['ContratosDiscograficos'].find_one(
              {'artistaAsociado.artistaId': aid, 'estadoContrato': 'Activo'},
              {'porcentajeDiscografica': 1})
          or db['ContratosDiscograficos'].find_one(
              {'artistaAsociado.artistaId': aid}, {'porcentajeDiscografica': 1}))
    return float((ct or {}).get('porcentajeDiscografica') or 0) / 100.0


def _pct_map(ids):
    """Mapa {artistaId: pct (0..1)} en UNA sola consulta (evita una query por
    fila al calcular regalías). Prefiere el contrato 'Activo' si hay varios."""
    ids = [i for i in set(ids) if i is not None]
    if not ids:
        return {}
    m = {}
    for d in _col('ContratosDiscograficos').find(
            {'artistaAsociado.artistaId': {'$in': ids}},
            {'artistaAsociado.artistaId': 1, 'porcentajeDiscografica': 1,
             'estadoContrato': 1}):
        aid = (d.get('artistaAsociado') or {}).get('artistaId')
        if aid is None:
            continue
        pct = float(d.get('porcentajeDiscografica') or 0) / 100.0
        if d.get('estadoContrato') == 'Activo' or aid not in m:
            m[aid] = pct
    return m


def _repro_no_liquidada():
    """Match de reproducciones que todavía no han sido pagadas (liquidadas)."""
    return {'$or': [{'liquidada': {'$exists': False}}, {'liquidada': False}]}


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


# ── Pendientes calculados EN VIVO desde reproducciones sin liquidar ────
def pendientes_por_reproduccion():
    """Cada reproducción registrada genera una regalía PENDIENTE para el
    artista. Se agrupan por artista/período/país hasta que el admin confirma
    el pago (momento en que pasan a la colección Regalias y al histórico)."""
    # Agrupamos PRIMERO las reproducciones (barato) y sólo después resolvemos
    # la canción/artista: así hacemos 1 lookup por canción/período/país en vez
    # de uno por cada reproducción (mucho más rápido en colecciones grandes).
    pipe = [
        {'$match': _repro_no_liquidada()},
        {'$group': {
            '_id': {
                'cancionId': '$cancionId',
                'periodo': {'$dateToString': {'format': '%Y-%m', 'date': '$fechaHora'}},
                'pais': {'$ifNull': ['$pais', 'Ecuador']},
            },
            'reproducciones': {'$sum': 1},
        }},
        {'$lookup': {'from': 'Cancion', 'localField': '_id.cancionId',
                     'foreignField': 'cancionId', 'as': '_c'}},
        {'$set': {'_c': {'$arrayElemAt': ['$_c', 0]}}},
        {'$unwind': '$_c.artistas'},
        {'$group': {
            '_id': {
                'artistaId': '$_c.artistas.artistaId',
                'periodo': '$_id.periodo',
                'pais': '$_id.pais',
            },
            'reproducciones': {'$sum': '$reproducciones'},
        }},
        {'$sort': {'_id.periodo': -1}},
    ]
    rows = list(_col('Reproduccion').aggregate(pipe))
    art_ids = [r['_id'].get('artistaId') for r in rows]
    nombres = _artistas_map(art_ids)
    discos = _discograficas_map(art_ids)
    pcts = _pct_map(art_ids)
    tarifas = _tarifas_map()
    out = []
    for r in rows:
        k = r['_id']
        aid = k.get('artistaId')
        mes, anio = _split_periodo(k.get('periodo'))
        repro = r.get('reproducciones') or 0
        tarifa = tarifas.get(k.get('pais'), DEFAULT_TARIFA)
        bruto = repro * tarifa
        pct = pcts.get(aid, 0.0)          # 0.0 si el artista no tiene discográfica
        disco = bruto * pct
        out.append({
            'MesPeriodo': mes,
            'AnioPeriodo': anio,
            'artistaId': str(aid) if aid else '',
            'BeneficiarioArtista': nombres.get(aid, '—'),
            'Discografica': discos.get(aid, 'Independiente'),
            'Pais': k.get('pais') or '—',
            'TarifaPais': tarifa,
            'TotalReproduccionesPeriodo': repro,
            'MontoBrutoTotal': bruto,
            'PagoADiscografica': disco,
            'PagoNetoArtista': bruto - disco,   # todo al artista si no hay discográfica
            'Estado': 'Pendiente',
        })
    return out


# ── Consolidado por período (cancelable) ──────────────────────────────
def _consolidado_regalias():
    """Regalías de la colección Regalias que SIGUEN pendientes de pago.
    Las ya pagadas NO se incluyen aquí (viven en el histórico)."""
    pipe = [
        {'$match': {'estadoPago': {'$ne': 'Pagado'}}},
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


def por_periodo():
    """SÓLO el saldo PENDIENTE de pago: regalías registradas aún no pagadas +
    pendientes calculadas en vivo desde reproducciones sin liquidar.
    Lo ya pagado pasa al histórico (`listar_registros`), no aparece aquí."""
    return _consolidado_regalias() + pendientes_por_reproduccion()


# ── Histórico de registros ────────────────────────────────────────────
def listar_registros(desde=None, hasta=None):
    """Histórico = regalías YA PAGADAS dentro del rango de períodos."""
    d = (desde or '0000-00')[:7]
    h = (hasta or '9999-99')[:7]
    pipe = [
        {'$match': {'periodo': {'$gte': d, '$lte': h}, 'estadoPago': 'Pagado'}},
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
def _materializar_reproducciones(periodo=None, aid=None, pais=None,
                                 periodo_desde=None, periodo_hasta=None):
    """Convierte las reproducciones SIN liquidar (de un período exacto o de un
    RANGO de períodos, y opcionalmente artista/país) en documentos Regalias ya
    PAGADOS, en UNA sola pasada de agregación. Marca esas reproducciones como
    liquidadas. Devuelve cuántos registros Regalias se crearon/actualizaron."""
    pipe = [
        {'$match': _repro_no_liquidada()},
        {'$set': {'_periodo': {'$dateToString': {'format': '%Y-%m', 'date': '$fechaHora'}}}},
    ]
    if periodo:
        pipe.append({'$match': {'_periodo': periodo}})
    elif periodo_desde or periodo_hasta:
        rng = {}
        if periodo_desde:
            rng['$gte'] = periodo_desde
        if periodo_hasta:
            rng['$lte'] = periodo_hasta
        pipe.append({'$match': {'_periodo': rng}})
    if pais:
        pipe.append({'$match': {'pais': pais}})
    # Group-first (barato) para 1 lookup por canción, luego resolvemos artista.
    pipe += [
        {'$group': {
            '_id': {'cancionId': '$cancionId', 'periodo': '$_periodo',
                    'pais': {'$ifNull': ['$pais', 'Ecuador']}},
            'reproducciones': {'$sum': 1},
            'reproIds': {'$push': '$_id'},
        }},
        {'$lookup': {'from': 'Cancion', 'localField': '_id.cancionId',
                     'foreignField': 'cancionId', 'as': '_c'}},
        {'$set': {'_c': {'$arrayElemAt': ['$_c', 0]}}},
        {'$unwind': '$_c.artistas'},
    ]
    if aid:
        pipe.append({'$match': {'_c.artistas.artistaId': aid}})
    pipe.append({'$group': {
        '_id': {'cancionId': '$_id.cancionId',
                'artistaId': '$_c.artistas.artistaId',
                'pais': '$_id.pais',
                'periodo': '$_id.periodo'},
        'reproducciones': {'$sum': '$reproducciones'},
        'reproIds': {'$first': '$reproIds'},
    }})
    grupos = list(_col('Reproduccion').aggregate(pipe))
    tarifas = _tarifas_map()
    pcts = _pct_map([g['_id'].get('artistaId') for g in grupos])
    ahora = datetime.utcnow()
    creados = 0
    for g in grupos:
        k = g['_id']
        aid2 = k.get('artistaId')
        pais = k.get('pais')
        periodo = k.get('periodo')
        repro = g.get('reproducciones') or 0
        tarifa = tarifas.get(pais, DEFAULT_TARIFA)
        bruto = round(repro * tarifa, 4)
        disco = round(bruto * pcts.get(aid2, 0.0), 4)
        neto = round(bruto - disco, 4)
        inc = {
            'cantidadReproducciones': repro,
            'montoTotalGenerado': bruto,
            'montoArtista': neto,
            'montoDiscografica': disco,
        }
        pago = {'estadoPago': 'Pagado', 'fechaPago': ahora}
        try:
            # Clave fina por canción; idempotente vía $inc + upsert.
            _col('Regalias').update_one(
                {'artistaId': aid2, 'periodo': periodo,
                 'paisReproduccion': pais, 'cancionId': k.get('cancionId')},
                {'$inc': inc, '$set': pago,
                 '$setOnInsert': {'regaliaId': ObjectId(), 'fechaCalculo': ahora}},
                upsert=True)
        except DuplicateKeyError:
            # La colección tiene índice único (paisReproduccion, periodo):
            # consolidamos en el único documento permitido de ese país/período.
            _col('Regalias').update_one(
                {'paisReproduccion': pais, 'periodo': periodo},
                {'$inc': inc, '$set': pago,
                 '$setOnInsert': {'regaliaId': ObjectId(), 'artistaId': aid2,
                                  'cancionId': k.get('cancionId'),
                                  'fechaCalculo': ahora}},
                upsert=True)
        _col('Reproduccion').update_many(
            {'_id': {'$in': g.get('reproIds') or []}},
            {'$set': {'liquidada': True, 'periodoLiquidado': periodo}})
        creados += 1
    return creados


def confirmar_periodo(mes, anio, artista_id=None, pais=None):
    """Confirma (PAGA) el saldo pendiente de regalías de un período/artista/país.
    Materializa las reproducciones sin liquidar en registros Regalias pagados
    (que pasan al histórico) y marca como pagadas las regalías que ya existían."""
    try:
        periodo = f'{int(anio):04d}-{int(mes):02d}'
    except (TypeError, ValueError):
        return 0
    aid = _oid(artista_id)
    creados = _materializar_reproducciones(periodo, aid, pais)
    filtro = {'periodo': periodo, 'estadoPago': {'$ne': 'Pagado'}}
    if aid:
        filtro['artistaId'] = aid
    if pais:
        filtro['paisReproduccion'] = pais
    res = _col('Regalias').update_many(
        filtro,
        {'$set': {'estadoPago': 'Pagado', 'fechaPago': datetime.utcnow()}})
    return creados + res.modified_count


def confirmar_rango(desde=None, hasta=None):
    """Confirma el pago de TODO el saldo pendiente (reproducciones + regalías)
    cuyo período cae en el rango indicado. Una sola pasada de materialización."""
    d = (desde or '0000-00')[:7]
    h = (hasta or '9999-99')[:7]
    creados = _materializar_reproducciones(periodo_desde=d, periodo_hasta=h)
    res = _col('Regalias').update_many(
        {'periodo': {'$gte': d, '$lte': h}, 'estadoPago': {'$ne': 'Pagado'}},
        {'$set': {'estadoPago': 'Pagado', 'fechaPago': datetime.utcnow()}})
    return creados + res.modified_count
