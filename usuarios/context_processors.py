"""Context processors globales de la app usuarios."""

from .notificaciones_service import obtener_notificaciones_oyente


def notificaciones_oyente(request):
    """Inyecta las notificaciones del oyente conectado en TODAS las plantillas
    del panel del oyente (el campanita vive en `base_oyente.html`).

    Solo consulta la BD cuando la sesión activa es de un oyente, para no
    penalizar al resto de paneles (admin / artista / login).
    """
    if request.session.get('tipo_usuario') != 'oyente':
        return {}

    uid = request.session.get('usuario_id')
    notifs = obtener_notificaciones_oyente(uid)
    return {
        'notificaciones': notifs,
        'notif_count': len(notifs),
    }
