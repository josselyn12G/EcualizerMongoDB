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
from django.db import connection, DatabaseError

logger = logging.getLogger('ecualizer.notificaciones')


def _rows(sql, params):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _fmt(fecha):
    """Formatea una fecha a dd/mm/aaaa (igual que CONVERT(..,103) del SP)."""
    try:
        return fecha.strftime('%d/%m/%Y')
    except (AttributeError, ValueError):
        return str(fecha or '')


# ──────────────────────────────────────────────────────────
# 1) Recordatorios de renovación  (regla del SP de Pagos)
#    El SP usa exactamente "vence en 3 días"; aquí ampliamos a
#    los próximos 7 días para que el aviso sea útil cualquier día.
# ──────────────────────────────────────────────────────────
def _recordatorios_renovacion(usuario_id):
    sql = """
        SELECT
            s.idSuscripcion,
            u.alias,
            tp.nombrePlan,
            s.fechaFin,
            DATEDIFF(DAY, CAST(GETDATE() AS DATE), s.fechaFin) AS diasRestantes
        FROM Pagos.Suscripcion s
        JOIN Usuario.Usuario u  ON u.idUsuario = s.Usuario_idUsuario
        JOIN Pagos.TipoPlan tp  ON tp.idTipoPlan = s.TipoPlan_idTipoPlan
        WHERE s.Usuario_idUsuario   = %s
          AND s.renovacionAutomatica = 'S'
          AND s.estadoSuscripcion    = 'activa'
          AND s.fechaFin >= CAST(GETDATE() AS DATE)
          AND s.fechaFin <= DATEADD(DAY, 7, CAST(GETDATE() AS DATE))
        ORDER BY s.fechaFin;
    """
    notifs = []
    for r in _rows(sql, [usuario_id]):
        dias = r.get('diasRestantes') or 0
        notifs.append({
            'tipo':   'renovacion',
            'icono':  'card_membership',
            'titulo': 'Renovación de suscripción',
            'mensaje': (
                f'Hola {r["alias"]}, tu suscripción al plan "{r["nombrePlan"]}" '
                f'vence el {_fmt(r["fechaFin"])} ({dias} días). '
                f'Se renovará automáticamente. Asegúrate de tener saldo disponible.'
            ),
            'fecha':     r['fechaFin'],
            'fecha_str': _fmt(r['fechaFin']),
        })
    return notifs


# ──────────────────────────────────────────────────────────
# 2) Notificaciones de lanzamiento  (regla del SP de Biblioteca)
#    El SP usa "lanzados hoy"; aquí mostramos los lanzamientos de
#    los últimos 14 días de los artistas seguidos con avisos activos.
# ──────────────────────────────────────────────────────────
def _notificaciones_lanzamiento(usuario_id):
    sql = """
        SELECT TOP 20
            a.idAlbum,
            a.tituloAlbum,
            ar.nombreArtistico,
            a.fechaLanzamientoAlbum,
            u.alias
        FROM Catalogo.Album a
        JOIN Usuario.Artista ar          ON ar.idUsuario = a.Artista_idUsuario
        JOIN Biblioteca.UsuarioSigueArtista usa ON usa.Artista_idUsuario = ar.idUsuario
        JOIN Usuario.Usuario u           ON u.idUsuario = usa.Usuario_idUsuario
        WHERE usa.Usuario_idUsuario      = %s
          AND usa.notificacionesActivas  = 'A'
          AND a.estadoAlbum              = 'activo'
          AND a.fechaLanzamientoAlbum >= DATEADD(DAY, -14, CAST(GETDATE() AS DATE))
          AND a.fechaLanzamientoAlbum <= CAST(GETDATE() AS DATE)
        ORDER BY a.fechaLanzamientoAlbum DESC, a.idAlbum DESC;
    """
    notifs = []
    for r in _rows(sql, [usuario_id]):
        notifs.append({
            'tipo':   'lanzamiento',
            'icono':  'album',
            'titulo': f'Nuevo álbum de {r["nombreArtistico"]}',
            'mensaje': (
                f'¡Hola {r["alias"]}! {r["nombreArtistico"]} acaba de lanzar su '
                f'nuevo álbum "{r["tituloAlbum"]}" el {_fmt(r["fechaLanzamientoAlbum"])}. '
                f'¡Escúchalo ahora en Ecualizer!'
            ),
            'fecha':     r['fechaLanzamientoAlbum'],
            'fecha_str': _fmt(r['fechaLanzamientoAlbum']),
        })
    return notifs


# ──────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────
def obtener_notificaciones_oyente(usuario_id):
    """Devuelve la lista combinada de notificaciones del oyente (más recientes
    primero). Cada elemento: {tipo, icono, titulo, mensaje, fecha, fecha_str}."""
    if not usuario_id:
        return []
    try:
        notifs = _notificaciones_lanzamiento(usuario_id) + _recordatorios_renovacion(usuario_id)
    except DatabaseError as e:
        logger.error('Notificaciones oyente · error BD · %s', e)
        return []

    # Orden global por fecha descendente (los lanzamientos recientes arriba).
    notifs.sort(key=lambda n: n.get('fecha') or '', reverse=True)
    return notifs
