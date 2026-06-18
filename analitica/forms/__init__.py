"""Forms del módulo de analítica (filtros de reportes y rangos)."""

from .filtros_forms import (
    RangoFechasForm,
    PeriodoForm,
    AnioForm,
    ConsolidadoRegaliasForm,
    FiltroAnalyticsArtistaForm,
    PERIODO_CHOICES,
    PERIODOS_ARTISTA_CHOICES,
)

__all__ = [
    'RangoFechasForm', 'PeriodoForm', 'AnioForm',
    'ConsolidadoRegaliasForm', 'FiltroAnalyticsArtistaForm',
    'PERIODO_CHOICES', 'PERIODOS_ARTISTA_CHOICES',
]
