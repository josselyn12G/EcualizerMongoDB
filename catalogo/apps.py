"""Configuración de la app catalogo (Album, Cancion, GeneroMusical, TipoAlbum)."""

from django.apps import AppConfig


class CatalogoConfig(AppConfig):
    """AppConfig de catalogo — esquema [Catalogo] del SQL Server."""

    default_auto_field = 'django.db.models.AutoField'
    name = 'catalogo'
    verbose_name = 'Catálogo Musical'
