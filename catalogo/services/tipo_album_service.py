"""
Wrappers para los SPs de [Catalogo].TipoAlbum.

SPs invocados:
  - Catalogo.SP_ListarTiposAlbum
  - Catalogo.SP_CrearTipoAlbum
  - Catalogo.SP_EditarTipoAlbum
  - Catalogo.SP_EliminarTipoAlbum
"""

from django.db import connection


def sp_listar_tipos_album(busqueda=None):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_ListarTiposAlbum @busqueda=%s;",
            [busqueda],
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def sp_crear_tipo_album(nombre_tipo, descripcion=None):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_CrearTipoAlbum "
            "@nombreTipo=%s, @descripcionTipo=%s;",
            [nombre_tipo, descripcion],
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None


def sp_editar_tipo_album(id_tipo, nombre_tipo, descripcion=None):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_EditarTipoAlbum "
            "@idTipoAlbum=%s, @nombreTipo=%s, @descripcionTipo=%s;",
            [id_tipo, nombre_tipo, descripcion],
        )


def sp_eliminar_tipo_album(id_tipo):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_EliminarTipoAlbum @idTipoAlbum=%s;",
            [id_tipo],
        )
