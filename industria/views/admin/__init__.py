"""Vistas CRUD del Administrador para Discográficas y Contratos."""

from .discografica_views import (
    DiscograficaListView, DiscograficaCreateView,
    DiscograficaUpdateView, DiscograficaDeleteView,
)
from .contrato_views import (
    ContratoListView, ContratoCreateView,
    ContratoUpdateView, ContratoDeleteView,
)

__all__ = [
    'DiscograficaListView', 'DiscograficaCreateView',
    'DiscograficaUpdateView', 'DiscograficaDeleteView',
    'ContratoListView', 'ContratoCreateView',
    'ContratoUpdateView', 'ContratoDeleteView',
]
