"""Views de la app industria — por rol."""

from .admin import (  # noqa: F401
    DiscograficaListView, DiscograficaCreateView,
    DiscograficaUpdateView, DiscograficaDeleteView,
    ContratoListView, ContratoCreateView,
    ContratoUpdateView, ContratoDeleteView,
)

from .artista import ContratosArtistaView  # noqa: F401
