# analitica/services/oyente_service.py
from __future__ import annotations
from .admin_service import _exec_rows


def sp_top_canciones_usuario(usuario_id: int, periodo: str = 'todo') -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_TopCancionesUsuario @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_top_artistas_usuario(usuario_id: int, periodo: str = 'todo') -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_TopArtistasUsuario @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_historial_reproduccion(usuario_id: int, fecha_inicio=None, fecha_fin=None) -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_HistorialReproduccionUsuario "
        "@idUsuario=%s, @fechaInicio=%s, @fechaFin=%s;",
        [usuario_id, fecha_inicio, fecha_fin]
    )


def sp_generos_favoritos_usuario(usuario_id: int, periodo: str = 'todo') -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_GenerosFavoritosUsuario @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_tiempo_total_escucha(usuario_id: int, periodo: str = 'mes') -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_TiempoTotalEscucha @idUsuario=%s, @periodo=%s;",
        [usuario_id, periodo]
    )


def sp_recomendaciones_semanales(usuario_id: int) -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_RecomendacionesSemanales @idUsuario=%s;",
        [usuario_id]
    )