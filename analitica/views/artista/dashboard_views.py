"""Vistas de analítica del artista: Dashboard, Analytics, Monetización."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereArtista
from usuarios.models import Persona, Artista
from catalogo.models import Album

from ...services import artista_service


PERIODOS_FULL = ('semana', 'mes', 'año', 'todo')


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def _get_persona_y_artista(request):
    uid = request.session.get('usuario_id')
    persona = Persona.objects.filter(pk=uid).first() if uid else None
    perfil = None
    if persona:
        try:
            perfil = persona.artista
        except (Artista.DoesNotExist, AttributeError):
            perfil = None
    return persona, perfil


def _albumes_del_artista(id_artista):
    return list(
        Album.objects
        .filter(artista_id=id_artista)
        .exclude(estado_album='eliminado')
        .values('id_album', 'titulo_album')
        .order_by('titulo_album')
    )


def _primer_y_ultimo_dia(mes: int, anio: int) -> tuple[date, date]:
    return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])


def _int(v, default=None):
    try:
        return int(v) if v not in (None, '') else default
    except (TypeError, ValueError):
        return default


def _periodo(v, default='mes', validos=PERIODOS_FULL):
    return v if v in validos else default


def _fecha(v, default):
    if not v:
        return default
    try:
        return date.fromisoformat(v)
    except (ValueError, TypeError):
        return default


# ──────────────────────────────────────────────────────────
# Dashboard (sin filtros — todo del mes actual)
# ──────────────────────────────────────────────────────────
class DashboardArtistaView(RequiereArtista, View):
    """Dashboard del artista — métricas del mes actual."""
    template_name = 'analitica/artista/dashboard.html'

    def get(self, request):
        persona, perfil = _get_persona_y_artista(request)
        id_artista = request.session.get('usuario_id')
        hoy = date.today()

        oyentes        = artista_service.oyentes_mensuales_crecimiento(
                            id_artista, hoy.month, hoy.year)
        top10          = artista_service.top10_canciones(id_artista, 'mes')
        geografia      = artista_service.distribucion_geografica(id_artista, 'mes')
        repros_cancion = artista_service.reproducciones_por_cancion(
                            id_artista, None, 'mes')

        total_reproducciones_mes = sum(
            (r.get('TotalReproducciones') or 0) for r in repros_cancion)

        return render(request, self.template_name, {
            'persona': persona,
            'perfil':  perfil,
            'oyentes':        oyentes,
            'top10':          top10,
            'geografia':      geografia,
            'repros_cancion': repros_cancion,
            'kpis': {
                'oyentes_mes':       (oyentes or {}).get('OyentesUnicosMes', 0),
                'oyentes_anterior':  (oyentes or {}).get('OyentesUnicosMesAnterior', 0),
                'crecimiento_pct':   (oyentes or {}).get('PorcentajeCrecimiento', 0),
                'periodo_label':     (oyentes or {}).get('PeriodoConsultado', ''),
                'reproducciones_mes': total_reproducciones_mes,
            },
        })


# ──────────────────────────────────────────────────────────
# Analytics (cada SP con sus propios filtros)
# ──────────────────────────────────────────────────────────
class AnalyticsArtistaView(RequiereArtista, View):
    """Analytics — cada sección tiene su propio filtro independiente."""
    template_name = 'analitica/artista/analytics.html'

    def get(self, request):
        persona, perfil = _get_persona_y_artista(request)
        id_artista = request.session.get('usuario_id')
        hoy = date.today()
        g = request.GET

        # ── Filtros por sección ──
        # Top 10
        f_top_periodo = _periodo(g.get('top_periodo'), 'mes', ('mes', 'año'))

        # Geografía
        f_geo_periodo = _periodo(g.get('geo_periodo'), 'mes')

        # Reproducciones por canción
        f_rep_periodo = _periodo(g.get('rep_periodo'), 'mes')
        f_rep_album   = _int(g.get('rep_album'))

        # Oyentes mes/año
        f_oy_mes  = _int(g.get('oy_mes'),  hoy.month)
        f_oy_anio = _int(g.get('oy_anio'), hoy.year)

        albumes = _albumes_del_artista(id_artista)

        oyentes        = artista_service.oyentes_mensuales_crecimiento(
                            id_artista, f_oy_mes, f_oy_anio)
        top10          = artista_service.top10_canciones(id_artista, f_top_periodo)
        geografia      = artista_service.distribucion_geografica(id_artista, f_geo_periodo)
        repros_cancion = artista_service.reproducciones_por_cancion(
                            id_artista, f_rep_album, f_rep_periodo)

        return render(request, self.template_name, {
            'persona': persona, 'perfil': perfil,
            'albumes': albumes,
            'oyentes':        oyentes,
            'top10':          top10,
            'geografia':      geografia,
            'repros_cancion': repros_cancion,
            'filtros': {
                'top_periodo': f_top_periodo,
                'geo_periodo': f_geo_periodo,
                'rep_periodo': f_rep_periodo,
                'rep_album':   f_rep_album,
                'oy_mes':      f_oy_mes,
                'oy_anio':     f_oy_anio,
            },
            'oyentes_kpi': {
                'mes':       (oyentes or {}).get('OyentesUnicosMes', 0),
                'anterior':  (oyentes or {}).get('OyentesUnicosMesAnterior', 0),
                'pct':       (oyentes or {}).get('PorcentajeCrecimiento', 0),
                'label':     (oyentes or {}).get('PeriodoConsultado', ''),
            },
        })


# ──────────────────────────────────────────────────────────
# Monetización (regalías pre-cierre + histórico + chart)
# ──────────────────────────────────────────────────────────
class MonetizacionArtistaView(RequiereArtista, View):
    """Página de monetización: regalías pendientes + histórico + evolución."""
    template_name = 'analitica/artista/monetizacion.html'

    def get(self, request):
        persona, perfil = _get_persona_y_artista(request)
        id_artista = request.session.get('usuario_id')
        hoy = date.today()
        g = request.GET

        # Filtros — sección "Pendiente" (pre-cierre)
        f_pend_desde = _fecha(g.get('pend_desde'),
                              date(hoy.year, hoy.month, 1))
        f_pend_hasta = _fecha(g.get('pend_hasta'), hoy)
        f_pend_tarifa = float(g.get('pend_tarifa') or 0.004)

        # Filtros — sección "Histórico" (post-cierre)
        f_hist_desde = _fecha(g.get('hist_desde'), hoy - timedelta(days=365))
        f_hist_hasta = _fecha(g.get('hist_hasta'), hoy)

        # Filtros — gráfico de evolución
        f_meses = _int(g.get('meses'), 12) or 12

        regalias_pendientes = artista_service.regalias_artista(
            id_artista,
            f_pend_desde.isoformat(),
            f_pend_hasta.isoformat(),
            f_pend_tarifa,
        )
        historial = artista_service.historial_regalias_artista(
            id_artista,
            f_hist_desde.isoformat(),
            f_hist_hasta.isoformat(),
        )
        evolucion = artista_service.resumen_mensual_regalias_artista(
            id_artista, f_meses)

        total_pendiente = sum(float(r.get('MontoNetoArtista') or 0)
                              for r in regalias_pendientes)
        total_historico = sum(float(r.get('MontoNetoArtista') or 0)
                              for r in historial)
        total_bruto_hist = sum(float(r.get('MontoBruto') or 0)
                               for r in historial)
        total_descontado = total_bruto_hist - total_historico

        return render(request, self.template_name, {
            'persona': persona, 'perfil': perfil,
            'regalias_pendientes': regalias_pendientes,
            'historial':           historial,
            'evolucion':           evolucion,
            'filtros': {
                'pend_desde':  f_pend_desde,
                'pend_hasta':  f_pend_hasta,
                'pend_tarifa': f_pend_tarifa,
                'hist_desde':  f_hist_desde,
                'hist_hasta':  f_hist_hasta,
                'meses':       f_meses,
            },
            'kpis': {
                'total_pendiente':  round(total_pendiente, 2),
                'total_historico':  round(total_historico, 2),
                'total_descontado': round(total_descontado, 2),
                'meses_cerrados':   len(evolucion),
            },
        })
