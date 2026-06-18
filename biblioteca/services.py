"""
Servicios de la app `biblioteca` — favoritos / sociales.

Cada función `toggle_*` revisa si la relación ya existe antes de insertar.
- Si existe → la elimina (estado pasa a OFF).
- Si no existe → la inserta (estado pasa a ON).
Devuelven `True` cuando queda ACTIVA, `False` cuando queda inactiva.

Las consultas usan SQL crudo porque las tablas [Biblioteca].[X] tienen PK
COMPUESTA y Django ORM no maneja bien ese caso sin migraciones explícitas.
Todas las tablas tienen UNIQUE garantizado en BD, por lo que no es posible
crear duplicados aunque dos requests lleguen a la vez (la BD rechazaría).
"""

from __future__ import annotations

from django.db import connection, transaction


# ──────────────────────────────────────────────────────────
# Helpers SQL
# ──────────────────────────────────────────────────────────
def _exists(sql: str, params: tuple) -> bool:
    with connection.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return bool(row and row[0])


def _execute(sql: str, params: tuple) -> None:
    with connection.cursor() as cur:
        cur.execute(sql, params)


# ──────────────────────────────────────────────────────────
# LIKES de canciones
# ──────────────────────────────────────────────────────────
def is_cancion_liked(usuario_id: int, cancion_id: int) -> bool:
    return _exists(
        "SELECT 1 FROM [Biblioteca].[UsuarioCancionLike] "
        "WHERE Usuario_idUsuario = %s AND Cancion_idCancion = %s",
        (usuario_id, cancion_id),
    )


@transaction.atomic
def toggle_like_cancion(usuario_id: int, cancion_id: int) -> bool:
    """Devuelve True si quedó liked, False si quedó sin like."""
    if is_cancion_liked(usuario_id, cancion_id):
        _execute(
            "DELETE FROM [Biblioteca].[UsuarioCancionLike] "
            "WHERE Usuario_idUsuario = %s AND Cancion_idCancion = %s",
            (usuario_id, cancion_id),
        )
        return False
    _execute(
        "INSERT INTO [Biblioteca].[UsuarioCancionLike] "
        "(Usuario_idUsuario, Cancion_idCancion) VALUES (%s, %s)",
        (usuario_id, cancion_id),
    )
    return True


def get_canciones_liked_ids(usuario_id: int) -> set[int]:
    """Set de IDs de canciones likeadas — útil para pintar estado en listas."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT Cancion_idCancion FROM [Biblioteca].[UsuarioCancionLike] "
            "WHERE Usuario_idUsuario = %s",
            (usuario_id,),
        )
        return {row[0] for row in cur.fetchall()}


def get_canciones_liked(usuario_id: int) -> list[dict]:
    """Lista enriquecida de canciones que le gustan al usuario."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
              c.idCancion        AS idCancion,
              c.nombreCancion    AS nombreCancion,
              c.duracion         AS duracion,
              c.calidadKbps      AS calidadKbps,
              c.totalReproducciones AS totalReproducciones,
              a.idAlbum          AS idAlbum,
              a.tituloAlbum      AS tituloAlbum,
              ar.nombreArtistico AS nombreArtistico,
              ucl.fechaLike      AS fechaLike
            FROM [Biblioteca].[UsuarioCancionLike] ucl
              INNER JOIN [Catalogo].[Cancion]    c  ON c.idCancion = ucl.Cancion_idCancion
              INNER JOIN [Catalogo].[Album]      a  ON a.idAlbum = c.Album_idAlbum
              INNER JOIN [Usuario].[Artista]     ar ON ar.idUsuario = a.Artista_idUsuario
            WHERE ucl.Usuario_idUsuario = %s
              AND c.estadoCancion = 'activa'
            ORDER BY ucl.fechaLike DESC
            """,
            (usuario_id,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# SEGUIR artistas
# ──────────────────────────────────────────────────────────
def is_artista_seguido(usuario_id: int, artista_id: int) -> bool:
    return _exists(
        "SELECT 1 FROM [Biblioteca].[UsuarioSigueArtista] "
        "WHERE Usuario_idUsuario = %s AND Artista_idUsuario = %s",
        (usuario_id, artista_id),
    )


@transaction.atomic
def toggle_seguir_artista(usuario_id: int, artista_id: int) -> bool:
    if is_artista_seguido(usuario_id, artista_id):
        _execute(
            "DELETE FROM [Biblioteca].[UsuarioSigueArtista] "
            "WHERE Usuario_idUsuario = %s AND Artista_idUsuario = %s",
            (usuario_id, artista_id),
        )
        return False
    _execute(
        "INSERT INTO [Biblioteca].[UsuarioSigueArtista] "
        "(Usuario_idUsuario, Artista_idUsuario) VALUES (%s, %s)",
        (usuario_id, artista_id),
    )
    return True


def get_artistas_seguidos_ids(usuario_id: int) -> set[int]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT Artista_idUsuario FROM [Biblioteca].[UsuarioSigueArtista] "
            "WHERE Usuario_idUsuario = %s",
            (usuario_id,),
        )
        return {row[0] for row in cur.fetchall()}


def get_artistas_seguidos(usuario_id: int) -> list[dict]:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
              ar.idUsuario       AS idArtista,
              ar.nombreArtistico AS nombreArtistico,
              ar.biografia       AS biografia,
              usa.fechaSeguimiento AS fechaSeguimiento
            FROM [Biblioteca].[UsuarioSigueArtista] usa
              INNER JOIN [Usuario].[Artista] ar
                  ON ar.idUsuario = usa.Artista_idUsuario
            WHERE usa.Usuario_idUsuario = %s
            ORDER BY usa.fechaSeguimiento DESC
            """,
            (usuario_id,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# GUARDAR álbumes
# ──────────────────────────────────────────────────────────
def is_album_guardado(usuario_id: int, album_id: int) -> bool:
    return _exists(
        "SELECT 1 FROM [Biblioteca].[UsuarioAlbum] "
        "WHERE Usuario_idUsuario = %s AND Album_idAlbum = %s",
        (usuario_id, album_id),
    )


@transaction.atomic
def toggle_guardar_album(usuario_id: int, album_id: int) -> bool:
    if is_album_guardado(usuario_id, album_id):
        _execute(
            "DELETE FROM [Biblioteca].[UsuarioAlbum] "
            "WHERE Usuario_idUsuario = %s AND Album_idAlbum = %s",
            (usuario_id, album_id),
        )
        return False
    _execute(
        "INSERT INTO [Biblioteca].[UsuarioAlbum] "
        "(Usuario_idUsuario, Album_idAlbum) VALUES (%s, %s)",
        (usuario_id, album_id),
    )
    return True


def get_albumes_guardados_ids(usuario_id: int) -> set[int]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT Album_idAlbum FROM [Biblioteca].[UsuarioAlbum] "
            "WHERE Usuario_idUsuario = %s",
            (usuario_id,),
        )
        return {row[0] for row in cur.fetchall()}


def get_albumes_guardados(usuario_id: int) -> list[dict]:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
              a.idAlbum          AS idAlbum,
              a.tituloAlbum      AS tituloAlbum,
              a.fechaLanzamientoAlbum AS fechaLanzamientoAlbum,
              ar.nombreArtistico AS nombreArtistico,
              ua.fechaGuardado   AS fechaGuardado
            FROM [Biblioteca].[UsuarioAlbum] ua
              INNER JOIN [Catalogo].[Album]   a  ON a.idAlbum = ua.Album_idAlbum
              INNER JOIN [Usuario].[Artista]  ar ON ar.idUsuario = a.Artista_idUsuario
            WHERE ua.Usuario_idUsuario = %s
              AND a.estadoAlbum = 'activo'
            ORDER BY ua.fechaGuardado DESC
            """,
            (usuario_id,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
