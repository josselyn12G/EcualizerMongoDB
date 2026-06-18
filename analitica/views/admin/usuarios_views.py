"""Vista de Analítica · Usuarios."""

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereAdmin
from ... import services


class UsuariosView(RequiereAdmin, View):
    template_name = 'analitica/admin/usuarios.html'

    def get(self, request):
        return render(request, self.template_name, {
            # Free vs Premium calculado con suscripción VIGENTE (no solo histórico)
            'distribucion_planes': services.free_vs_premium(),
            'crecimiento':         services.crecimiento_usuarios(12),
            'distribucion_pais':   services.distribucion_usuarios_pais(),
            'planes':              services.distribucion_planes(),
            'kpis':                services.kpis_resumen(),
        })
