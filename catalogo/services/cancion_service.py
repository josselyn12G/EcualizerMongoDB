"""
Wrapper Python para los Stored Procedures de Cancion.

SPs implementados en [Catalogo]:
  - SP_CrearCancion
  - SP_EditarCancion
  - SP_ListarCanciones
  - SP_FiltrarCancionesGenero
  - SP_DesactivarCancion
  - SP_ReportarCancion
"""

from django.db import connection


# ──────────────────────────────────────────────────────────
# SP_CrearCancion
# ──────────────────────────────────────────────────────────
def sp_crear_cancion(nombre, duracion, fecha_lanzamiento, calidad_kbps,
                     letra, album_id, numero_pista, generos_ids=None):
    """
    Crea una canción dentro de un álbum.

    generos_ids: lista de ids de GeneroMusical a asociar (M:N).
                 El SP los inserta dentro de CancionGeneroMusical.

    Ejemplo:
        nuevo_id = sp_crear_cancion(
            nombre='Tide', duracion=210, fecha_lanzamiento=date.today(),
            calidad_kbps=320, letra=None, album_id=12, numero_pista=3,
            generos_ids=[1, 4],
        )
    """
    # SQL Server admite TVPs, pero para simplicidad pasamos los géneros
    # como string CSV y el SP los parsea con STRING_SPLIT.
    csv_generos = ','.join(str(g) for g in generos_ids) if generos_ids else ''

    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_CrearCancion "
            "@nombreCancion=%s, @duracion=%s, @fechaLanzamiento=%s, "
            "@calidadKbps=%s, @letraCancion=%s, @Album_idAlbum=%s, "
            "@numeroPista=%s, @generos=%s;",
            [nombre, duracion, fecha_lanzamiento, calidad_kbps,
             letra, album_id, numero_pista, csv_generos],
        )
        row = cur.fetchone()
        return row[0] if row else None


# ──────────────────────────────────────────────────────────
# SP_EditarCancion
# ──────────────────────────────────────────────────────────
def sp_editar_cancion(id_cancion, nombre, duracion, fecha_lanzamiento,
                      calidad_kbps, letra, numero_pista,
                      estado=None, generos_ids=None, artista_id=None):
    """
    Edita una canción. Si se pasa artista_id, el SP valida ownership.
    """
    csv_generos = ','.join(str(g) for g in generos_ids) if generos_ids else None

    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_EditarCancion "
            "@idCancion=%s, @nombreCancion=%s, @duracion=%s, "
            "@fechaLanzamiento=%s, @calidadKbps=%s, @letraCancion=%s, "
            "@numeroPista=%s, @estadoCancion=%s, @generos=%s, "
            "@Artista_idUsuario=%s;",
            [id_cancion, nombre, duracion, fecha_lanzamiento,
             calidad_kbps, letra, numero_pista, estado,
             csv_generos, artista_id],
        )


# ──────────────────────────────────────────────────────────
# SP_ListarCanciones
# ──────────────────────────────────────────────────────────
def sp_listar_canciones(artista_id=None, album_id=None,
                        estado=None, busqueda=None):
    """
    Lista canciones con filtros opcionales.
    Devuelve list[dict].
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_ListarCanciones "
            "@Artista_idUsuario=%s, @Album_idAlbum=%s, "
            "@estadoCancion=%s, @busqueda=%s;",
            [artista_id, album_id, estado, busqueda],
        )
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# SP_FiltrarCancionesGenero
# ──────────────────────────────────────────────────────────
def sp_filtrar_canciones_genero(genero_id):
    """
    Devuelve canciones activas filtradas por un género musical.
    Lo usa la vista de Usuario (oyente) para el filtro por género.
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_FiltrarCancionesGenero @idGeneroMusical=%s;",
            [genero_id],
        )
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# SP_DesactivarCancion
# ──────────────────────────────────────────────────────────
def sp_desactivar_cancion(id_cancion, ejecutor_id):
    """Soft delete: estadoCancion → 'inactiva'."""
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_DesactivarCancion "
            "@idCancion=%s, @ejecutor=%s;",
            [id_cancion, ejecutor_id],
        )


# ──────────────────────────────────────────────────────────
# SP_ReportarCancion
# ──────────────────────────────────────────────────────────
def sp_reportar_cancion(id_cancion, admin_id, motivo, comentario):
    """
    Registra un reporte de canción enviando un comentario al artista.
    El SP graba en una tabla de reportes (creada en el script SQL) y
    opcionalmente marca la canción como 'bloqueada'.
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC [Catalogo].SP_ReportarCancion "
            "@idCancion=%s, @idAdmin=%s, @motivo=%s, @comentario=%s;",
            [id_cancion, admin_id, motivo, comentario],
        )
