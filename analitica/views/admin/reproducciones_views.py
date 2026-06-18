"""Analítica · Reproducciones (engagement + series + geografía)."""

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereAdmin
from ... import services


class ReproduccionesView(RequiereAdmin, View):
    template_name = 'analitica/admin/reproducciones.html'

    def get(self, request):
        try:
            dias = int(request.GET.get('dias', 30))
        except (TypeError, ValueError):
            dias = 30
        dias = max(7, min(dias, 365))

        return render(request, self.template_name, {
            'dias':        dias,
            'engagement':  services.engagement_resumen(),
            'serie_dias':  services.reproducciones_por_dia(dias),
            'serie_hora':  services.reproducciones_por_hora(),
            'top_paises':  services.reproducciones_por_pais(10),
        })
