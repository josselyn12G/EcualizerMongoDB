"""
Wrappers para los SPs de [Catalogo].GeneroMusical y M:N Cancion↔Genero.

SPs invocados:
  - Catalogo.SP_ListarGeneros
  - Catalogo.SP_CrearGenero
  - Catalogo.SP_EditarGenero
  - Catalogo.SP_EliminarGenero
  - Catalogo.SP_AgregarGeneroACancion
  - Catalogo.SP_QuitarGeneroDeCancion
  - Catalogo.SP_GenerosDeCancion
  - Catalogo.SP_ListarCancionesConGeneros
"""

from django.db import connection


# ──────────────────────────────────────────────────────────
# CRUD Genero
# ──────────────────────────────────────────────────────────
def sp_listar_generos(busqueda=None):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_ListarGeneros @busqueda=%s;",
            [busqueda],
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def sp_crear_genero(nombre_genero):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_CrearGenero @nombreGenero=%s;",
            [nombre_genero],
        )
        row = cur.fetchone()
        return row[0] if row else None


def sp_editar_genero(id_genero, nombre_genero):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_EditarGenero "
            "@idGeneroMusical=%s, @nombreGenero=%s;",
            [id_genero, nombre_genero],
        )


def sp_eliminar_genero(id_genero):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_EliminarGenero @idGeneroMusical=%s;",
            [id_genero],
        )


# ──────────────────────────────────────────────────────────
# M:N Cancion ↔ Genero
# ──────────────────────────────────────────────────────────
def sp_agregar_genero_a_cancion(id_cancion, id_genero):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_AgregarGeneroACancion "
            "@idCancion=%s, @idGeneroMusical=%s;",
            [id_cancion, id_genero],
        )


def sp_quitar_genero_de_cancion(id_cancion, id_genero):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_QuitarGeneroDeCancion "
            "@idCancion=%s, @idGeneroMusical=%s;",
            [id_cancion, id_genero],
        )


def sp_generos_de_cancion(id_cancion):
    """Devuelve [{idGeneroMusical, nombreGenero}, ...]."""
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_GenerosDeCancion @idCancion=%s;",
            [id_cancion],
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def sp_listar_canciones_con_generos(artista_id=None, album_id=None,
                                    estado=None, busqueda=None):
    """Lista de canciones incluyendo CSV de géneros (`generosCSV`)."""
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_ListarCancionesConGeneros "
            "@Artista_idUsuario=%s, @Album_idAlbum=%s, "
            "@estadoCancion=%s, @busqueda=%s;",
            [artista_id, album_id, estado, busqueda],
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
