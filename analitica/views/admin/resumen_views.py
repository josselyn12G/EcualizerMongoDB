"""Resumen general + endpoint JSON de KPIs."""

from django.shortcuts import render
from django.views import View
from django.http import JsonResponse

from usuarios.mixins import RequiereAdmin
from ... import services


class ResumenGeneralView(RequiereAdmin, View):
    template_name = 'analitica/admin/resumen_general.html'

    def get(self, request):
        return render(request, self.template_name, {
            'kpis':            services.kpis_resumen(),
            'engagement':      services.engagement_resumen(),
            'regalias':        services.regalias_resumen(),
            'serie_dias':      services.reproducciones_por_dia(30),
            'serie_hora':      services.reproducciones_por_hora(),
            'top_paises':      services.reproducciones_por_pais(8),
            'top_generos':     services.top_generos(8),
            'top_artistas':    services.top_artistas(8),
            'top_likes':       services.top_canciones_likes(10),
            'crecimiento':     services.crecimiento_usuarios(12),
            'usuarios_planes': services.usuarios_activos(),
            'planes':          services.distribucion_planes(),
            'actividad':       services.actividad_reciente(15),
        })


class KpisJsonView(RequiereAdmin, View):
    """API simple para refrescar KPIs sin recargar la página."""

    def get(self, request):
        return JsonResponse({'ok': True, 'data': services.kpis_resumen()})
