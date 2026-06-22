"""Analítica · Reportes y Regalías."""

from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse

from usuarios.mixins import RequiereAdmin
from ... import services
from ...forms import AnioForm, ConsolidadoRegaliasForm


class ReportesView(RequiereAdmin, View):
    template_name = 'analitica/admin/reportes.html'

    def get(self, request):
        form = AnioForm(request.GET or None)
        anio = form.cleaned_data.get('anio') if form.is_valid() else None
        return render(request, self.template_name, {
            'form':             form,
            'anio':             anio,
            'ingresos':         services.ingresos_mensuales(anio),
            'regalias':         services.regalias_resumen(),
            'regalias_artista': services.regalias_por_artista(15),
        })


class RegaliasView(RequiereAdmin, View):
    """Panel de regalías del administrador (datos desde MongoDB)."""
    template_name = 'analitica/admin/regalias.html'

    def get(self, request):
        from ...services import regalias_admin_mongo as rm

        hoy = date.today()
        defaults = {
            'desde': hoy - timedelta(days=900),  # amplio: los cierres son ~2024
            'hasta': hoy,
        }
        form = ConsolidadoRegaliasForm(request.GET or defaults)
        form.is_valid()
        data = form.cleaned_data
        desde = data.get('desde') or defaults['desde']
        hasta = data.get('hasta') or defaults['hasta']

        return render(request, self.template_name, {
            'form':         form,
            'resumen':      rm.resumen(),
            'por_artista':  rm.por_artista(20),
            'por_pais':     rm.por_pais(),
            'consolidado':  rm.por_periodo(),
            'registros':    rm.listar_registros(desde.isoformat(), hasta.isoformat()),
            'cierre_info':  rm.info_periodos(),
            'tasas_pais':   rm.tarifas_por_pais(),
        })


def _parse_int(v):
    try:
        return int(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


class ConfirmarRegaliasView(RequiereAdmin, View):
    """POST → CONFIRMA el pago de las regalías de un período (las marca como
    'Pagado'). El artista lo verá reflejado en su monetización."""

    def post(self, request):
        from ...services import regalias_admin_mongo as rm
        mes = _parse_int(request.POST.get('mes'))
        anio = _parse_int(request.POST.get('anio'))
        artista_id = request.POST.get('artista_id') or None
        pais = request.POST.get('pais') or None
        n = rm.confirmar_periodo(mes, anio, artista_id, pais)
        if n:
            messages.success(request, f'Pago confirmado: {n} registro(s) de regalías marcados como pagados.')
        else:
            messages.info(request, 'No se encontraron regalías para confirmar.')
        return redirect(reverse('analitica:regalias'))

    def get(self, request):
        return redirect(reverse('analitica:regalias'))


class ConfirmarRegaliasTodosView(RequiereAdmin, View):
    """POST → CONFIRMA el pago de todas las regalías del rango indicado."""

    def post(self, request):
        from ...services import regalias_admin_mongo as rm
        desde = request.POST.get('desde') or None
        hasta = request.POST.get('hasta') or None
        n = rm.confirmar_rango(desde, hasta)
        if n:
            messages.success(request, f'Pago confirmado: {n} registro(s) marcados como pagados.')
        else:
            messages.info(request, 'No había regalías en el rango indicado.')
        return redirect(reverse('analitica:regalias'))

    def get(self, request):
        return redirect(reverse('analitica:regalias'))
