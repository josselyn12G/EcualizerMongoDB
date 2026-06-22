"""Métricas de analítica del oyente sobre MongoDB."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from usuarios.mongo_service import get_database

logger = logging.getLogger('ecualizer.analitica')


def _db():
    return get_database()


def _oid(v):
    v = str(v) if v is not None else ''
    return ObjectId(v) if ObjectId.is_valid(v) else None


def _cutoff(periodo: str):
    now = datetime.now(timezone.utc)
    if periodo == 'semana':
        return now - timedelta(days=7)
    if periodo == 'mes':
        return now - timedelta(days=30)
    if periodo == 'año':
        return now - timedelta(days=365)
    return None


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        logger.warning('oyente_service error: %s', e)
        return default if default is not None else []


def sp_top_canciones_usuario(usuario_id, periodo: str = 'todo') -> list[dict]:
    def _q():
        oid = _oid(usuario_id)
        match = {'usuarioId': oid} if oid else {'_id': None}
        co = _cutoff(periodo)
        if co:
            match['fechaHora'] = {'$gte': co}
        pipeline = [
            {'$match': match},
            {'$group': {'_id': '$cancionId', 'Total': {'$sum': 1}}},
            {'$sort': {'Total': -1}},
            {'$limit': 10},
            {'$lookup': {
                'from': 'Cancion',
                'let': {'cid': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$or': [
                        {'$eq': ['$cancionId', '$$cid']},
                        {'$eq': ['$_id', '$$cid']},
                    ]}}},
                    {'$limit': 1},
                ],
                'as': 'c',
            }},
            {'$unwind': {'path': '$c', 'preserveNullAndEmptyArrays': True}},
            {'$project': {
                '_id': 0,
                'NombreCancion':       {'$ifNull': ['$c.tituloCancion', '—']},
                'NombreArtistico':     {'$ifNull': [{'$arrayElemAt': ['$c.artistas.nombreArtistico', 0]}, '—']},
                'TotalReproducciones': '$Total',
            }},
        ]
        return list(_db()['Reproduccion'].aggregate(pipeline))
    return _safe(_q)


def sp_top_artistas_usuario(usuario_id, periodo: str = 'todo') -> list[dict]:
    def _q():
        oid = _oid(usuario_id)
        match = {'usuarioId': oid} if oid else {'_id': None}
        co = _cutoff(periodo)
        if co:
            match['fechaHora'] = {'$gte': co}
        pipeline = [
            {'$match': match},
            {'$lookup': {
                'from': 'Cancion',
                'let': {'cid': '$cancionId'},
                'pipeline': [
                    {'$match': {'$expr': {'$or': [
                        {'$eq': ['$cancionId', '$$cid']},
                        {'$eq': ['$_id', '$$cid']},
                    ]}}},
                    {'$project': {'artistas': 1}},
                    {'$limit': 1},
                ],
                'as': 'c',
            }},
            {'$unwind': {'path': '$c', 'preserveNullAndEmptyArrays': True}},
            {'$unwind': {'path': '$c.artistas', 'preserveNullAndEmptyArrays': True}},
            {'$group': {
                '_id': '$c.artistas.nombreArtistico',
                'Total': {'$sum': 1},
            }},
            {'$sort': {'Total': -1}},
            {'$limit': 10},
            {'$project': {'_id': 0, 'NombreArtistico': '$_id', 'TotalReproducciones': '$Total'}},
        ]
        return list(_db()['Reproduccion'].aggregate(pipeline))
    return _safe(_q)


def sp_historial_reproduccion(usuario_id, fecha_inicio=None, fecha_fin=None) -> list[dict]:
    def _q():
        oid = _oid(usuario_id)
        match = {'usuarioId': oid} if oid else {'_id': None}
        if fecha_inicio:
            match.setdefault('fechaHora', {})['$gte'] = datetime.fromisoformat(str(fecha_inicio))
        if fecha_fin:
            match.setdefault('fechaHora', {})['$lte'] = datetime.fromisoformat(str(fecha_fin))
        rows = list(_db()['Reproduccion'].find(match).sort('fechaHora', -1).limit(100))
        return [{'Fecha': r.get('fechaHora'), 'CancionId': str(r.get('cancionId', ''))} for r in rows]
    return _safe(_q)


def sp_generos_favoritos_usuario(usuario_id, periodo: str = 'todo') -> list[dict]:
    def _q():
        oid = _oid(usuario_id)
        match = {'usuarioId': oid} if oid else {'_id': None}
        co = _cutoff(periodo)
        if co:
            match['fechaHora'] = {'$gte': co}
        pipeline = [
            {'$match': match},
            {'$lookup': {
                'from': 'Cancion',
                'let': {'cid': '$cancionId'},
                'pipeline': [
                    {'$match': {'$expr': {'$or': [
                        {'$eq': ['$cancionId', '$$cid']},
                        {'$eq': ['$_id', '$$cid']},
                    ]}}},
                    {'$project': {'generos': 1}},
                    {'$limit': 1},
                ],
                'as': 'c',
            }},
            {'$unwind': {'path': '$c', 'preserveNullAndEmptyArrays': True}},
            {'$unwind': {'path': '$c.generos', 'preserveNullAndEmptyArrays': True}},
            {'$group': {'_id': '$c.generos.nombreGenero', 'Total': {'$sum': 1}}},
            {'$sort': {'Total': -1}},
            {'$limit': 8},
            {'$project': {'_id': 0, 'NombreGenero': '$_id', 'TotalReproducciones': '$Total'}},
        ]
        return list(_db()['Reproduccion'].aggregate(pipeline))
    return _safe(_q)


def sp_tiempo_total_escucha(usuario_id, periodo: str = 'mes') -> list[dict]:
    def _q():
        oid = _oid(usuario_id)
        match = {'usuarioId': oid} if oid else {'_id': None}
        co = _cutoff(periodo)
        if co:
            match['fechaHora'] = {'$gte': co}
        pipeline = [
            {'$match': match},
            {'$group': {
                '_id': None,
                'TiempoTotal': {'$sum': '$duracionEscuchada'},
                'Total': {'$sum': 1},
            }},
            {'$project': {
                '_id': 0,
                'TiempoTotalSeg': '$TiempoTotal',
                'TotalReproducciones': '$Total',
            }},
        ]
        rows = list(_db()['Reproduccion'].aggregate(pipeline))
        return rows
    return _safe(_q)


def sp_recomendaciones_semanales(usuario_id) -> list[dict]:
    def _q():
        rows = list(_db()['Cancion'].find(
            {'estadoCancion': {'$ne': 'inactivo'}},
            {'tituloCancion': 1, 'artistas': 1, 'totalReproducciones': 1}
        ).sort('totalReproducciones', -1).limit(10))
        return [{
            'NombreCancion':   r.get('tituloCancion', ''),
            'NombreArtistico': (r.get('artistas') or [{}])[0].get('nombreArtistico', '—'),
        } for r in rows]
    return _safe(_q)
