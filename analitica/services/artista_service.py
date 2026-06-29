"""
Métricas de analítica del artista sobre MongoDB.

Mantiene las mismas firmas que usaban los SPs originales para no tocar las vistas.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from usuarios.mongo_service import get_database

logger = logging.getLogger('ecualizer.analitica')

PERIODOS_VALIDOS = ('semana', 'mes', 'año', 'todo')


def _db():
    return get_database()


def _oid(v):
    v = str(v) if v is not None else ''
    return ObjectId(v) if ObjectId.is_valid(v) else None


def _artista_ids(id_artista):
    """Devuelve el set de _id / usuarioId del artista para filtrar canciones."""
    oid = _oid(id_artista)
    filtro = {'$or': [{'_id': oid}, {'usuarioId': oid}]} if oid else {}
    doc = _db()['Usuarios'].find_one(filtro, {'_id': 1, 'usuarioId': 1}) if filtro else None
    if not doc:
        return set()
    return {doc['_id'], doc.get('usuarioId')} - {None}


def _cutoff(periodo: str):
    now = datetime.now(timezone.utc)
    if periodo == 'semana':
        return now - timedelta(days=7)
    if periodo == 'mes':
        return now - timedelta(days=30)
    if periodo == 'año':
        return now - timedelta(days=365)
    return None  # 'todo'


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        logger.warning('artista_service error: %s', e)
        return default if default is not None else []


# ══════════════════════════════════════════════════════════════════════
# Canciones del artista  (mapa cancionId-campo → título + álbum)
#
# OJO: en los datos, Reproduccion.cancionId referencia el CAMPO `cancionId`
# de Cancion (no su _id). Por eso todos los joins de analítica usan ese campo.
# ══════════════════════════════════════════════════════════════════════
def _artista_canciones(id_artista, id_album=None) -> dict:
    ids = _artista_ids(id_artista)
    if not ids:
        return {}
    filtro = {'artistas.artistaId': {'$in': list(ids)}}
    if id_album:
        filtro['albumId'] = _oid(id_album)
    cans = list(_db()['Cancion'].find(
        filtro, {'cancionId': 1, 'tituloCancion': 1, 'albumId': 1}))
    album_ids = list({c.get('albumId') for c in cans if c.get('albumId')})
    titulos_album = {
        a.get('albumId'): a.get('tituloAlbum')
        for a in _db()['Albums'].find(
            {'albumId': {'$in': album_ids}}, {'albumId': 1, 'tituloAlbum': 1})
    }
    salida = {}
    for c in cans:
        key = c.get('cancionId') or c['_id']
        salida[key] = {
            'titulo': c.get('tituloCancion', '') or '—',
            'album':  titulos_album.get(c.get('albumId')) or '—',
        }
    return salida


# ══════════════════════════════════════════════════════════════════════
# REPRODUCCIONES POR CANCIÓN  (cuenta eventos reales en Reproduccion)
# ══════════════════════════════════════════════════════════════════════
def reproducciones_por_cancion(id_artista, id_album=None, periodo: str = 'todo') -> list[dict]:
    def _q():
        canmap = _artista_canciones(id_artista, id_album)
        if not canmap:
            return []
        match = {'cancionId': {'$in': list(canmap.keys())}}
        co = _cutoff(periodo)
        if co:
            match['fechaHora'] = {'$gte': co}
        rows = _db()['Reproduccion'].aggregate([
            {'$match': match},
            {'$group': {
                '_id': '$cancionId',
                'TotalReproducciones': {'$sum': 1},
                'oyentes': {'$addToSet': '$usuarioId'},
            }},
            {'$sort': {'TotalReproducciones': -1}},
        ])
        salida = []
        for r in rows:
            info = canmap.get(r['_id'], {})
            salida.append({
                'Cancion':             info.get('titulo', '—'),
                'Album':               info.get('album', '—'),
                'TotalReproducciones': r['TotalReproducciones'],
                'OyentesUnicos':       len(r.get('oyentes') or []),
            })
        return salida
    return _safe(_q)


# ══════════════════════════════════════════════════════════════════════
# TOP 10 CANCIONES  (por reproducciones reales del periodo)
# ══════════════════════════════════════════════════════════════════════
def top10_canciones(id_artista, periodo: str = 'mes') -> list[dict]:
    return reproducciones_por_cancion(id_artista, None, periodo)[:10]


# ══════════════════════════════════════════════════════════════════════
# OYENTES MENSUALES (crecimiento)
# ══════════════════════════════════════════════════════════════════════
def oyentes_mensuales_crecimiento(id_artista, mes: int, anio: int) -> dict:
    def _q():
        canciones_ids = list(_artista_canciones(id_artista).keys())
        if not canciones_ids:
            return {'OyentesUnicosMes': 0, 'OyentesUnicosMesAnterior': 0, 'PorcentajeCrecimiento': 0,
                    'PeriodoConsultado': f'{anio}-{mes:02d}'}

        inicio_mes = datetime(anio, mes, 1, tzinfo=timezone.utc)
        if mes == 12:
            inicio_sig = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
        else:
            inicio_sig = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)

        mes_ant = mes - 1 if mes > 1 else 12
        anio_ant = anio if mes > 1 else anio - 1
        inicio_ant = datetime(anio_ant, mes_ant, 1, tzinfo=timezone.utc)

        def _oyentes_unicos(desde, hasta):
            cur = _db()['Reproduccion'].aggregate([
                {'$match': {'cancionId': {'$in': canciones_ids}, 'fechaHora': {'$gte': desde, '$lt': hasta}}},
                {'$group': {'_id': '$usuarioId'}},
                {'$count': 'total'},
            ])
            r = list(cur)
            return r[0]['total'] if r else 0

        actual   = _oyentes_unicos(inicio_mes, inicio_sig)
        anterior = _oyentes_unicos(inicio_ant, inicio_mes)
        pct = ((actual - anterior) / anterior * 100) if anterior else 0

        return {
            'OyentesUnicosMes':       actual,
            'OyentesUnicosMesAnterior': anterior,
            'PorcentajeCrecimiento':  round(pct, 1),
            'PeriodoConsultado':       f'{anio}-{mes:02d}',
        }
    return _safe(_q, {})


# ══════════════════════════════════════════════════════════════════════
# DISTRIBUCIÓN GEOGRÁFICA
# ══════════════════════════════════════════════════════════════════════
def distribucion_geografica(id_artista, periodo: str = 'todo') -> list[dict]:
    def _q():
        canciones_ids = list(_artista_canciones(id_artista).keys())
        if not canciones_ids:
            return []
        match = {'cancionId': {'$in': canciones_ids}}
        co = _cutoff(periodo)
        if co:
            match['fechaHora'] = {'$gte': co}
        rows = list(_db()['Reproduccion'].aggregate([
            {'$match': match},
            {'$group': {'_id': '$pais', 'Total': {'$sum': 1}}},
            {'$sort': {'Total': -1}},
            {'$limit': 20},
        ]))
        total = sum(r['Total'] for r in rows) or 1
        return [{
            'Pais':                r['_id'] or 'Desconocido',
            'TotalReproducciones': r['Total'],
            'Porcentaje':          round(r['Total'] / total * 100, 1),
        } for r in rows]
    return _safe(_q)


# ══════════════════════════════════════════════════════════════════════
# REGALÍAS DEL ARTISTA (pre-cierre)
# ══════════════════════════════════════════════════════════════════════
def regalias_artista(id_artista, fecha_inicio: str, fecha_fin: str,
                     valor_por_reproduccion: float = 0.004) -> list[dict]:
    from . import regalias_mongo
    return _safe(lambda: regalias_mongo.pendiente_regalias(
        id_artista, fecha_inicio, fecha_fin, valor_por_reproduccion))


def historial_regalias_artista(id_artista, desde=None, hasta=None) -> list[dict]:
    from . import regalias_mongo
    desde = desde or '2020-01-01'
    hasta = hasta or datetime.now(timezone.utc).date().isoformat()
    return _safe(lambda: regalias_mongo.historial_regalias(id_artista, desde, hasta))


def resumen_mensual_regalias_artista(id_artista, meses: int = 12) -> list[dict]:
    from . import regalias_mongo
    return _safe(lambda: regalias_mongo.evolucion_regalias(id_artista, meses))
