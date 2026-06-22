"""Re-exports de las vistas del dashboard de Analítica del administrador."""

from .resumen_views import ResumenGeneralView, KpisJsonView
from .musica_views import MusicaView, AlbumesView, GenerosView, ArtistasView
from .reproducciones_views import ReproduccionesView
from .actividad_views import ActividadView
from .reportes_views import (
    ReportesView, RegaliasView,
    ConfirmarRegaliasView, ConfirmarRegaliasTodosView,
)
from .comercial_views import (
    DiscograficasView, ContratosView, PlanesView, SuscripcionesView,
)

__all__ = [
    'ResumenGeneralView', 'KpisJsonView',
    'MusicaView', 'AlbumesView', 'GenerosView', 'ArtistasView',
    'ReproduccionesView',
    'ActividadView',
    'ReportesView', 'RegaliasView',
    'ConfirmarRegaliasView', 'ConfirmarRegaliasTodosView',
    'DiscograficasView', 'ContratosView',
    'PlanesView', 'SuscripcionesView',
]
