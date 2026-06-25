"""Vista del artista para visualizar sus contratos discográficos — MongoDB."""

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereArtista
from usuarios.mongo_service import find_user_by_identifier, build_user_namespace

from ... import mongo_service as ms


def _get_persona_y_artista(request):
    uid = request.session.get('usuario_id')
    doc = find_user_by_identifier(uid) if uid else None
    persona = build_user_namespace(doc) if doc else None
    perfil = getattr(persona, 'artista', None) if persona else None
    return persona, perfil


class ContratosArtistaView(RequiereArtista, View):
    """Lista los contratos discográficos del artista logueado (solo lectura)."""
    template_name = 'industria/artista/contratos.html'

    def get(self, request):
        persona, perfil = _get_persona_y_artista(request)
        id_artista = request.session.get('usuario_id')

        contratos = ms.listar_contratos(artista_id=id_artista)
        kpis = ms.contratos_kpis(artista_id=id_artista)

        return render(request, self.template_name, {
            'persona':   persona,
            'perfil':    perfil,
            'contratos': contratos,
            'kpis':      kpis,
        })
