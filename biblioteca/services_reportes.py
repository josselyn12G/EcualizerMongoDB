from django.db import connection


def sp_crear_playlist(usuario_id, nombre, descripcion, visibilidad, tipo):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC Biblioteca.SP_CrearPlaylistUsuario "
            "@Usuario_idUsuario=%s, @nombrePlaylist=%s, "
            "@descripcion=%s, @tipoVisibilidad=%s, @tipoPlaylist=%s;",
            [usuario_id, nombre, descripcion, visibilidad, tipo]
        )
        try:
            rows = cur.fetchall()
            return rows[0][0] if rows else None
        except Exception:
            return None


def sp_listar_playlists(usuario_id, visibilidad=None):
    """Lista las playlists del usuario.

    Se consulta directamente sobre las tablas Biblioteca.Playlist /
    UsuarioPlaylist (en vez de un SP) para no depender de procedimientos
    que pueden no estar desplegados. Devuelve las columnas que usa el
    template: idPlaylist, nombrePlaylist, descripcionPlaylist,
    tipoVisibilidad, tipoPlaylist y TotalCanciones.
    """
    sql = """
        SELECT
            p.idPlaylist,
            p.nombrePlaylist,
            p.descripcionPlaylist,
            p.tipoVisibilidad,
            p.tipoPlaylist,
            (SELECT COUNT(*) FROM Biblioteca.CancionPlaylist cp
             WHERE cp.Playlist_idPlaylist = p.idPlaylist) AS TotalCanciones
        FROM Biblioteca.Playlist p
        INNER JOIN Biblioteca.UsuarioPlaylist up
                ON up.Playlist_idPlaylist = p.idPlaylist
        WHERE up.Usuario_idUsuario = %s
    """
    params = [usuario_id]
    if visibilidad:
        sql += " AND p.tipoVisibilidad = %s"
        params.append(visibilidad)
    sql += " ORDER BY p.idPlaylist DESC;"

    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def sp_generos_favoritos(usuario_id):
    with connection.cursor() as cur:
        cur.execute(
            "EXEC Biblioteca.sp_ListarGenerosFavoritos @idUsuario=%s;",
            [usuario_id]
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    
def get_canciones_playlist(playlist_id):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
                c.idCancion,
                c.nombreCancion,
                c.duracion,
                c.totalReproducciones,
                a.tituloAlbum,
                ar.nombreArtistico,
                cp.posicionPlaylist,
                cp.fechaAgregada
            FROM Biblioteca.CancionPlaylist cp
            INNER JOIN Catalogo.Cancion c ON c.idCancion = cp.Cancion_idCancion
            INNER JOIN Catalogo.Album a ON a.idAlbum = c.Album_idAlbum
            INNER JOIN Usuario.Artista ar ON ar.idUsuario = a.Artista_idUsuario
            WHERE cp.Playlist_idPlaylist = %s
              AND c.estadoCancion = 'activa'
            ORDER BY cp.posicionPlaylist
            """,
            [playlist_id]
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_playlist_info(playlist_id, usuario_id):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT p.idPlaylist, p.nombrePlaylist, p.descripcionPlaylist,
                   p.tipoVisibilidad, p.tipoPlaylist
            FROM Biblioteca.Playlist p
            INNER JOIN Biblioteca.UsuarioPlaylist up ON up.Playlist_idPlaylist = p.idPlaylist
            WHERE p.idPlaylist = %s AND up.Usuario_idUsuario = %s
            """,
            [playlist_id, usuario_id]
        )
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None