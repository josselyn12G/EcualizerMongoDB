"""
Modelos de la app catalogo.

Cada modelo refleja una tabla del esquema [Catalogo] del SQL Server.
managed = False porque la BD ya existe — Django no ejecuta migraciones sobre estas tablas.
"""

from .tipo_album import TipoAlbum
from .album import Album
from .genero_musical import GeneroMusical
from .cancion import Cancion
from .cancion_genero import CancionGeneroMusical

__all__ = [
    'TipoAlbum',
    'Album',
    'GeneroMusical',
    'Cancion',
    'CancionGeneroMusical',
]
