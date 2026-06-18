"""Vista del artista para visualizar sus contratos discográficos."""

from datetime import date

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereArtista
from usuarios.models import Persona, Artista

from ...models import ContratoDiscografica


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


class ContratosArtistaView(RequiereArtista, View):
    """Lista los contratos discográficos del artista logueado (solo lectura)."""
    template_name = 'industria/artista/contratos.html'

    def get(self, request):
        persona, perfil = _get_persona_y_artista(request)
        id_artista = request.session.get('usuario_id')

        contratos = list(
            ContratoDiscografica.objects
            .filter(artista_id=id_artista)
            .select_related('discografica')
            .order_by('-fecha_inicio')
        )

        hoy = date.today()
        activos = sum(1 for c in contratos
                      if c.estado_contrato == 'Activo'
                      and (c.fecha_fin is None or c.fecha_fin >= hoy))
        finalizados = sum(1 for c in contratos
                          if c.estado_contrato == 'Finalizado')
        cancelados  = sum(1 for c in contratos
                          if c.estado_contrato == 'Cancelado')

        return render(request, self.template_name, {
            'persona':   persona,
            'perfil':    perfil,
            'contratos': contratos,
            'kpis': {
                'total':       len(contratos),
                'activos':     activos,
                'finalizados': finalizados,
                'cancelados':  cancelados,
            },
        })
