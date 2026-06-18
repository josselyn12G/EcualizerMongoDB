"""
Wrapper Python para los Stored Procedures de Album.

SPs implementados en [Catalogo]:
  - SP_CrearAlbum
  - SP_EditarAlbum
  - SP_ListarAlbumes
  - SP_DesactivarAlbum
"""

from django.db import connection


# ──────────────────────────────────────────────────────────
# SP_CrearAlbum
# ──────────────────────────────────────────────────────────
def sp_crear_album(titulo, fecha_lanzamiento, descripcion,
                   tipo_album_id, artista_id):
    """
    Llama a [Catalogo].SP_CrearAlbum.
    Devuelve el idAlbum recién creado.

    Ejemplo de uso desde una vista:
        nuevo_id = sp_crear_album(
            titulo='Midnight Echoes',
            fecha_lanzamiento=date(2024, 5, 1),
            descripcion='Mi primer álbum',
            tipo_album_id=1,
            artista_id=request.session['usuario_id'],
        )
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_CrearAlbum "
            "@tituloAlbum=%s, "
            "@fechaLanzamientoAlbum=%s, "
            "@descripcionAlbum=%s, "
            "@TipoAlbum_idTipoAlbum=%s, "
            "@Artista_idUsuario=%s;",
            [titulo, fecha_lanzamiento, descripcion, tipo_album_id, artista_id],
        )
        row = cur.fetchone()
        return row[0] if row else None


# ──────────────────────────────────────────────────────────
# SP_EditarAlbum
# ──────────────────────────────────────────────────────────
def sp_editar_album(id_album, titulo, fecha_lanzamiento,
                    descripcion, tipo_album_id, estado=None,
                    artista_id=None):
    """
    Llama a [Catalogo].SP_EditarAlbum.

    El SP valida que el artista_id sea el dueño cuando se envía
    (None ⇒ llamada del admin, omite el chequeo).
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_EditarAlbum "
            "@idAlbum=%s, "
            "@tituloAlbum=%s, "
            "@fechaLanzamientoAlbum=%s, "
            "@descripcionAlbum=%s, "
            "@TipoAlbum_idTipoAlbum=%s, "
            "@estadoAlbum=%s, "
            "@Artista_idUsuario=%s;",
            [id_album, titulo, fecha_lanzamiento, descripcion,
             tipo_album_id, estado, artista_id],
        )


# ──────────────────────────────────────────────────────────
# SP_ListarAlbumes
# ──────────────────────────────────────────────────────────
def sp_listar_albumes(artista_id=None, estado=None, busqueda=None):
    """
    Llama a [Catalogo].SP_ListarAlbumes.
    Filtros opcionales:
      - artista_id  → solo álbumes de un artista
      - estado      → 'activo', 'inactivo', 'eliminado'
      - busqueda    → texto en título

    Devuelve list[dict] con las columnas del SP.
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_ListarAlbumes "
            "@Artista_idUsuario=%s, @estadoAlbum=%s, @busqueda=%s;",
            [artista_id, estado, busqueda],
        )
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# SP_DesactivarAlbum
# ──────────────────────────────────────────────────────────
def sp_desactivar_album(id_album, ejecutor_id):
    """
    Llama a [Catalogo].SP_DesactivarAlbum.
    Cambia estadoAlbum → 'inactivo' (soft delete).
    ejecutor_id ayuda al SP a auditar quién hizo la operación.
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_DesactivarAlbum "
            "@idAlbum=%s, @ejecutor=%s;",
            [id_album, ejecutor_id],
        )
