"""Re-exports de las vistas del dashboard de Analítica del administrador."""

from .resumen_views import ResumenGeneralView, KpisJsonView
from .usuarios_views import UsuariosView
from .musica_views import MusicaView, AlbumesView, GenerosView, ArtistasView
from .reproducciones_views import ReproduccionesView
from .actividad_views import ActividadView
from .reportes_views import (
    ReportesView, RegaliasView,
    CerrarFacturacionMensualView, CerrarFacturacionTodosView,
)
from .comercial_views import (
    DiscograficasView, ContratosView, PlanesView, SuscripcionesView,
)

__all__ = [
    'ResumenGeneralView', 'KpisJsonView',
    'UsuariosView',
    'MusicaView', 'AlbumesView', 'GenerosView', 'ArtistasView',
    'ReproduccionesView',
    'ActividadView',
    'ReportesView', 'RegaliasView',
    'CerrarFacturacionMensualView', 'CerrarFacturacionTodosView',
    'DiscograficasView', 'ContratosView',
    'PlanesView', 'SuscripcionesView',
]
