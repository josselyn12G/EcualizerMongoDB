"""
Servicio de notificaciones del Oyente.

Reproduce, a nivel de un único usuario, la lógica de negocio de los dos
cursores diarios definidos en
`Scripts SQL/Reglas de Negocio/Script Cursores.sql`:

  • Pagos.SP_GenerarRecordatoriosRenovacion
        → recordatorio de renovación de suscripción próxima a vencer.
  • Biblioteca.SP_EnviarNotificacionLanzamiento
        → aviso de nuevos álbumes de los artistas que sigue el oyente.

Los SP originales son procesos batch (SQL Agent) que recorren TODOS los
usuarios y devuelven un result-set; aquí ejecutamos las MISMAS reglas pero
acotadas al oyente conectado, para alimentar el "campanita" del panel.

Es totalmente defensivo: si la BD falla, devuelve listas vacías para que el
panel siempre se renderice.
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta

logger = logging.getLogger('ecualizer.notificaciones')


def _fmt(fecha):
    """Formatea una fecha a dd/mm/aaaa."""
    try:
        return fecha.strftime('%d/%m/%Y')
    except (AttributeError, ValueError):
        return str(fecha or '')


def _a_date(value):
    """datetime / date / 'YYYY-MM-DD' / None → date | None."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


# ──────────────────────────────────────────────────────────
# 1) Recordatorios de renovación  (MongoDB)
#    Aviso cuando una suscripción activa con renovación automática está por
#    vencer (próximos 7 días). Suscripciones en la colección `Suscripcion`
#    con `plan` embebido y `renovacionAutomatica` booleano.
# ──────────────────────────────────────────────────────────
def _recordatorios_renovacion(usuario_id):
    from bson import ObjectId
    from usuarios.mongo_service import get_database

    oid = ObjectId(str(usuario_id)) if ObjectId.is_valid(str(usuario_id)) else None
    if not oid:
        return []
    db = get_database()
    user = db['Usuarios'].find_one(
        {'$or': [{'_id': oid}, {'usuarioId': oid}]},
        {'perfilOyente.alias': 1, 'primerNombre': 1})
    alias = (((user or {}).get('perfilOyente') or {}).get('alias')
             or (user or {}).get('primerNombre') or 'oyente')

    hoy = date.today()
    limite = hoy + timedelta(days=7)
    notifs = []
    for s in db['Suscripcion'].find({'usuarioId': oid, 'estadoSuscripcion': 'activa'}):
        if not s.get('renovacionAutomatica'):
            continue
        fin = _a_date(s.get('fechaFin'))
        if not fin or not (hoy <= fin <= limite):
            continue
        dias = (fin - hoy).days
        plan = (s.get('plan') or {}).get('nombrePlan') or 'tu plan'
        notifs.append({
            'tipo':   'renovacion',
            'icono':  'card_membership',
            'titulo': 'Renovación de suscripción',
            'mensaje': (
                f'Hola {alias}, tu suscripción al plan "{plan}" '
                f'vence el {_fmt(fin)} ({dias} días). '
                f'Se renovará automáticamente. Asegúrate de tener saldo disponible.'
            ),
            'fecha':     fin,
            'fecha_str': _fmt(fin),
        })
    return notifs


# ──────────────────────────────────────────────────────────
# 2) Notificaciones de lanzamiento  (MongoDB)
#    Avisa de los álbumes recientes (últimos 30 días) publicados por los
#    artistas que el oyente sigue con notificaciones activas. Los follows
#    están embebidos en Usuarios.perfilOyente.artistasSeguidos.
# ──────────────────────────────────────────────────────────
def _notificaciones_lanzamiento(usuario_id):
    from datetime import datetime, timedelta, timezone
    from bson import ObjectId
    from usuarios.mongo_service import get_database

    oid = ObjectId(str(usuario_id)) if ObjectId.is_valid(str(usuario_id)) else None
    if not oid:
        return []
    db = get_database()
    user = db['Usuarios'].find_one(
        {'$or': [{'_id': oid}, {'usuarioId': oid}]},
        {'perfilOyente': 1, 'primerNombre': 1})
    if not user:
        return []

    oyente = user.get('perfilOyente') or {}
    seguidos = oyente.get('artistasSeguidos') or []
    art_ids = [s.get('artistaId') for s in seguidos
               if s.get('artistaId') and s.get('notificacionesActivas', 'A') != 'D']
    if not art_ids:
        return []

    # Un artista puede estar referenciado por su `_id` o por su `usuarioId`,
    # y los álbumes pueden guardar cualquiera de los dos. Expandimos el set de
    # ids del artista para que el match con Albums.artistaId sea robusto.
    ids_expandidos = set(art_ids)
    for u in db['Usuarios'].find(
            {'$or': [{'_id': {'$in': art_ids}}, {'usuarioId': {'$in': art_ids}}]},
            {'_id': 1, 'usuarioId': 1}):
        ids_expandidos.add(u['_id'])
        if u.get('usuarioId') is not None:
            ids_expandidos.add(u['usuarioId'])

    alias = oyente.get('alias') or user.get('primerNombre') or 'oyente'
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    notifs = []
    cursor = db['Albums'].find({
        'artistaId': {'$in': list(ids_expandidos)},
        'estadoAlbum': 'activo',
    }).sort('fechaCreacion', -1).limit(40)
    for a in cursor:
        # Un álbum es "novedad" si se creó (o se lanzó) en los últimos 30 días.
        fecha_ref = a.get('fechaCreacion') or a.get('fechaLanzamiento')
        if isinstance(fecha_ref, datetime):
            ref = fecha_ref if fecha_ref.tzinfo else fecha_ref.replace(tzinfo=timezone.utc)
            if ref < cutoff:
                continue
        nombre_art = a.get('nombreArtistico') or 'Un artista'
        titulo = a.get('tituloAlbum') or 'nuevo álbum'
        fecha_show = a.get('fechaLanzamiento') or a.get('fechaCreacion')
        notifs.append({
            'tipo':   'lanzamiento',
            'icono':  'album',
            'titulo': f'Nuevo álbum de {nombre_art}',
            'mensaje': (
                f'¡Hola {alias}! {nombre_art} acaba de publicar su nuevo álbum '
                f'"{titulo}". ¡Escúchalo ahora en Ecualizer!'
            ),
            'fecha':     fecha_show,
            'fecha_str': _fmt(fecha_show),
        })
        if len(notifs) >= 20:
            break
    return notifs


# ──────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────
def obtener_notificaciones_oyente(usuario_id):
    """Devuelve la lista combinada de notificaciones del oyente (más recientes
    primero). Cada elemento: {tipo, icono, titulo, mensaje, fecha, fecha_str}."""
    if not usuario_id:
        return []
    notifs = []
    # Lanzamientos de álbumes (MongoDB) — defensivo e independiente.
    try:
        notifs += _notificaciones_lanzamiento(usuario_id)
    except Exception as e:
        logger.error('Notificaciones lanzamiento · error · %s', e)
    # Recordatorios de renovación (SQL legacy) — solo si sigue disponible.
    try:
        notifs += _recordatorios_renovacion(usuario_id)
    except Exception as e:  # noqa: BLE001  (BD SQL legacy puede no existir)
        logger.warning('Notificaciones renovación no disponibles · %s', e)

    def _key(n):
        f = n.get('fecha')
        try:
            return f.isoformat()
        except AttributeError:
            return str(f or '')
    notifs.sort(key=_key, reverse=True)
    return notifs
