"""Re-exports de las vistas del dashboard analítico del artista."""

from .dashboard_views import (
    DashboardArtistaView,
    AnalyticsArtistaView,
    MonetizacionArtistaView,
)

__all__ = [
    'DashboardArtistaView',
    'AnalyticsArtistaView',
    'MonetizacionArtistaView',
]
