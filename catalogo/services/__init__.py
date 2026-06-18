"""
Servicios de catálogo — wrappers que invocan Stored Procedures de SQL Server.

Cada función abre un cursor con `connection.cursor()` y ejecuta `EXEC` sobre
el SP correspondiente del esquema [Catalogo].

Convención: las funciones devuelven el resultado del SP o lanzan la excepción
propagada por SQL Server (THROW) para que la vista la maneje.
"""

from .album_service import (
    sp_crear_album,
    sp_editar_album,
    sp_listar_albumes,
    sp_desactivar_album,
)
from .cancion_service import (
    sp_crear_cancion,
    sp_editar_cancion,
    sp_listar_canciones,
    sp_filtrar_canciones_genero,
    sp_desactivar_cancion,
    sp_reportar_cancion,
)
from .existing_sps import (
    sp_reporte_reproducciones_por_cancion,
    sp_top10_canciones_artista,
    sp_ranking_global_canciones,
    sp_registrar_reproduccion,
)
from .genero_service import (
    sp_listar_generos,
    sp_crear_genero,
    sp_editar_genero,
    sp_eliminar_genero,
    sp_agregar_genero_a_cancion,
    sp_quitar_genero_de_cancion,
    sp_generos_de_cancion,
    sp_listar_canciones_con_generos,
)
from .tipo_album_service import (
    sp_listar_tipos_album,
    sp_crear_tipo_album,
    sp_editar_tipo_album,
    sp_eliminar_tipo_album,
)
from .deezer_service import (
    deezer_get_artist_image,
    deezer_get_album_image,
    deezer_get_track_image,
    deezer_get_track_preview,
    deezer_enrich_canciones,
    deezer_enrich_albumes,
)
from .lyrics_service import obtener_letra

__all__ = [
    # SPs nuevos · Album / Cancion
    'sp_crear_album', 'sp_editar_album', 'sp_listar_albumes', 'sp_desactivar_album',
    'sp_crear_cancion', 'sp_editar_cancion', 'sp_listar_canciones',
    'sp_filtrar_canciones_genero', 'sp_desactivar_cancion', 'sp_reportar_cancion',
    # SPs existentes
    'sp_reporte_reproducciones_por_cancion',
    'sp_top10_canciones_artista',
    'sp_ranking_global_canciones',
    'sp_registrar_reproduccion',
    # Genero CRUD + M:N
    'sp_listar_generos', 'sp_crear_genero', 'sp_editar_genero', 'sp_eliminar_genero',
    'sp_agregar_genero_a_cancion', 'sp_quitar_genero_de_cancion',
    'sp_generos_de_cancion', 'sp_listar_canciones_con_generos',
    # TipoAlbum CRUD
    'sp_listar_tipos_album', 'sp_crear_tipo_album',
    'sp_editar_tipo_album', 'sp_eliminar_tipo_album',
    # Deezer (imágenes + preview MP3, sin auth)
    'deezer_get_artist_image', 'deezer_get_album_image', 'deezer_get_track_image',
    'deezer_get_track_preview',
    'deezer_enrich_canciones', 'deezer_enrich_albumes',
    # Letras (api.lyrics.ovh)
    'obtener_letra',
]
