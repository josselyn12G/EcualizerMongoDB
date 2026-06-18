"""
Wrappers Python para los SPs del Dashboard del Artista.

Fuente: Scripts SQL/Consultas e Informes/Artista/Script Procedimientos Almacenados.sql

SPs envueltos:
  - Analitica.sp_ReporteReproduccionesPorCancion
  - Analitica.sp_Top10CancionesArtista
  - Analitica.sp_OyentesMensualesCrecimiento
  - Analitica.sp_DistribucionGeograficaArtista
  - Pagos.sp_ReporteRegaliasArtista
"""

from __future__ import annotations

import logging

from .admin_service import _exec_rows, _exec_one


logger = logging.getLogger('ecualizer.analitica')


PERIODOS_VALIDOS = ('semana', 'mes', 'año', 'todo')


def reproducciones_por_cancion(id_artista: int,
                                id_album: int | None = None,
                                periodo: str = 'todo') -> list[dict]:
    """Reproducciones por canción del artista, filtrable por álbum/periodo."""
    if periodo not in PERIODOS_VALIDOS:
        periodo = 'todo'
    return _exec_rows(
        "EXEC Analitica.sp_ReporteReproduccionesPorCancion "
        "@idArtista=%s, @idAlbum=%s, @periodo=%s;",
        [id_artista, id_album, periodo],
    )


def top10_canciones(id_artista: int, periodo: str = 'mes') -> list[dict]:
    """Top 10 canciones por reproducciones (solo 'mes' o 'año')."""
    if periodo not in ('mes', 'año'):
        periodo = 'mes'
    return _exec_rows(
        "EXEC Analitica.sp_Top10CancionesArtista "
        "@idArtista=%s, @periodo=%s;",
        [id_artista, periodo],
    )


def oyentes_mensuales_crecimiento(id_artista: int,
                                    mes: int,
                                    anio: int) -> dict:
    """Oyentes únicos del mes vs anterior + porcentaje de crecimiento."""
    return _exec_one(
        "EXEC Analitica.sp_OyentesMensualesCrecimiento "
        "@idArtista=%s, @mes=%s, @anio=%s;",
        [id_artista, mes, anio],
    )


def distribucion_geografica(id_artista: int,
                             periodo: str = 'todo') -> list[dict]:
    """Distribución de reproducciones por país."""
    if periodo not in PERIODOS_VALIDOS:
        periodo = 'todo'
    return _exec_rows(
        "EXEC Analitica.sp_DistribucionGeograficaArtista "
        "@idArtista=%s, @periodo=%s;",
        [id_artista, periodo],
    )


def regalias_artista(id_artista: int,
                      fecha_inicio: str,
                      fecha_fin: str,
                      valor_por_reproduccion: float = 0.004) -> list[dict]:
    """Reporte de regalías PRE-cierre (calculado en vivo desde Reproduccion)."""
    return _exec_rows(
        "EXEC Pagos.sp_ReporteRegaliasArtista "
        "@idArtista=%s, @fechaInicio=%s, @fechaFin=%s, "
        "@valorPorReproduccion=%s;",
        [id_artista, fecha_inicio, fecha_fin, valor_por_reproduccion],
    )


def historial_regalias_artista(id_artista: int,
                                desde: str | None = None,
                                hasta: str | None = None) -> list[dict]:
    """Histórico de regalías YA cerradas (desde Analitica.Regalia)."""
    return _exec_rows(
        "EXEC Pagos.sp_HistorialRegaliasArtista "
        "@idArtista=%s, @desde=%s, @hasta=%s;",
        [id_artista, desde, hasta],
    )


def resumen_mensual_regalias_artista(id_artista: int,
                                       meses: int = 12) -> list[dict]:
    """Resumen mes-a-mes para gráfico de evolución."""
    return _exec_rows(
        "EXEC Pagos.sp_ResumenMensualRegaliasArtista "
        "@idArtista=%s, @meses=%s;",
        [id_artista, meses],
    )
