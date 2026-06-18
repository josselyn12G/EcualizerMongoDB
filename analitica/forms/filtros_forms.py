"""
Formularios usados en el panel de Analítica del administrador.

Son forms de FILTRO/RANGO (no de creación), porque las tablas Reproduccion
y Regalia se cargan vía SPs (SP_RegistrarReproduccion, jobs internos).
"""

from datetime import date, timedelta
from django import forms


PERIODO_CHOICES = [
    ('semana', 'Última semana'),
    ('mes',    'Último mes'),
    ('año',    'Último año'),
    ('todo',   'Histórico completo'),
]


class RangoFechasForm(forms.Form):
    """Filtro genérico de rango de fechas (regalías, reportes, etc.)."""
    desde = forms.DateField(
        label='Desde',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    hasta = forms.DateField(
        label='Hasta',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    def clean(self):
        cleaned = super().clean()
        d, h = cleaned.get('desde'), cleaned.get('hasta')
        if d and h and d > h:
            raise forms.ValidationError('"Desde" no puede ser posterior a "Hasta".')
        return cleaned

    @staticmethod
    def default_range(days: int = 30) -> tuple[date, date]:
        hoy = date.today()
        return hoy - timedelta(days=days), hoy


class PeriodoForm(forms.Form):
    """Filtro de periodo predefinido (semana / mes / año / todo)."""
    periodo = forms.ChoiceField(
        choices=PERIODO_CHOICES,
        required=False,
        initial='mes',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class AnioForm(forms.Form):
    """Filtro por año (reportes de ingresos, regalías)."""
    anio = forms.IntegerField(
        label='Año',
        required=False,
        min_value=2000,
        max_value=date.today().year,
        widget=forms.NumberInput(attrs={'class': 'form-control',
                                         'placeholder': str(date.today().year)}),
    )


PERIODOS_ARTISTA_CHOICES = [
    ('semana', 'Última semana'),
    ('mes',    'Último mes'),
    ('año',    'Último año'),
    ('todo',   'Histórico completo'),
]


class FiltroAnalyticsArtistaForm(forms.Form):
    """Filtros para el dashboard analítico del artista.

    Cada SP usa una combinación distinta de campos; las views toman lo
    que necesitan y dejan el resto:
      - sp_ReporteReproduccionesPorCancion → periodo + album
      - sp_Top10CancionesArtista          → periodo_top (mes / año)
      - sp_OyentesMensualesCrecimiento    → mes + anio
      - sp_DistribucionGeograficaArtista  → periodo
      - sp_ReporteRegaliasArtista         → desde + hasta + valor
    """

    periodo = forms.ChoiceField(
        label='Periodo (canciones / geografía)',
        choices=PERIODOS_ARTISTA_CHOICES,
        required=False, initial='mes',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    periodo_top = forms.ChoiceField(
        label='Periodo (Top 10)',
        choices=[('mes', 'Último mes'), ('año', 'Último año')],
        required=False, initial='mes',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    album = forms.IntegerField(
        label='Álbum (opcional)',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    mes = forms.IntegerField(
        label='Mes (oyentes)',
        required=False, min_value=1, max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    anio = forms.IntegerField(
        label='Año (oyentes)',
        required=False, min_value=2000, max_value=date.today().year + 1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    desde = forms.DateField(
        label='Regalías · desde',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    hasta = forms.DateField(
        label='Regalías · hasta',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    valor_por_reproduccion = forms.DecimalField(
        label='USD por reproducción',
        required=False, initial=0.004, min_value=0,
        max_digits=8, decimal_places=4,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
    )


class ConsolidadoRegaliasForm(RangoFechasForm):
    """Filtro del reporte de consolidado: sólo rango de fechas.

    La tarifa por reproducción se fija en el SP (0.004 USD/play) para
    coincidir con `Analitica.SP_CerrarFacturacionMensual`.
    """
    pass
