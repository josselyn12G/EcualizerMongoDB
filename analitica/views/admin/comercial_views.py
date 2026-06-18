"""
Analítica/Comercial · Discográficas y Contratos (vistas de solo-lectura
desde el módulo de analítica).

NOTA: el CRUD completo de Industria (Discográfica/Contrato) vive en la
app `industria` con su propia carpeta de templates/views/forms. Aquí solo
exponemos los listados que el dashboard comercial necesita.
"""

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereAdmin
from ... import services


class DiscograficasView(RequiereAdmin, View):
    template_name = 'analitica/admin/discograficas.html'

    def get(self, request):
        q = request.GET.get('q') or None
        return render(request, self.template_name, {
            'q':              q,
            'discograficas':  services.listar_discograficas(q),
            'kpis':           services.contratos_kpis(),
        })


class ContratosView(RequiereAdmin, View):
    template_name = 'analitica/admin/contratos.html'

    def get(self, request):
        estado = request.GET.get('estado') or None
        return render(request, self.template_name, {
            'estado':     estado,
            'contratos':  services.listar_contratos(estado),
            'kpis':       services.contratos_kpis(),
        })


class PlanesView(RequiereAdmin, View):
    """Comercial · Planes (catálogo TipoPlan con métricas agregadas)."""
    template_name = 'analitica/admin/planes.html'

    def get(self, request):
        return render(request, self.template_name, {
            'planes':              services.listar_planes(),
            'distribucion_planes': services.distribucion_planes(),
            'kpis':                services.suscripciones_kpis(),
        })


class SuscripcionesView(RequiereAdmin, View):
    """Comercial · Suscripciones (Usuario ↔ TipoPlan)."""
    template_name = 'analitica/admin/suscripciones.html'

    def get(self, request):
        estado = request.GET.get('estado') or None
        tipo_plan = request.GET.get('plan')
        tipo_plan_id = int(tipo_plan) if tipo_plan and tipo_plan.isdigit() else None

        return render(request, self.template_name, {
            'estado':         estado,
            'tipo_plan_id':   tipo_plan_id,
            'suscripciones':  services.listar_suscripciones(estado, tipo_plan_id),
            'kpis':           services.suscripciones_kpis(),
            'series_mensual': services.suscripciones_por_mes(12),
            'planes':         services.listar_planes(),
        })
