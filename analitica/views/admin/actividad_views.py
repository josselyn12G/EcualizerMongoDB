"""Analítica · Feed de actividad reciente (reproducciones, likes, follows)."""

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereAdmin
from ... import services


class ActividadView(RequiereAdmin, View):
    template_name = 'analitica/admin/actividad.html'

    def get(self, request):
        try:
            top = int(request.GET.get('top', 50))
        except (TypeError, ValueError):
            top = 50
        top = max(10, min(top, 200))
        return render(request, self.template_name, {
            'top':       top,
            'actividad': services.actividad_reciente(top),
        })
