from django.db import connection


def _fetch(sql, params):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def sp_top_canciones_usuario(usuario_id, periodo='todo'):
    return _fetch(
        "EXEC Analitica.sp_TopCancionesUsuario @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_top_artistas_usuario(usuario_id, periodo='todo'):
    return _fetch(
        "EXEC Analitica.sp_TopArtistasUsuario @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_historial_reproduccion(usuario_id, fecha_inicio=None, fecha_fin=None):
    return _fetch(
        "EXEC Analitica.sp_HistorialReproduccionUsuario "
        "@idUsuario=%s, @fechaInicio=%s, @fechaFin=%s;",
        [usuario_id, fecha_inicio, fecha_fin]
    )


def sp_generos_favoritos_usuario(usuario_id, periodo='todo'):
    return _fetch(
        "EXEC Analitica.sp_GenerosFavoritosUsuario @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_tiempo_total_escucha(usuario_id, periodo='mes'):
    return _fetch(
        "EXEC Analitica.sp_TiempoTotalEscucha @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_recomendaciones_semanales(usuario_id):
    return _fetch(
        "EXEC Analitica.sp_RecomendacionesSemanales @idUsuario=%s;",
        [usuario_id]
    )