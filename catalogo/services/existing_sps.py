"""
Wrappers Python para Stored Procedures ya existentes en el proyecto SQL
que vamos a reutilizar dentro de las vistas de la app `catalogo`.

────────────────────────────────────────────────────────────────────────
SPs YA CREADOS EN OTROS SCRIPTS QUE USAMOS AQUÍ
────────────────────────────────────────────────────────────────────────

ARTISTA:
  - Analitica.sp_ReporteReproduccionesPorCancion
        Ruta: Scripts SQL/Consultas e Informes/Artista/...
        Uso : ArtistaCancionListView · muestra reproducciones por canción

  - Analitica.sp_Top10CancionesArtista
        Ruta: Scripts SQL/Consultas e Informes/Artista/...
        Uso : ArtistaAlbumListView (header) · top 10 del artista

ADMINISTRADOR:
  - Analitica.sp_RankingGlobalCanciones
        Ruta: Scripts SQL/Consultas e Informes/Administrador/...
        Uso : AdminCancionListView · ranking global top-20

USUARIO (oyente):
  - Analitica.SP_RegistrarReproduccion
        Ruta: Scripts SQL/Reglas de Negocio/...
        Uso : UsuarioCancionDetailView · registra el "play" cuando el
              oyente reproduce una canción (regla de negocio)
"""

from django.db import connection


# ──────────────────────────────────────────────────────────
# ARTISTA · Reporte de reproducciones por canción
# ──────────────────────────────────────────────────────────
def sp_reporte_reproducciones_por_cancion(id_artista, id_album=None, periodo='todo'):
    """
    @idArtista INT,
    @idAlbum   INT     = NULL,
    @periodo   VARCHAR(10) = 'todo'   -- 'semana' | 'mes' | 'año' | 'todo'
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC Analitica.sp_ReporteReproduccionesPorCancion "
            "@idArtista=%s, @idAlbum=%s, @periodo=%s;",
            [id_artista, id_album, periodo],
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# ARTISTA · Top 10 canciones
# ──────────────────────────────────────────────────────────
def sp_top10_canciones_artista(id_artista, periodo='mes'):
    """
    @idArtista INT,
    @periodo   VARCHAR(10)  -- 'mes' | 'año'
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC Analitica.sp_Top10CancionesArtista "
            "@idArtista=%s, @periodo=%s;",
            [id_artista, periodo],
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# ADMIN · Ranking global de canciones
# ──────────────────────────────────────────────────────────
def sp_ranking_global_canciones(periodo='todo', id_genero=None, pais=None):
    """Top 20 canciones por reproducciones (consulta directa).

    El SP Analitica.sp_RankingGlobalCanciones puede no estar desplegado,
    por lo que se consulta directamente sobre Analitica.Reproduccion.
    Devuelve: Cancion, Artista, TotalReproduccionesGlobales, OyentesUnicos.
    """
    filtros = {
        'semana': 'AND r.fechaHora >= DATEADD(DAY, -7, GETDATE())',
        'mes':    'AND r.fechaHora >= DATEADD(MONTH, -1, GETDATE())',
        'año':    'AND r.fechaHora >= DATEADD(YEAR, -1, GETDATE())',
        'anio':   'AND r.fechaHora >= DATEADD(YEAR, -1, GETDATE())',
        'todo':   '',
    }
    filtro = filtros.get(periodo, '')
    sql = f"""
        SELECT TOP 20
            c.nombreCancion    AS Cancion,
            ar.nombreArtistico AS Artista,
            COUNT(*)                            AS TotalReproduccionesGlobales,
            COUNT(DISTINCT r.Usuario_idUsuario) AS OyentesUnicos
        FROM Analitica.Reproduccion r
        JOIN Catalogo.Cancion c  ON c.idCancion = r.Cancion_idCancion
        JOIN Catalogo.Album   al ON al.idAlbum  = c.Album_idAlbum
        JOIN Usuario.Artista  ar ON ar.idUsuario = al.Artista_idUsuario
        WHERE 1 = 1 {filtro}
        GROUP BY c.nombreCancion, ar.nombreArtistico
        ORDER BY TotalReproduccionesGlobales DESC;
    """
    with connection.cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ──────────────────────────────────────────────────────────
# USUARIO · Registrar reproducción (regla de negocio)
# ──────────────────────────────────────────────────────────
def sp_registrar_reproduccion(usuario_id, cancion_id, pais,
                              duracion_escuchada, fue_saltada='N'):
    """
    @Usuario_idUsuario  INT,
    @Cancion_idCancion  INT,
    @pais               VARCHAR(50),
    @duracionEscuchada  SMALLINT,
    @fueSaltada         CHAR(1)   -- 'S' | 'N'

    Devuelve dict con el registro creado (idReproduccion, contadorActualizado, ...).
    """
    with connection.cursor() as cur:
        cur.execute(
            "EXEC Analitica.SP_RegistrarReproduccion "
            "@Usuario_idUsuario=%s, @Cancion_idCancion=%s, "
            "@pais=%s, @duracionEscuchada=%s, @fueSaltada=%s;",
            [usuario_id, cancion_id, pais, duracion_escuchada, fue_saltada],
        )
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None
