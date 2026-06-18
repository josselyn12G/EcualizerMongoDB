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
    template_name = 'analitica/admin/regalias.html'

    def get(self, request):
        hoy = date.today()
        defaults = {
            'desde': hoy - timedelta(days=365),
            'hasta': hoy,
        }
        form = ConsolidadoRegaliasForm(request.GET or defaults)
        form.is_valid()
        data = form.cleaned_data
        desde = data.get('desde') or defaults['desde']
        hasta = data.get('hasta') or defaults['hasta']

        return render(request, self.template_name, {
            'form':         form,
            'resumen':      services.regalias_resumen(),
            'por_artista':  services.regalias_por_artista(20),
            'por_pais':     services.regalias_por_pais(),
            'consolidado':  services.consolidado_pagos_artistas(
                                desde.isoformat(), hasta.isoformat()),
            'registros':    services.listar_regalias(
                                desde.isoformat(), hasta.isoformat()),
            'cierre_info':  services.cierre_facturacion_info(),
            'tasas_pais':   services.listar_tasas_por_pais(),
        })


def _parse_int(v):
    try:
        return int(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


class CerrarFacturacionMensualView(RequiereAdmin, View):
    """
    POST → Ejecuta `Analitica.SP_CerrarFacturacionMensual` para un período.

    Acepta opcionalmente `mes` y `anio` por POST para cerrar un período
    específico. Si no se pasan, el SP cierra el mes anterior (legacy).
    """

    def post(self, request):
        mes  = _parse_int(request.POST.get('mes'))
        anio = _parse_int(request.POST.get('anio'))
        ok, mensaje, _filas = services.cerrar_facturacion_mensual(mes, anio)
        if ok:
            messages.success(request, mensaje)
        else:
            messages.error(request, f'No se pudo cerrar la facturación: {mensaje}')
        return redirect(reverse('analitica:regalias'))

    def get(self, request):
        return redirect(reverse('analitica:regalias'))


class CerrarFacturacionTodosView(RequiereAdmin, View):
    """POST → Cierra todos los períodos pendientes en serie."""

    def post(self, request):
        exitosos, fallidos, errores = services.cerrar_facturacion_todos()
        if exitosos and not fallidos:
            messages.success(
                request, f'{exitosos} período(s) cerrado(s) correctamente.')
        elif exitosos and fallidos:
            messages.warning(
                request,
                f'{exitosos} cerrado(s), {fallidos} con error: '
                + '; '.join(errores[:3]))
        elif not exitosos and not fallidos:
            messages.info(request, 'No hay períodos pendientes de cerrar.')
        else:
            messages.error(
                request,
                'Ningún período pudo cerrarse: ' + '; '.join(errores[:3]))
        return redirect(reverse('analitica:regalias'))

    def get(self, request):
        return redirect(reverse('analitica:regalias'))
