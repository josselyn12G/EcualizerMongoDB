"""
Views del módulo de analítica.

Separadas por rol:
  - admin/   → Dashboard del administrador (todos los KPIs, charts, reportes)
  - artista/ → Dashboard individual del artista logueado (5 SPs específicos)

Se re-exportan las clases del admin para mantener compat con `analitica.urls`.
"""

from .admin import (  # noqa: F401
    ResumenGeneralView,
    UsuariosView,
    MusicaView,
    AlbumesView,
    ReproduccionesView,
    GenerosView,
    ArtistasView,
    ActividadView,
    ReportesView,
    RegaliasView,
    CerrarFacturacionMensualView,
    CerrarFacturacionTodosView,
    DiscograficasView,
    ContratosView,
    PlanesView,
    SuscripcionesView,
    KpisJsonView,
)

from .artista import (  # noqa: F401
    DashboardArtistaView as DashboardArtistaAnalyticsView,
    AnalyticsArtistaView,
)
