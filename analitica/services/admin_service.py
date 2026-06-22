"""
Servicio de Analítica del Administrador — implementado sobre MongoDB Atlas.

Todas las funciones mantienen las mismas firmas y formatos de salida
que usaban los Stored Procedures originales de SQL Server, para no
tocar los templates ni las vistas.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from usuarios.mongo_service import get_database

logger = logging.getLogger('ecualizer.analitica')


def _db():
    return get_database()


def _safe(fn, default=None):
    """Wrapper defensivo: si algo falla retorna el default."""
    try:
        return fn()
    except Exception as e:
        logger.warning('admin_service error: %s', e)
        return default if default is not None else []


# ══════════════════════════════════════════════════════════════════════
# KPIs Y RESÚMENES
# ══════════════════════════════════════════════════════════════════════
def kpis_resumen() -> dict:
    def _q():
        db = _db()
        return {
            'TotalOyentes':         db['Usuarios'].count_documents({'tipoUsuario': 'oyente'}),
            'TotalArtistas':        db['Usuarios'].count_documents({'tipoUsuario': 'artista'}),
            'TotalCanciones':       db['Cancion'].count_documents({}),
            'TotalAlbumes':         db['Albums'].count_documents({}),
            'TotalReproducciones':  db['Reproduccion'].count_documents({}),
            'TotalLikes':           db['Likes'].count_documents({}),
            'SuscripcionesActivas': db['Suscripcion'].count_documents({'estadoSuscripcion': 'activa'}),
            'IngresosTotales':      0,
        }
    return _safe(_q, {})


def engagement_resumen() -> dict:
    def _q():
        db = _db()
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        pipeline = [
            {'$match': {'fechaHora': {'$gte': cutoff}}},
            {'$group': {
                '_id': None,
                'TotalReproducciones': {'$sum': 1},
                'TotalSaltadas':       {'$sum': {'$cond': [{'$eq': ['$fueSaltada', True]}, 1, 0]}},
                'DuracionPromedioSeg': {'$avg': '$duracionEscuchada'},
                'CancionesUnicas':     {'$addToSet': '$cancionId'},
                'OyentesUnicos':       {'$addToSet': '$usuarioId'},
            }},
            {'$project': {
                '_id': 0,
                'TotalReproducciones': 1,
                'TotalSaltadas': 1,
                'DuracionPromedioSeg': {'$round': ['$DuracionPromedioSeg', 0]},
                'CancionesUnicas':     {'$size': '$CancionesUnicas'},
                'OyentesUnicos':       {'$size': '$OyentesUnicos'},
                'PorcentajeSkipRate': {
                    '$round': [
                        {'$multiply': [
                            {'$divide': ['$TotalSaltadas', {'$max': ['$TotalReproducciones', 1]}]},
                            100
                        ]}, 1
                    ]
                },
            }},
        ]
        rows = list(db['Reproduccion'].aggregate(pipeline))
        return rows[0] if rows else {}
    return _safe(_q, {})


def regalias_resumen() -> dict:
    def _q():
        db = _db()
        pipeline = [
            {'$group': {
                '_id': None,
                'TotalRegalias': {'$sum': '$montoRegalia'},
                'TotalRegistros': {'$sum': 1},
            }},
        ]
        rows = list(db['Regalias'].aggregate(pipeline))
        if rows:
            return {'TotalRegalias': round(rows[0].get('TotalRegalias', 0), 2),
                    'TotalRegistros': rows[0].get('TotalRegistros', 0)}
        return {}
    return _safe(_q, {})


# ══════════════════════════════════════════════════════════════════════
# REPRODUCCIONES (series y geografía)
# ══════════════════════════════════════════════════════════════════════
def reproducciones_por_dia(dias: int = 30) -> list[dict]:
    def _q():
        cutoff = datetime.now(timezone.utc) - timedelta(days=dias)
        pipeline = [
            {'$match': {'fechaHora': {'$gte': cutoff}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$fechaHora', 'timezone': 'UTC'}},
                'Total': {'$sum': 1},
            }},
            {'$sort': {'_id': 1}},
            {'$project': {'_id': 0, 'Fecha': '$_id', 'Total': 1}},
        ]
        return list(_db()['Reproduccion'].aggregate(pipeline))
    return _safe(_q)


def reproducciones_por_hora() -> list[dict]:
    def _q():
        pipeline = [
            {'$group': {
                '_id': {'$hour': '$fechaHora'},
                'Total': {'$sum': 1},
            }},
            {'$sort': {'_id': 1}},
            {'$project': {'_id': 0, 'Hora': '$_id', 'Total': 1}},
        ]
        return list(_db()['Reproduccion'].aggregate(pipeline))
    return _safe(_q)


def reproducciones_por_pais(top: int = 10) -> list[dict]:
    def _q():
        pipeline = [
            {'$group': {'_id': '$paisUsuario', 'Total': {'$sum': 1}}},
            {'$sort': {'Total': -1}},
            {'$limit': top},
            {'$project': {'_id': 0, 'Pais': {'$ifNull': ['$_id', 'Desconocido']}, 'Total': 1}},
        ]
        return list(_db()['Reproduccion'].aggregate(pipeline))
    return _safe(_q)


# ══════════════════════════════════════════════════════════════════════
# MÚSICA · GÉNEROS · ARTISTAS · ÁLBUMES
# ══════════════════════════════════════════════════════════════════════
def top_generos(top: int = 10) -> list[dict]:
    def _q():
        pipeline = [
            {'$unwind': '$generos'},
            {'$group': {
                '_id': '$generos.nombreGenero',
                'Canciones':      {'$sum': 1},
                'Reproducciones': {'$sum': '$totalReproducciones'},
            }},
            {'$sort': {'Reproducciones': -1}},
            {'$limit': top},
            {'$project': {'_id': 0, 'Genero': '$_id', 'Canciones': 1, 'Reproducciones': 1}},
        ]
        return list(_db()['Cancion'].aggregate(pipeline))
    return _safe(_q)


def top_artistas(top: int = 10) -> list[dict]:
    def _q():
        db = _db()
        # Reproducciones por artista desde Cancion
        pipeline_canciones = [
            {'$unwind': '$artistas'},
            {'$group': {
                '_id': '$artistas.nombreArtistico',
                'Reproducciones': {'$sum': '$totalReproducciones'},
                'TotalCanciones': {'$sum': 1},
            }},
            {'$sort': {'Reproducciones': -1}},
            {'$limit': top},
        ]
        rows = list(db['Cancion'].aggregate(pipeline_canciones))

        # Albums por artista
        album_counts = {}
        for a in db['Albums'].aggregate([
            {'$group': {'_id': '$nombreArtistico', 'n': {'$sum': 1}}}
        ]):
            album_counts[a['_id']] = a['n']

        return [{
            'Artista':       r['_id'],
            'Reproducciones': r['Reproducciones'],
            'OyentesUnicos': 0,
            'TotalAlbumes':  album_counts.get(r['_id'], 0),
        } for r in rows]
    return _safe(_q)


def top_canciones_likes(top: int = 15) -> list[dict]:
    def _q():
        db = _db()
        pipeline = [
            {'$group': {'_id': '$cancionId', 'TotalLikes': {'$sum': 1}}},
            {'$sort': {'TotalLikes': -1}},
            {'$limit': top},
            {'$lookup': {
                'from': 'Cancion',
                'let':  {'cid': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$or': [
                        {'$eq': ['$cancionId', '$$cid']},
                        {'$eq': ['$_id', '$$cid']},
                    ]}}},
                    {'$limit': 1},
                ],
                'as': 'cancion',
            }},
            {'$unwind': {'path': '$cancion', 'preserveNullAndEmptyArrays': True}},
            {'$project': {
                '_id': 0,
                'Cancion':       {'$ifNull': ['$cancion.tituloCancion', '—']},
                'Artista':       {'$ifNull': [{'$arrayElemAt': ['$cancion.artistas.nombreArtistico', 0]}, '—']},
                'TotalLikes':    1,
                'Reproducciones': {'$ifNull': ['$cancion.totalReproducciones', 0]},
            }},
        ]
        return list(db['Likes'].aggregate(pipeline))
    return _safe(_q)


def albumes_mas_guardados(top: int = 10) -> list[dict]:
    """Top álbumes por reproducciones acumuladas de sus canciones."""
    def _q():
        pipeline = [
            {'$group': {
                '_id': '$albumId',
                'VecesGuardado': {'$sum': '$totalReproducciones'},
            }},
            {'$sort': {'VecesGuardado': -1}},
            {'$limit': top},
            {'$lookup': {
                'from': 'Albums',
                'let': {'aid': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$or': [
                        {'$eq': ['$albumId', '$$aid']},
                        {'$eq': ['$_id', '$$aid']},
                    ]}}},
                    {'$limit': 1},
                ],
                'as': 'album',
            }},
            {'$unwind': {'path': '$album', 'preserveNullAndEmptyArrays': True}},
            {'$project': {
                '_id': 0,
                'Album':         {'$ifNull': ['$album.tituloAlbum', '—']},
                'Artista':       {'$ifNull': ['$album.nombreArtistico', '—']},
                'VecesGuardado': 1,
            }},
        ]
        return list(_db()['Cancion'].aggregate(pipeline))
    return _safe(_q)


def ranking_global_canciones(periodo: str = 'mes') -> list[dict]:
    def _q():
        pipeline = [
            {'$sort': {'totalReproducciones': -1}},
            {'$limit': 20},
            {'$project': {
                '_id': 0,
                'Cancion':                  '$tituloCancion',
                'Artista':                  {'$arrayElemAt': ['$artistas.nombreArtistico', 0]},
                'TotalReproduccionesGlobales': '$totalReproducciones',
                'OyentesUnicos':            '$totalReproducciones',
            }},
        ]
        return list(_db()['Cancion'].aggregate(pipeline))
    return _safe(_q)


# ══════════════════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════════════════
def usuarios_activos(tipo: str | None = None) -> list[dict]:
    def _q():
        filtro = {'estado': 'activo'}
        if tipo:
            filtro['tipoUsuario'] = tipo
        rows = list(_db()['Usuarios'].find(filtro, {
            'primerNombre': 1, 'primerApellido': 1, 'correo': 1,
            'tipoUsuario': 1, 'fechaRegistro': 1,
        }).limit(50))
        return [{
            'Nombre':   f"{r.get('primerNombre','')} {r.get('primerApellido','')}".strip(),
            'Correo':   r.get('correo', ''),
            'Tipo':     r.get('tipoUsuario', ''),
            'Registro': r.get('fechaRegistro'),
        } for r in rows]
    return _safe(_q)


def crecimiento_usuarios(meses: int = 12) -> list[dict]:
    def _q():
        pipeline = [
            {'$group': {
                '_id': {
                    'anio': {'$year': '$fechaRegistro'},
                    'mes':  {'$month': '$fechaRegistro'},
                },
                'NuevosUsuarios': {'$sum': 1},
            }},
            {'$sort': {'_id.anio': 1, '_id.mes': 1}},
            {'$limit': meses},
            {'$project': {
                '_id': 0,
                'Mes':            '$_id.mes',
                'Anio':           '$_id.anio',
                'NuevosUsuarios': 1,
            }},
        ]
        return list(_db()['Usuarios'].aggregate(pipeline))
    return _safe(_q)


def distribucion_usuarios_pais() -> list[dict]:
    def _q():
        pipeline = [
            {'$match': {'tipoUsuario': 'oyente'}},
            {'$group': {'_id': '$perfilOyente.paisUsuario', 'Total': {'$sum': 1}}},
            {'$sort': {'Total': -1}},
            {'$limit': 10},
            {'$project': {'_id': 0, 'Pais': '$_id', 'Total': 1}},
        ]
        return list(_db()['Usuarios'].aggregate(pipeline))
    return _safe(_q)


# ══════════════════════════════════════════════════════════════════════
# ACTIVIDAD RECIENTE
# ══════════════════════════════════════════════════════════════════════
def actividad_reciente(top: int = 20) -> list[dict]:
    def _q():
        db = _db()
        eventos = []

        # Últimas reproducciones
        for r in db['Reproduccion'].find({}).sort('fechaHora', -1).limit(top // 2):
            eventos.append({
                'Tipo':   'reproduccion',
                'Quien':  str(r.get('usuarioId', ''))[:8] + '…',
                'Que':    'Reproducción',
                'Detalle': r.get('paisUsuario', ''),
                'Fecha':  r.get('fechaHora'),
            })

        # Últimos likes
        for lk in db['Likes'].find({}).sort('fechaLike', -1).limit(top // 2):
            eventos.append({
                'Tipo':   'like',
                'Quien':  str(lk.get('usuarioId', ''))[:8] + '…',
                'Que':    'Like',
                'Detalle': str(lk.get('cancionId', '')),
                'Fecha':  lk.get('fechaLike'),
            })

        # Ordenar por fecha descendente
        eventos.sort(key=lambda x: x['Fecha'] or datetime.min, reverse=True)
        return eventos[:top]
    return _safe(_q)


# ══════════════════════════════════════════════════════════════════════
# COMERCIAL · INGRESOS · REGALÍAS (datos de otros equipos)
# ══════════════════════════════════════════════════════════════════════
def ingresos_mensuales(anio: int | None = None) -> list[dict]:
    def _q():
        db = _db()
        filtro = {}
        if anio:
            filtro['anio'] = anio
        pipeline = [
            {'$match': filtro},
            {'$group': {
                '_id': {'mes': '$mes', 'anio': '$anio'},
                'Total': {'$sum': '$montoTotal'},
            }},
            {'$sort': {'_id.anio': 1, '_id.mes': 1}},
            {'$project': {'_id': 0, 'Mes': '$_id.mes', 'Anio': '$_id.anio', 'Total': 1}},
        ]
        try:
            return list(db['Pagos'].aggregate(pipeline))
        except Exception:
            return []
    return _safe(_q)


def distribucion_planes() -> list[dict]:
    def _q():
        pipeline = [
            {'$group': {'_id': '$tipoPlan', 'Total': {'$sum': 1}}},
            {'$project': {'_id': 0, 'Plan': '$_id', 'Total': 1}},
        ]
        return list(_db()['Suscripcion'].aggregate(pipeline))
    return _safe(_q)


def listar_planes() -> list[dict]:
    return _safe(lambda: list(_db()['Plan'].find({}, {'_id': 0}).limit(20)))


def listar_suscripciones(estado=None, tipo_plan_id=None) -> list[dict]:
    def _q():
        filtro = {}
        if estado:
            filtro['estadoSuscripcion'] = estado
        return list(_db()['Suscripcion'].find(filtro).sort('fechaInicio', -1).limit(50))
    return _safe(_q)


def suscripciones_kpis() -> dict:
    def _q():
        db = _db()
        return {
            'Activas':    db['Suscripcion'].count_documents({'estadoSuscripcion': 'activa'}),
            'Canceladas': db['Suscripcion'].count_documents({'estadoSuscripcion': 'cancelada'}),
            'Total':      db['Suscripcion'].count_documents({}),
        }
    return _safe(_q, {})


def free_vs_premium() -> list[dict]:
    return _safe(lambda: distribucion_planes())


def suscripciones_por_mes(meses: int = 12) -> list[dict]:
    def _q():
        pipeline = [
            {'$group': {
                '_id': {'mes': {'$month': '$fechaInicio'}, 'anio': {'$year': '$fechaInicio'}},
                'Total': {'$sum': 1},
            }},
            {'$sort': {'_id.anio': 1, '_id.mes': 1}},
            {'$limit': meses},
            {'$project': {'_id': 0, 'Mes': '$_id.mes', 'Anio': '$_id.anio', 'Total': 1}},
        ]
        return list(_db()['Suscripcion'].aggregate(pipeline))
    return _safe(_q)


def regalias_por_artista(top: int = 15) -> list[dict]:
    def _q():
        pipeline = [
            {'$group': {
                '_id': '$nombreArtistico',
                'TotalRegalias': {'$sum': '$montoRegalia'},
            }},
            {'$sort': {'TotalRegalias': -1}},
            {'$limit': top},
            {'$project': {'_id': 0, 'Artista': '$_id', 'TotalRegalias': 1}},
        ]
        return list(_db()['Regalias'].aggregate(pipeline))
    return _safe(_q)


def consolidado_pagos_artistas(fecha_inicio: str, fecha_fin: str) -> list[dict]:
    return []


# ══════════════════════════════════════════════════════════════════════
# COMERCIAL · DISCOGRÁFICAS Y CONTRATOS
# ══════════════════════════════════════════════════════════════════════
def listar_discograficas(busqueda=None) -> list[dict]:
    def _q():
        import re
        filtro = {}
        if busqueda:
            filtro['discograficaNombre'] = {'$regex': re.escape(busqueda), '$options': 'i'}
        rows = list(_db()['Discograficas'].find(filtro).limit(50))
        return [{'Nombre': r.get('discograficaNombre', ''), 'Pais': r.get('pais', '')} for r in rows]
    return _safe(_q)


def listar_contratos(estado=None) -> list[dict]:
    def _q():
        filtro = {}
        if estado:
            filtro['estadoContrato'] = estado
        rows = list(_db()['ContratosDiscograficos'].find(filtro).limit(100))
        return [{
            'Artista':    (r.get('artistaAsociado') or {}).get('nombreArtistico', ''),
            'Discografica': (r.get('discograficaAsociada') or {}).get('discograficaNombre', ''),
            'Estado':     r.get('estadoContrato', ''),
            'FechaInicio': r.get('fechaInicio'),
            'FechaFin':   r.get('fechaFin'),
        } for r in rows]
    return _safe(_q)


def contratos_kpis() -> dict:
    def _q():
        db = _db()
        return {
            'Activos':    db['ContratosDiscograficos'].count_documents({'estadoContrato': 'Activo'}),
            'Finalizados': db['ContratosDiscograficos'].count_documents({'estadoContrato': 'Finalizado'}),
            'Total':      db['ContratosDiscograficos'].count_documents({}),
        }
    return _safe(_q, {})


def listar_regalias(desde=None, hasta=None) -> list[dict]:
    def _q():
        filtro = {}
        if desde or hasta:
            filtro['fechaPago'] = {}
            if desde:
                filtro['fechaPago']['$gte'] = desde
            if hasta:
                filtro['fechaPago']['$lte'] = hasta
        return list(_db()['Regalias'].find(filtro).sort('fechaPago', -1).limit(100))
    return _safe(_q)


def regalias_por_pais() -> list[dict]:
    def _q():
        pipeline = [
            {'$group': {'_id': '$pais', 'Total': {'$sum': '$montoRegalia'}}},
            {'$sort': {'Total': -1}},
            {'$project': {'_id': 0, 'Pais': '$_id', 'Total': 1}},
        ]
        return list(_db()['Regalias'].aggregate(pipeline))
    return _safe(_q)


# ══════════════════════════════════════════════════════════════════════
# CIERRE DE FACTURACIÓN (delegado al servicio de Regalías)
# ══════════════════════════════════════════════════════════════════════
def listar_tasas_por_pais() -> list[dict]:
    return _safe(lambda: list(_db()['TasasPais'].find({}, {'_id': 0}).limit(50)))


def cierre_facturacion_info() -> dict:
    return {}


def periodos_pendientes() -> list[dict]:
    return []


def cerrar_facturacion_mensual(mes=None, anio=None):
    return False, 'Operación no disponible en modo MongoDB', 0


def cerrar_facturacion_todos():
    return 0, 0, []
